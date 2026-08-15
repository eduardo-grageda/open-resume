from __future__ import annotations

import logging
from typing import Any, Optional

from openai import AsyncOpenAI

from backend.config import AppConfig

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._client: Optional[AsyncOpenAI] = None

    @property
    def client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=self._config.openrouter_api_key,
                base_url=self._config.openrouter_base_url,
            )
        return self._client

    @property
    def model(self) -> str:
        return self._config.openrouter_model

    async def embed(
        self, texts: list[str], model: Optional[str] = None
    ) -> list[list[float]]:
        """Embed texts via the OpenAI-compatible embeddings endpoint."""
        response = await self.client.embeddings.create(
            model=model or self.model,
            input=texts,
        )
        return [item.embedding for item in response.data]

    async def test_connection(self) -> tuple[bool, str]:
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5,
            )
            return True, response.model or self.model
        except Exception as e:
            logger.warning("LLM connection test failed: %s", e)
            return False, str(e)

    async def chat(
        self,
        messages: list[dict[str, str]],
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[dict[str, str]] = None,
    ) -> str:
        full_messages: list[dict[str, str]] = []
        if system:
            full_messages.append({"role": "system", "content": system})
        full_messages.extend(messages)

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=full_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
        )
        choice = response.choices[0]
        content = choice.message.content or ""
        if not content and choice.finish_reason:
            logger.error(
                "LLM returned empty content (finish_reason=%s, model=%s)",
                choice.finish_reason,
                response.model or self.model,
            )
            raise RuntimeError(
                f"LLM returned empty response (finish_reason={choice.finish_reason})"
            )
        return content

    async def chat_json(
        self,
        messages: list[dict[str, str]],
        system: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        max_retries: int = 2,
    ) -> tuple[Any, int]:
        import json

        retries = 0
        current_max_tokens = max_tokens

        for attempt in range(max_retries + 1):
            try:
                text = await self.chat(
                    messages=messages,
                    system=system,
                    temperature=temperature,
                    max_tokens=current_max_tokens,
                    response_format={"type": "json_object"},
                )
                result = json.loads(text)
                return result, retries
            except json.JSONDecodeError as e:
                retries = attempt + 1
                logger.warning(
                    "LLM chat_json JSON parse attempt %d/%d failed: %s",
                    retries, max_retries + 1, e,
                )
                if attempt >= max_retries:
                    raise RuntimeError(
                        f"LLM JSON parse failed after {retries} retries: {e}"
                    ) from e
            except RuntimeError as e:
                retries = attempt + 1
                error_str = str(e)
                logger.warning(
                    "LLM chat_json attempt %d/%d failed: %s",
                    retries, max_retries + 1, error_str,
                )
                if "length" in error_str and current_max_tokens < 8192:
                    current_max_tokens = min(current_max_tokens * 2, 8192)
                if attempt >= max_retries:
                    raise

        raise RuntimeError("LLM chat_json failed after all retries")