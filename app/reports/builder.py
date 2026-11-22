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
    profile_claims = profile.claims if profile else []
    parsed_claim_count = len(profile_claims)
    independent_claims = [claim for claim in profile_claims if claim.independent]
    dependent_claim_count = parsed_claim_count - len(independent_claims)
    charted_claim_numbers = {chart.claim_number for chart in results.claim_charts}
    charted_independent_count = sum(
        claim.claim_number in charted_claim_numbers for claim in independent_claims
    )
    dependent_claim_note = (
        f"{dependent_claim_count} dependent claim(s) were extracted but are not independently charted in this version."
        if dependent_claim_count
        else "No dependent claims were parsed; only independent claims receive charts in this version."
    )
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
            summary=(
                f"Parsed {parsed_claim_count} claim(s): {len(independent_claims)} independent and "
                f"{dependent_claim_count} dependent. {charted_independent_count} independent claim(s) "
                f"charted. {dependent_claim_note} Evidence retrieval and matching are not configured; chart rows are "
                "provisional and require human review."
                if profile and parsed_claim_count
                else "No numbered claims were parsed (0 parsed, 0 independent, 0 dependent; 0 independent "
                "charts). Review the uploaded patent and extraction output. Evidence retrieval and "
                "matching are not configured; human review is required."
                if profile
                else "Patent profile is unavailable. Claim counts cannot be confirmed, and evidence "
                "retrieval and matching are not configured."
            ),
            confidence=profile.confidence if profile else 0.0,
        ),
        competitor_landscape=ReportSection(
            title="Competitor landscape",
            summary=(f"{competitor_count} evidence-qualified licensing target(s) returned. Empty results mean no supported candidate is available in this scaffold."),
            confidence=0.0,
        ),
        claim_charts=ReportSection(
            title="Claim charts",
            summary=(
                f"{chart_count} provisional limitation row(s) across {charted_independent_count} "
                "independent claim chart(s). Evidence retrieval and matching are not configured; "
                "all labels require human review."
            ),
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
            summary=("Risks: source evidence and commercial inputs remain unverified. Next steps: validate extracted claims, add market and royalty evidence, and review each provisional claim chart." + (f" Missing inputs: {', '.join(sorted(set(missing)))}." if missing else "")),
        ),
    )
