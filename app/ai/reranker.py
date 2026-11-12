"""Reranker interface; model weights are not imported by the scaffold."""

from app.schemas.common import EvidenceItem


class EvidenceReranker:
    """Stable no-op reranker for an empty or unconfigured evidence corpus."""

    def rerank(self, query: str, evidence: list[EvidenceItem], *, limit: int = 5) -> list[EvidenceItem]:
        """Return the first evidence items without claiming relevance."""

        del query
        return evidence[:limit]
