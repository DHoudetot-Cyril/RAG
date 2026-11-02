"""Client minimal pour n'importe quel serveur exposant l'API OpenAI `/v1/chat/completions`.

Testé avec vLLM ; fonctionne aussi avec llama.cpp (`llama-server`), Ollama, LM Studio
ou l'API OpenAI elle-même : il suffit de changer LLM_BASE_URL et LLM_MODEL_NAME.
"""

from __future__ import annotations

import json
import re
from collections.abc import AsyncIterator
from typing import Protocol

import httpx

_THINK_BLOCK = re.compile(r"<think>.*?</think>\s*", re.DOTALL)


class LLMError(RuntimeError):
    pass


class ChatModel(Protocol):
    async def complete(self, messages: list[dict]) -> str: ...

    def stream(self, messages: list[dict]) -> AsyncIterator[str]: ...

    async def ping(self) -> bool: ...


def strip_reasoning(text: str) -> str:
    """Retire les blocs <think>…</think> produits par les modèles « raisonneurs » (Qwen3, DeepSeek-R1)."""
    return _THINK_BLOCK.sub("", text).strip()


class ThinkFilter:
    """Filtre incrémental qui supprime les blocs <think>…</think> d'un flux de tokens."""

    OPEN, CLOSE = "<think>", "</think>"

    def __init__(self) -> None:
        self.in_think = False

    def feed(self, delta: str) -> str:
        output = []
        while delta:
            if self.in_think:
                end = delta.find(self.CLOSE)
                if end == -1:
                    return "".join(output)
                delta = delta[end + len(self.CLOSE) :].lstrip()
                self.in_think = False
            else:
                start = delta.find(self.OPEN)
                if start == -1:
                    output.append(delta)
                    break
                output.append(delta[:start])
                delta = delta[start + len(self.OPEN) :]
                self.in_think = True
        return "".join(output)


class OpenAICompatibleLLM:
    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str = "not-needed",
        temperature: float = 0.2,
        max_tokens: int = 768,
        timeout: float = 120.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=httpx.Timeout(timeout, connect=10.0),
            transport=transport,
        )

    def _payload(self, messages: list[dict], stream: bool) -> dict:
        return {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": stream,
        }

    async def complete(self, messages: list[dict]) -> str:
        try:
            response = await self._client.post("/chat/completions", json=self._payload(messages, stream=False))
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"] or ""
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
            raise LLMError(f"Le modèle de langage est indisponible : {exc}") from exc
        return strip_reasoning(content)

    async def stream(self, messages: list[dict]) -> AsyncIterator[str]:
        think_filter = ThinkFilter()
        try:
            async with self._client.stream(
                "POST", "/chat/completions", json=self._payload(messages, stream=True)
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[len("data:") :].strip()
                    if data == "[DONE]":
                        break
                    try:
                        delta = json.loads(data)["choices"][0]["delta"].get("content") or ""
                    except (ValueError, KeyError, IndexError):
                        continue
                    delta = think_filter.feed(delta)
                    if delta:
                        yield delta
        except httpx.HTTPError as exc:
            raise LLMError(f"Le modèle de langage est indisponible : {exc}") from exc

    async def ping(self) -> bool:
        try:
            response = await self._client.get("/models", timeout=3.0)
            return response.status_code == 200
        except httpx.HTTPError:
            return False

    async def aclose(self) -> None:
        await self._client.aclose()
