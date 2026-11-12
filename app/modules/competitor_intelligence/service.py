"""Competitor ranking interface; patent similarity alone is never sufficient."""

from app.schemas.patent import PatentProfile
from app.schemas.intelligence import CompetitorTarget


async def find_competitor_targets(profile: PatentProfile) -> list[CompetitorTarget]:
    """Return no candidates until company activity and commercial evidence exist."""

    del profile
    # TODO: blend semantic patent similarity with independently sourced company
    # activity, commercial relevance, and citations for each claim in the ranking.
    return []
