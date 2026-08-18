from __future__ import annotations

import asyncio
import logging
import re
from typing import Optional
from urllib.parse import urljoin, urlparse

import httpx

from backend.config import AppConfig, load_config

logger = logging.getLogger(__name__)

USER_AGENT = "OpenResumeRemy/0.1 (local personal job search; respects robots.txt)"
BROWSER_ACCEPT = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"

_robots_cache: dict[str, list[str]] = {}


async def polite_sleep(config: AppConfig) -> None:
    """Wait `remy_request_delay` seconds between requests (politeness)."""
    delay = max(0.0, float(config.remy_request_delay))
    if delay > 0:
        await asyncio.sleep(delay)


async def fetch_text(url: str, *, timeout: float = 30.0, headers: Optional[dict] = None, cookies: Optional[dict] = None) -> str:
    """Fetch a page and return its text body. Optionally reuse cookies across calls."""
    merged = {
        "User-Agent": USER_AGENT,
        "Accept": BROWSER_ACCEPT,
        "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
    }
    if headers:
        merged.update(headers)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, cookies=cookies) as client:
        try:
            resp = await client.get(url, headers=merged)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            raise RuntimeError(f"Failed to fetch {url}: {e}") from e
    return resp.text


async def url_is_blocked(url: str, timeout: float = 10.0) -> bool:
    """Check robots.txt (cached per host). Returns True when the path is disallowed."""
    parsed = urlparse(url)
    host = f"{parsed.scheme}://{parsed.netloc}"
    if host not in _robots_cache:
        try:
            robots_url = urljoin(host + "/", "robots.txt")
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                resp = await client.get(robots_url, headers={"User-Agent": USER_AGENT})
                resp.raise_for_status()
                body = resp.text
            rules: list[str] = []
            agent = "*"
            current_agent = "*"
            for line in body.splitlines():
                stripped = line.strip().lower()
                if not stripped or stripped.startswith("#"):
                    continue
                if stripped.startswith("user-agent:"):
                    current_agent = stripped.split(":", 1)[1].strip()
                    continue
                if current_agent == agent and stripped.startswith("disallow:"):
                    path = stripped.split(":", 1)[1].strip()
                    if path:
                        rules.append(path)
            _robots_cache[host] = rules
        except httpx.HTTPError:
            logger.warning("Could not fetch robots.txt for %s; assuming allowed", host)
            _robots_cache[host] = []
    for rule in _robots_cache[host]:
        if rule.endswith("*"):
            rule = rule[:-1]
        if rule == "/":
            return True
        if parsed.path.startswith(rule):
            return True
    return False


def normalize_url(url: str) -> str:
    """Strip tracking params and fragments for stable dedup keys."""
    parsed = urlparse(url)
    query = []
    for pair in (parsed.query or "").split("&"):
        if not pair:
            continue
        key = pair.split("=", 1)[0].lower()
        if key.startswith("utm_") or key in ("refid", "trackingid", "sessionid", "uuid"):
            continue
        query.append(pair)
    clean = parsed._replace(query="&".join(query), fragment="").geturl()
    return clean.rstrip("/")


async def fetch_text_get_cookies(
    url: str, *, timeout: float = 30.0, headers: Optional[dict] = None
) -> tuple[str, httpx.Cookies]:
    """Fetch a page and return (text, cookies) for session reuse."""
    merged: dict[str, str] = {
        "User-Agent": USER_AGENT,
        "Accept": BROWSER_ACCEPT,
        "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
    }
    if headers:
        merged.update(headers)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        try:
            resp = await client.get(url, headers=merged)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            raise RuntimeError(f"Failed to fetch {url}: {e}") from e
    return resp.text, resp.cookies


def slugify(text: str) -> str:
    """Lowercase slug from arbitrary text (used for OCC detail URLs)."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower().strip()).strip("-")
    return slug


def _blocks_to_markdown(node) -> list[str]:
    """Convert a BeautifulSoup node tree into markdown-ish lines."""
    from bs4 import NavigableString, Tag

    lines: list[str] = []
    if isinstance(node, NavigableString):
        text = str(node).strip()
        if text:
            lines.append(text)
        return lines
    if not isinstance(node, Tag):
        return lines

    if node.name in ("script", "style", "nav", "header", "footer", "aside", "form"):
        return lines

    name = node.name or ""
    if name in ("h1", "h2", "h3", "h4", "h5", "h6"):
        level = int(name[1])
        text = node.get_text(" ", strip=True)
        if text:
            lines.append(f"{'#' * level} {text}")
        return lines
    if name == "a":
        href = node.get("href", "")
        text = node.get_text(" ", strip=True)
        if href and not href.startswith(("javascript:", "#")):
            resolved = urljoin("https://placeholder.local/", href)
            lines.append(f"[{text}]({resolved})" if text else resolved)
        elif text:
            lines.append(text)
        return lines
    if name in ("p", "div", "section", "article", "tr"):
        inner = []
        for child in node.children:
            inner.extend(_blocks_to_markdown(child))
        joined = " ".join(inner).strip()
        if joined:
            lines.append(joined)
        return lines
    if name == "br":
        return []
    if name == "li":
        inner = []
        for child in node.children:
            inner.extend(_blocks_to_markdown(child))
        text = " ".join(inner).strip()
        return [f"- {text}"] if text else []
    if name in ("ul", "ol"):
        for child in node.children:
            lines.extend(_blocks_to_markdown(child))
        return lines
    if name in ("span", "strong", "b", "em", "i", "td", "th", "small"):
        text = node.get_text(" ", strip=True)
        return [text] if text else []

    inner = []
    for child in node.children:
        inner.extend(_blocks_to_markdown(child))
    return inner


def html_to_markdown(html: str, base_url: str = "") -> str:
    """Deterministic HTML → markdown using BeautifulSoup (no LLM roundtrip)."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    main = soup.find("main") or soup.find("article") or soup.body or soup
    lines: list[str] = []
    for child in main.children:
        block = _blocks_to_markdown(child)
        block = [b for b in block if b.strip()]
        if block:
            lines.extend(block)
            lines.append("")

    cleaned = "\n".join(lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    max_chars = 20000
    if len(cleaned) > max_chars:
        cleaned = cleaned[:max_chars] + "\n...[truncated]"
    return cleaned


def get_config() -> AppConfig:
    return load_config()
