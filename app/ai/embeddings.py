"""Embedding provider protocol, offline stub, and local CPU implementation."""

import math
from typing import Any, Protocol

DEFAULT_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384


class EmbeddingProvider(Protocol):
    """Interface for text embedding models."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one vector per input text."""


class StubEmbeddingProvider:
    """Return empty vectors until a local embedding model is configured."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Produce shape-compatible empty placeholder vectors."""

        return [[] for _ in texts]


class LocalEmbeddingProvider:
    """Generate normalized 384-dimensional embeddings on the CPU.

    Sentence Transformers and its model are loaded only when the first
    non-empty batch is embedded. Tests and callers can replace ``_load_model``
    to supply a compatible model object without downloading model weights.
    """

    def __init__(self, model_name: str = DEFAULT_MODEL_NAME) -> None:
        self.model_name = model_name
        self._model: Any | None = None

    def _load_model(self) -> Any:
        """Load Sentence Transformers lazily and explicitly select CPU."""

        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "Install sentence-transformers to use LocalEmbeddingProvider."
            ) from exc
        return SentenceTransformer(self.model_name, device="cpu")

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch, returning one validated vector for each input."""

        if not isinstance(texts, list):
            raise TypeError("texts must be a list of strings")
        if any(not isinstance(text, str) for text in texts):
            raise TypeError("every item in texts must be a string")
        if any(not text.strip() for text in texts):
            raise ValueError("texts must not contain empty or whitespace-only strings")
        if not texts:
            return []

        if self._model is None:
            self._model = self._load_model()

        encoded = self._model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        if hasattr(encoded, "tolist"):
            encoded = encoded.tolist()

        # Accept a one-dimensional result from compatible model adapters when
        # the caller supplied exactly one text.
        if (
            len(texts) == 1
            and isinstance(encoded, (list, tuple))
            and encoded
            and isinstance(encoded[0], (int, float))
        ):
            encoded = [encoded]

        if not isinstance(encoded, (list, tuple)) or len(encoded) != len(texts):
            raise RuntimeError("embedding model returned an unexpected batch shape")

        vectors: list[list[float]] = []
        for vector in encoded:
            if not isinstance(vector, (list, tuple)) or len(vector) != EMBEDDING_DIMENSION:
                raise RuntimeError(
                    f"embedding model must return {EMBEDDING_DIMENSION}-dimensional vectors"
                )
            try:
                values = [float(value) for value in vector]
            except (OverflowError, TypeError, ValueError) as exc:
                raise RuntimeError("embedding model returned non-numeric values") from exc
            if not all(math.isfinite(value) for value in values):
                raise RuntimeError("embedding model returned non-finite values")
            vectors.append(values)
        return vectors
