"""Build provisional independent-claim charts with retrieved source passages."""

from collections.abc import Iterable
from typing import Any

from app.ai.embeddings import EmbeddingProvider, LocalEmbeddingProvider
from app.ai.retrieval import EvidenceRetriever
from app.schemas.intelligence import (
    ClaimAssessment,
    ClaimChart,
    ClaimChartEvidence,
    ClaimChartRow,
    EvidenceRetrievalStatus,
)
from app.schemas.patent import PatentProfile

_EVIDENCE_ROLES = ("product_documentation", "reference_prior_art")


async def build_claim_charts(
    profile: PatentProfile,
    *,
    assessment_id: str | None = None,
    evidence_documents: Iterable[Any] = (),
    embedding_provider: EmbeddingProvider | None = None,
) -> list[ClaimChart]:
    """Build GAP-only charts and retrieve source passages for each limitation.

    One assessment-scoped retriever is built for this chart operation and reused
    across all independent-claim limitations. Retrieval failures leave the
    chart rows intact with empty evidence and mandatory human review.
    """

    limitations_by_claim = [
        (claim, claim.limitations or ["TODO: split independent claim into limitations."])
        for claim in profile.claims
        if claim.independent
    ]
    if not limitations_by_claim:
        return []

    retriever: EvidenceRetriever | None = None
    if assessment_id is not None:
        try:
            retriever = EvidenceRetriever(
                assessment_id,
                evidence_documents,
                embedding_provider if embedding_provider is not None else LocalEmbeddingProvider(),
            )
        except Exception:
            # Preserve the legacy provisional chart if index preparation fails.
            retriever = None

    charts: list[ClaimChart] = []
    for claim, limitations in limitations_by_claim:
        rows: list[ClaimChartRow] = []
        for limitation in limitations:
            retrieved_items: list[ClaimChartEvidence] = []
            if retriever is None:
                retrieval_status = EvidenceRetrievalStatus.UNAVAILABLE
            else:
                try:
                    retrieved = retriever.search(limitation, roles=_EVIDENCE_ROLES)
                    retrieved_items = [
                        ClaimChartEvidence(
                            assessment_id=item.assessment_id,
                            document_id=item.document_id,
                            document_name=item.document_name,
                            document_role=item.document_role,
                            page=item.page_number,
                            source_locator=item.source_locator,
                            start_offset=item.start_offset,
                            end_offset=item.end_offset,
                            passage=item.passage,
                            similarity_score=item.similarity_score,
                        )
                        for item in retrieved
                    ]
                    retrieval_status = (
                        EvidenceRetrievalStatus.AVAILABLE
                        if retrieved_items
                        else EvidenceRetrievalStatus.NO_RESULTS
                    )
                except Exception:
                    # A model/download or retrieval error must not remove chart rows.
                    retrieved_items = []
                    retrieval_status = EvidenceRetrievalStatus.UNAVAILABLE
                    retriever = None

            rows.append(ClaimChartRow(
                claim_number=claim.claim_number,
                limitation=limitation,
                assessment=ClaimAssessment.GAP,
                explanation=_row_explanation(retrieval_status),
                confidence=0.0,
                evidence=retrieved_items,
                needs_human_review=True,
                retrieval_status=retrieval_status,
            ))
        charts.append(ClaimChart(
            claim_number=claim.claim_number,
            rows=rows,
            needs_human_review=True,
        ))
    return charts


def _row_explanation(status: EvidenceRetrievalStatus) -> str:
    """Explain retrieval state without turning similarity into a finding."""

    if status is EvidenceRetrievalStatus.AVAILABLE:
        return (
            "Similarity-ranked passages are supplied for human review only; they do not establish "
            "coverage. The provisional GAP status and zero confidence remain unchanged."
        )
    if status is EvidenceRetrievalStatus.NO_RESULTS:
        return (
            "Evidence retrieval completed without relevant passages. The provisional GAP status "
            "and zero confidence remain unchanged and require human review."
        )
    return (
        "Evidence retrieval was unavailable. The provisional GAP status and zero confidence remain "
        "unchanged and require human review."
    )
