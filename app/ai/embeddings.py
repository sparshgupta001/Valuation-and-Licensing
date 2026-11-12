"""Embedding provider protocol and deterministic offline stub."""

from typing import Protocol


class EmbeddingProvider(Protocol):
    """Interface for text embedding models."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one vector per input text."""


class StubEmbeddingProvider:
    """Return empty vectors until a local embedding model is configured."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Produce shape-compatible empty placeholder vectors."""

        return [[] for _ in texts]
