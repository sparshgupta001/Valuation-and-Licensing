"""Evidence retrieval interface; a vector database adapter belongs here."""

from app.schemas.common import EvidenceItem


class EvidenceRetriever:
    """Placeholder retrieval service that never invents evidence."""

    def search(self, query: str, *, limit: int = 5) -> list[EvidenceItem]:
        """Return no passages until an indexed corpus is configured."""

        del query, limit
        return []
