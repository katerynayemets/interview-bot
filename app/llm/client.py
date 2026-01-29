# app/llm/client.py
"""
Абстрактный клиент для LLM провайдеров.
Поддержка OpenAI, Anthropic Claude, и других.
"""

import time
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncIterator

import httpx

from app.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class LLMResponse:
    """Ответ от LLM"""
    content: str
    model: str
    tokens_input: int
    tokens_output: int
    latency_ms: int
    finish_reason: str = "stop"
    raw_response: dict = field(default_factory=dict)

    @property
    def total_tokens(self) -> int:
        return self.tokens_input + self.tokens_output

    def estimate_cost(self, input_price_per_1k: float, output_price_per_1k: float) -> float:
        """Оценка стоимости запроса"""
        return (
            (self.tokens_input / 1000) * input_price_per_1k +
            (self.tokens_output / 1000) * output_price_per_1k
        )


@dataclass
class ChatMessage:
    """Сообщение для чата"""
    role: str  # system | user | assistant
    content: str


class LLMClient(ABC):
    """Базовый класс для LLM клиентов"""

    def __init__(self, api_key: str, model: str, timeout: float = 60.0):
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    @abstractmethod
    async def chat(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        """Отправляет запрос к LLM и возвращает ответ"""
        pass

    @abstractmethod
    async def chat_stream(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> AsyncIterator[str]:
        """Стриминг ответа от LLM"""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass


class OpenAIClient(LLMClient):
    """Клиент для OpenAI API (GPT-4, GPT-3.5, GPT-5, o1)"""

    BASE_URL = "https://api.openai.com/v1"

    # Модели, которые требуют max_completion_tokens вместо max_tokens
    NEW_API_MODELS = {"o1", "o1-mini", "o1-preview", "o3", "o3-mini", "o4-mini"}
    # Префиксы моделей, использующих новый API
    NEW_API_PREFIXES = ("gpt-5", "o1", "o3", "o4")

    # Цены за 1K токенов (примерные, могут меняться)
    PRICING = {
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-4o": {"input": 0.005, "output": 0.015},
        "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
        "gpt-5-nano": {"input": 0.0001, "output": 0.0004},
    }

    def _uses_new_api(self) -> bool:
        """Проверяет, использует ли модель новый API (max_completion_tokens)"""
        if self.model in self.NEW_API_MODELS:
            return True
        return any(self.model.startswith(prefix) for prefix in self.NEW_API_PREFIXES)

    @property
    def provider_name(self) -> str:
        return "openai"

    async def chat(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        start_time = time.time()

        # Новые модели (GPT-5, o1, o3) используют max_completion_tokens
        if self._uses_new_api():
            token_param = {"max_completion_tokens": max_tokens}
        else:
            token_param = {"max_tokens": max_tokens}

        body = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            **token_param,
        }
        # Новые модели (gpt-5, o1, o3) не поддерживают кастомный temperature
        if not self._uses_new_api():
            body["temperature"] = temperature

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=body,
            )
            if response.status_code != 200:
                error_body = response.text
                logger.error(
                    f"OpenAI API error {response.status_code}: {error_body}",
                    extra={"model": self.model, "status": response.status_code}
                )
                response.raise_for_status()
            data = response.json()

        latency_ms = int((time.time() - start_time) * 1000)

        usage = data.get("usage", {})
        choice = data["choices"][0]

        logger.info(
            f"OpenAI response: {usage.get('total_tokens', 0)} tokens, {latency_ms}ms",
            extra={"model": self.model, "tokens": usage.get("total_tokens", 0)}
        )

        return LLMResponse(
            content=choice["message"]["content"],
            model=self.model,
            tokens_input=usage.get("prompt_tokens", 0),
            tokens_output=usage.get("completion_tokens", 0),
            latency_ms=latency_ms,
            finish_reason=choice.get("finish_reason", "stop"),
            raw_response=data,
        )

    async def chat_stream(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> AsyncIterator[str]:
        if self._uses_new_api():
            token_param = {"max_completion_tokens": max_tokens}
        else:
            token_param = {"max_tokens": max_tokens}

        body = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": True,
            **token_param,
        }
        if not self._uses_new_api():
            body["temperature"] = temperature

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream(
                "POST",
                f"{self.BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=body,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: ") and line != "data: [DONE]":
                        import json
                        chunk = json.loads(line[6:])
                        delta = chunk["choices"][0].get("delta", {})
                        if "content" in delta:
                            yield delta["content"]


class AnthropicClient(LLMClient):
    """Клиент для Anthropic API (Claude)"""

    BASE_URL = "https://api.anthropic.com/v1"
    API_VERSION = "2023-06-01"

    # Цены за 1K токенов
    PRICING = {
        "claude-3-opus-20240229": {"input": 0.015, "output": 0.075},
        "claude-3-sonnet-20240229": {"input": 0.003, "output": 0.015},
        "claude-3-haiku-20240307": {"input": 0.00025, "output": 0.00125},
        "claude-3-5-sonnet-20241022": {"input": 0.003, "output": 0.015},
    }

    @property
    def provider_name(self) -> str:
        return "anthropic"

    async def chat(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        start_time = time.time()

        # Anthropic использует отдельный system prompt
        system_message = None
        chat_messages = []

        for msg in messages:
            if msg.role == "system":
                system_message = msg.content
            else:
                chat_messages.append({"role": msg.role, "content": msg.content})

        request_body = {
            "model": self.model,
            "messages": chat_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        if system_message:
            request_body["system"] = system_message

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.BASE_URL}/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": self.API_VERSION,
                    "Content-Type": "application/json",
                },
                json=request_body,
            )
            response.raise_for_status()
            data = response.json()

        latency_ms = int((time.time() - start_time) * 1000)

        usage = data.get("usage", {})

        logger.info(
            f"Anthropic response: {usage.get('input_tokens', 0) + usage.get('output_tokens', 0)} tokens, {latency_ms}ms",
            extra={"model": self.model}
        )

        return LLMResponse(
            content=data["content"][0]["text"],
            model=self.model,
            tokens_input=usage.get("input_tokens", 0),
            tokens_output=usage.get("output_tokens", 0),
            latency_ms=latency_ms,
            finish_reason=data.get("stop_reason", "end_turn"),
            raw_response=data,
        )

    async def chat_stream(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> AsyncIterator[str]:
        system_message = None
        chat_messages = []

        for msg in messages:
            if msg.role == "system":
                system_message = msg.content
            else:
                chat_messages.append({"role": msg.role, "content": msg.content})

        request_body = {
            "model": self.model,
            "messages": chat_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
        }

        if system_message:
            request_body["system"] = system_message

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream(
                "POST",
                f"{self.BASE_URL}/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": self.API_VERSION,
                    "Content-Type": "application/json",
                },
                json=request_body,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        import json
                        chunk = json.loads(line[6:])
                        if chunk["type"] == "content_block_delta":
                            yield chunk["delta"].get("text", "")


# ============== Factory ==============

_client_cache: dict[str, LLMClient] = {}


def get_llm_client(
    provider: str = "openai",
    model: str | None = None,
    api_key: str | None = None,
) -> LLMClient:
    """
    Фабрика для создания LLM клиентов.

    Args:
        provider: "openai" или "anthropic"
        model: модель (если не указана, берется дефолтная)
        api_key: API ключ (если не указан, берется из env)

    Returns:
        LLMClient для выбранного провайдера
    """
    # Дефолтные модели
    default_models = {
        "openai": "gpt-4o-mini",
        "anthropic": "claude-3-5-sonnet-20241022",
    }

    # API ключи из env
    env_keys = {
        "openai": os.getenv("OPENAI_API_KEY"),
        "anthropic": os.getenv("ANTHROPIC_API_KEY"),
    }

    if provider not in default_models:
        raise ValueError(f"Unknown provider: {provider}. Supported: {list(default_models.keys())}")

    model = model or default_models[provider]
    api_key = api_key or env_keys[provider]

    if not api_key:
        raise ValueError(f"API key not found for {provider}. Set {provider.upper()}_API_KEY env variable.")

    cache_key = f"{provider}:{model}"

    if cache_key not in _client_cache:
        if provider == "openai":
            _client_cache[cache_key] = OpenAIClient(api_key=api_key, model=model)
        elif provider == "anthropic":
            _client_cache[cache_key] = AnthropicClient(api_key=api_key, model=model)

    return _client_cache[cache_key]


def estimate_cost(
    provider: str,
    model: str,
    tokens_input: int,
    tokens_output: int,
) -> float:
    """Оценка стоимости запроса"""
    pricing = {}

    if provider == "openai":
        pricing = OpenAIClient.PRICING.get(model, {"input": 0.01, "output": 0.03})
    elif provider == "anthropic":
        pricing = AnthropicClient.PRICING.get(model, {"input": 0.003, "output": 0.015})

    return (
        (tokens_input / 1000) * pricing["input"] +
        (tokens_output / 1000) * pricing["output"]
    )
