"""Assemble report sections from module outputs without inventing evidence."""

from app.schemas.assessment import AssessmentCreate
from app.schemas.report import AssessmentReport, AssessmentResults, ReportSection


def build_report(
    assessment_id: str,
    assessment: AssessmentCreate,
    results: AssessmentResults,
) -> AssessmentReport:
    """Build the nine report sections with transparent gaps and review flags."""

    profile = results.patent_profile
    valuation = results.valuation
    negotiation = results.negotiation
    competitor_count = len(results.competitors)
    chart_count = sum(len(chart.rows) for chart in results.claim_charts)
    missing = list(negotiation.missing_inputs) if negotiation else []
    if valuation:
        missing.extend(method.method for method in valuation.methods if not method.available)

    return AssessmentReport(
        assessment_id=assessment_id,
        patent_overview=ReportSection(
            title="Patent overview",
            summary=f"{assessment.title} ({assessment.application_number}); owner: {assessment.owner_name or 'not provided'}.",
            confidence=profile.confidence if profile else 0.0,
        ),
        patent_intelligence=ReportSection(
            title="Patent intelligence",
            summary=(f"Profile includes {len(profile.claims)} claim record(s). Extraction is a placeholder pending document analysis." if profile else "Patent profile is unavailable."),
            confidence=profile.confidence if profile else 0.0,
        ),
        competitor_landscape=ReportSection(
            title="Competitor landscape",
            summary=(f"{competitor_count} evidence-qualified licensing target(s) returned. Empty results mean no supported candidate is available in this scaffold."),
            confidence=0.0,
        ),
        claim_charts=ReportSection(
            title="Claim charts",
            summary=f"{chart_count} provisional limitation row(s); all labels require human review.",
            confidence=0.0,
        ),
        ip_valuation=ReportSection(
            title="IP valuation",
            summary=(f"Combined estimate: {valuation.combined_estimate} {valuation.percentiles.currency}." if valuation and valuation.combined_estimate is not None else "No combined estimate; required financial inputs are missing."),
            evidence=[],
            confidence=valuation.confidence if valuation else 0.0,
        ),
        patent_strength=ReportSection(
            title="Patent strength",
            summary=(f"Weighted score: {valuation.patent_strength_score:.1f}/100." if valuation and valuation.patent_strength_score is not None else "No strength score; expert rubric inputs are missing."),
        ),
        licensing_strategy=ReportSection(
            title="Licensing strategy",
            summary=(f"Objective: {assessment.licensing_objective or 'not provided'}. Candidate outreach should wait for commercial evidence and human review."),
        ),
        negotiation_strategy=ReportSection(
            title="Negotiation strategy",
            summary=(f"Deterministic royalty corridor available: {negotiation.target_low_rate is not None}." if negotiation else "Negotiation output is unavailable."),
        ),
        recommendations=ReportSection(
            title="Recommendations",
            summary=("Risks: source evidence and commercial inputs remain unverified. Next steps: validate patent extraction, add market and royalty evidence, and review each provisional claim chart." + (f" Missing inputs: {', '.join(sorted(set(missing)))}." if missing else "")),
        ),
    )
