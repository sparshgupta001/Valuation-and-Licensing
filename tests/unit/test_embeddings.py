"""Offline tests for the local embedding provider."""

import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.ai.embeddings import (
    DEFAULT_MODEL_NAME,
    EMBEDDING_DIMENSION,
    LocalEmbeddingProvider,
    StubEmbeddingProvider,
)


class FakeModel:
    def __init__(self, vectors: list[list[float]]) -> None:
        self.vectors = vectors
        self.encode = Mock(return_value=vectors)


def vector(value: float) -> list[float]:
    return [value] * EMBEDDING_DIMENSION


def test_model_load_is_lazy_and_empty_batch_does_not_load() -> None:
    provider = LocalEmbeddingProvider()
    provider._load_model = Mock(return_value=FakeModel([]))  # type: ignore[method-assign]

    assert provider.embed([]) == []
    provider._load_model.assert_not_called()


def test_single_text_and_batches_return_384_dimension_vectors() -> None:
    model = FakeModel([])
    model.encode = Mock(side_effect=[[vector(0.25)], [vector(0.5), vector(0.75)]])
    provider = LocalEmbeddingProvider()
    provider._load_model = Mock(return_value=model)  # type: ignore[method-assign]
    provider._load_model.assert_not_called()

    single = provider.embed(["one passage"])
    batch = provider.embed(["first passage", "second passage"])

    assert len(single) == 1
    assert single[0] == vector(0.25)
    assert len(batch) == 2
    assert all(len(item) == EMBEDDING_DIMENSION for item in batch)
    assert all(isinstance(value, float) for item in batch for value in item)
    assert provider._load_model.call_count == 1
    assert model.encode.call_args_list[0].args == (["one passage"],)
    assert model.encode.call_args_list[1].kwargs == {
        "convert_to_numpy": True,
        "normalize_embeddings": True,
        "show_progress_bar": False,
    }


def test_model_loader_selects_cpu_and_default_model(monkeypatch) -> None:
    constructor = Mock(return_value=object())
    monkeypatch.setitem(
        sys.modules,
        "sentence_transformers",
        SimpleNamespace(SentenceTransformer=constructor),
    )

    provider = LocalEmbeddingProvider()
    provider._load_model()

    constructor.assert_called_once_with(DEFAULT_MODEL_NAME, device="cpu")


@pytest.mark.parametrize("invalid", [None, "a string", 4])
def test_non_list_input_raises_type_error(invalid) -> None:
    provider = LocalEmbeddingProvider()
    with pytest.raises(TypeError, match="list of strings"):
        provider.embed(invalid)  # type: ignore[arg-type]


def test_non_string_and_blank_items_are_rejected_before_loading() -> None:
    provider = LocalEmbeddingProvider()
    provider._load_model = Mock()  # type: ignore[method-assign]

    with pytest.raises(TypeError, match="every item"):
        provider.embed(["valid", 42])  # type: ignore[list-item]
    with pytest.raises(ValueError, match="empty or whitespace-only"):
        provider.embed([" \n"])

    provider._load_model.assert_not_called()


@pytest.mark.parametrize(
    ("model_output", "message"),
    [
        ([vector(0.1)], "batch shape"),
        ([[1.0, 2.0]], "384-dimensional"),
        ([[float("nan")] * EMBEDDING_DIMENSION], "non-finite"),
    ],
)
def test_invalid_model_output_is_rejected(model_output, message: str) -> None:
    provider = LocalEmbeddingProvider()
    provider._load_model = Mock(return_value=FakeModel(model_output))  # type: ignore[method-assign]

    with pytest.raises(RuntimeError, match=message):
        provider.embed(["one", "two"] if message == "batch shape" else ["one"])


def test_stub_provider_remains_compatible() -> None:
    assert StubEmbeddingProvider().embed(["one", "two"]) == [[], []]
