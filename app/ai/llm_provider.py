"""LLM provider abstraction with a safe placeholder implementation."""

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Interface for extraction and narrative generation, never valuation math."""

    @abstractmethod
    async def generate(self, prompt: str, *, task: str) -> str:
        """Generate text for one named task."""


class StubLLMProvider(LLMProvider):
    """No-model implementation that makes placeholder behavior explicit."""

    async def generate(self, prompt: str, *, task: str) -> str:
        """Return a placeholder response without loading a model."""

        del prompt
        return f"TODO: configure an LLM provider for task '{task}'."
