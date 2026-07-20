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
        content = response.choices[0].message.content or ""
        return content

    async def chat_json(
        self,
        messages: list[dict[str, str]],
        system: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> Any:
        import json
        text = await self.chat(
            messages=messages,
            system=system,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        return json.loads(text)