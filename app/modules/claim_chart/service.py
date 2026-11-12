"""Claim chart interface with conservative, reviewable placeholder rows."""

from app.schemas.intelligence import ClaimAssessment, ClaimChart, ClaimChartRow
from app.schemas.patent import PatentProfile


async def build_claim_charts(profile: PatentProfile) -> list[ClaimChart]:
    """Create one provisional chart for each independent claim."""

    charts: list[ClaimChart] = []
    for claim in profile.claims:
        if not claim.independent:
            continue
        limitations = claim.limitations or ["TODO: split independent claim into limitations."]
        rows = [
            ClaimChartRow(
                claim_number=claim.claim_number,
                limitation=limitation,
                assessment=ClaimAssessment.GAP,
                explanation="No evidence corpus is configured; label is provisional and requires human review.",
                confidence=0.0,
                evidence=[],
                needs_human_review=True,
            )
            for limitation in limitations
        ]
        charts.append(ClaimChart(claim_number=claim.claim_number, rows=rows, needs_human_review=True))
    return charts
