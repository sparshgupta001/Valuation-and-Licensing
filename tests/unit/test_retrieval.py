"""Tests for assessment-scoped semantic evidence retrieval."""

from types import SimpleNamespace

import pytest

from app.ai.embeddings import EMBEDDING_DIMENSION
from app.ai.retrieval import EvidenceRetriever
from app.ingestion.extracted_document import ExtractedTextSegment


def vector(*values: float) -> list[float]:
    return [*values, *([0.0] * (EMBEDDING_DIMENSION - len(values)))]


class FakeEmbeddingProvider:
    def __init__(self, embeddings: dict[str, list[float]] | None = None) -> None:
        self.embeddings = embeddings or {}
        self.calls: list[list[str]] = []

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(list(texts))
        return [self.embeddings.get(text, vector(1.0)) for text in texts]


def make_document(
    document_id: str,
    text: str,
    *,
    assessment_id: str = "assessment-1",
    role: str = "product_documentation",
) -> SimpleNamespace:
    return SimpleNamespace(
        id=document_id,
        assessment_id=assessment_id,
        filename=f"{document_id}.txt",
        content_type="text/plain",
        role=role,
        content=text.encode("utf-8"),
    )


def test_cross_assessment_documents_are_filtered_before_content_access() -> None:
    provider = FakeEmbeddingProvider()

    class ForeignDocument:
        assessment_id = "assessment-2"

        @property
        def role(self):
            raise AssertionError("foreign document role must not be read")

        @property
        def filename(self):
            raise AssertionError("foreign document filename must not be read")

        @property
        def content_type(self):
            raise AssertionError("foreign document type must not be read")

        @property
        def content(self):
            raise AssertionError("foreign document content must not be read")

    retriever = EvidenceRetriever(
        "assessment-1",
        [ForeignDocument(), make_document("own", "own evidence")],
        provider,
    )

    results = retriever.search("query")

    assert provider.calls == [["own evidence"], ["query"]]
    assert [result.document_id for result in results] == ["own"]
    assert all(result.assessment_id == "assessment-1" for result in results)


def test_target_patent_is_excluded_and_evidence_roles_can_be_filtered() -> None:
    provider = FakeEmbeddingProvider()
    documents = [
        make_document("patent", "patent text", role="target_patent"),
        make_document("product", "product evidence", role="product_documentation"),
        make_document("prior", "prior art evidence", role="reference_prior_art"),
    ]
    retriever = EvidenceRetriever("assessment-1", documents, provider)

    product_results = retriever.search("query", roles=["product_documentation"])
    prior_results = retriever.search("query", roles=["reference_prior_art"])
    patent_results = retriever.search("query", roles=["target_patent"])

    assert [result.document_id for result in product_results] == ["product"]
    assert [result.document_id for result in prior_results] == ["prior"]
    assert patent_results == []
    assert provider.calls[0] == ["prior art evidence", "product evidence"]
    assert "patent text" not in provider.calls[0]
    assert all(result.document_role != "target_patent" for result in product_results + prior_results)


def test_results_are_ranked_by_cosine_similarity() -> None:
    provider = FakeEmbeddingProvider({
        "aligned passage": vector(3.0, 0.0),
        "angled passage": vector(4.0, 3.0),
        "opposite passage": vector(-1.0, 0.0),
        "query": vector(2.0, 0.0),
    })
    retriever = EvidenceRetriever(
        "assessment-1",
        [
            make_document("a", "aligned passage"),
            make_document("b", "angled passage"),
            make_document("c", "opposite passage"),
        ],
        provider,
    )

    results = retriever.search("query")

    assert [result.document_id for result in results] == ["a", "b", "c"]
    assert [result.similarity_score for result in results] == pytest.approx([1.0, 0.8, -1.0])


def test_zero_corpus_vectors_are_skipped_and_zero_query_returns_no_results() -> None:
    provider = FakeEmbeddingProvider({
        "zero passage": vector(),
        "valid passage": vector(1.0),
        "zero query": vector(),
    })
    retriever = EvidenceRetriever(
        "assessment-1",
        [make_document("zero", "zero passage"), make_document("valid", "valid passage")],
        provider,
    )

    assert [item.document_id for item in retriever.search("normal query")] == ["valid"]
    assert retriever.search("zero query") == []


def test_equal_scores_use_document_id_locator_and_offset_for_stable_order() -> None:
    provider = FakeEmbeddingProvider()
    retriever = EvidenceRetriever(
        "assessment-1",
        [make_document("z-document", "same passage"), make_document("a-document", "same passage")],
        provider,
    )

    results = retriever.search("query")

    assert [(item.document_id, item.source_locator, item.start_offset) for item in results] == [
        ("a-document", "text:chars:0-12", 0),
        ("z-document", "text:chars:0-12", 0),
    ]


def test_exact_passage_and_all_provenance_fields_are_preserved(monkeypatch) -> None:
    exact_text = "A  verbatim passage;\nwith exact spacing."
    monkeypatch.setattr(
        "app.ai.retrieval.extract_document_segments",
        lambda *_args: [ExtractedTextSegment(exact_text, "page:7", page_number=7)],
    )
    provider = FakeEmbeddingProvider()
    retriever = EvidenceRetriever(
        "assessment-1",
        [make_document("source-9", "ignored by patched extractor", role="reference_prior_art")],
        provider,
        chunk_size=100,
        overlap=10,
    )

    result = retriever.search("query")[0]

    assert result.assessment_id == "assessment-1"
    assert result.document_id == "source-9"
    assert result.document_name == "source-9.txt"
    assert result.document_role == "reference_prior_art"
    assert result.page_number == 7
    assert result.source_locator == f"page:7:chars:0-{len(exact_text)}"
    assert result.start_offset == 0
    assert result.end_offset == len(exact_text)
    assert result.passage == exact_text
    assert result.similarity_score == pytest.approx(1.0)


def test_empty_corpus_and_blank_query_do_not_call_embedding_provider() -> None:
    provider = FakeEmbeddingProvider()
    retriever = EvidenceRetriever("assessment-1", [], provider)

    assert retriever.search(" ") == []
    assert retriever.search("a real query") == []
    assert provider.calls == []


def test_corpus_is_batched_once_and_only_queries_are_embedded_afterward() -> None:
    provider = FakeEmbeddingProvider()
    retriever = EvidenceRetriever(
        "assessment-1",
        [
            make_document("c", "third"),
            make_document("a", "first"),
            make_document("b", "second"),
        ],
        provider,
        batch_size=2,
    )

    retriever.search("query one")
    retriever.search("query two")

    assert provider.calls == [
        ["first", "second"],
        ["third"],
        ["query one"],
        ["query two"],
    ]


@pytest.mark.parametrize(
    ("output", "error_message"),
    [
        ([], "corpus batch length"),
        ([[]], None),
        ([[1.0, 2.0]], "384-dimensional"),
        ([[float("inf")] * EMBEDDING_DIMENSION], None),
    ],
)
def test_invalid_or_unusable_provider_output_is_handled_safely(output, error_message) -> None:
    class InvalidProvider:
        def embed(self, texts: list[str]):
            if texts == ["passage"]:
                return output
            return [vector(1.0)]

    retriever = EvidenceRetriever(
        "assessment-1",
        [make_document("source", "passage")],
        InvalidProvider(),
    )

    if error_message is None:
        assert retriever.search("query") == []
    else:
        with pytest.raises(ValueError, match=error_message):
            retriever.search("query")


def test_missing_query_embedding_returns_no_results() -> None:
    class MissingQueryProvider:
        def embed(self, texts: list[str]):
            return [vector(1.0)] if texts == ["passage"] else []

    retriever = EvidenceRetriever(
        "assessment-1",
        [make_document("source", "passage")],
        MissingQueryProvider(),
    )

    assert retriever.search("query") == []


@pytest.mark.parametrize(
    ("assessment_id", "exception", "message"),
    [
        (None, TypeError, "assessment_id"),
        ("", ValueError, "assessment_id"),
        ("   ", ValueError, "assessment_id"),
        (" assessment-1", ValueError, "trimmed"),
    ],
)
def test_invalid_assessment_identifiers_are_rejected(assessment_id, exception, message) -> None:
    with pytest.raises(exception, match=message):
        EvidenceRetriever(assessment_id, [], FakeEmbeddingProvider())
