"""Abstraction layer over OpenAI and Anthropic APIs."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ringbot.config import get_api_key


class LLMProvider(ABC):
    """Base class for LLM providers."""

    @abstractmethod
    def chat(self, system_prompt: str, user_message: str) -> str:
        """Send a message and return the assistant's text reply."""


class OpenAIProvider(LLMProvider):
    def __init__(self) -> None:
        from openai import OpenAI
        self._client = OpenAI(api_key=get_api_key("openai"))

    def chat(self, system_prompt: str, user_message: str) -> str:
        response = self._client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.7,
            max_tokens=2000,
        )
        return response.choices[0].message.content or ""


class AnthropicProvider(LLMProvider):
    def __init__(self) -> None:
        from anthropic import Anthropic
        self._client = Anthropic(api_key=get_api_key("anthropic"))

    def chat(self, system_prompt: str, user_message: str) -> str:
        response = self._client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        return response.content[0].text


def get_provider(name: str) -> LLMProvider:
    """Factory: return the requested LLM provider."""
    providers = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
    }
    cls = providers.get(name)
    if cls is None:
        raise ValueError(f"Unknown provider '{name}'. Choose from: {list(providers)}")
    return cls()
