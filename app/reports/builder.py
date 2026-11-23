"""Assemble report sections from module outputs without inventing evidence."""

from app.schemas.assessment import AssessmentCreate
from app.schemas.intelligence import EvidenceRetrievalStatus
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
    retrieval_summary = _retrieval_summary(
        results,
        bool(independent_claims),
        profile_available=profile is not None,
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
                f"charted. {dependent_claim_note} {retrieval_summary}"
                if profile and parsed_claim_count
                else "No numbered claims were parsed (0 parsed, 0 independent, 0 dependent; 0 independent "
                f"charts). Review the uploaded patent and extraction output. {retrieval_summary}"
                if profile
                else f"Patent profile is unavailable. Claim counts cannot be confirmed. {retrieval_summary}"
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
                f"independent claim chart(s). {retrieval_summary} Similarity-ranked passages are "
                "for evidence discovery only and do not establish coverage; all rows remain provisional GAP with zero confidence "
                "and require human review."
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


def _retrieval_summary(
    results: AssessmentResults,
    has_independent_claims: bool,
    *,
    profile_available: bool,
) -> str:
    """Describe chart retrieval outcomes without conflating absence and failure."""

    rows = [row for chart in results.claim_charts for row in chart.rows]
    if not rows:
        if not profile_available:
            return "Evidence retrieval is unavailable because the patent profile is unavailable."
        if has_independent_claims:
            return "Evidence retrieval is unavailable because no claim-chart rows were generated."
        return "Evidence retrieval was not run because no independent claim limitations were available."

    available = sum(row.retrieval_status is EvidenceRetrievalStatus.AVAILABLE for row in rows)
    no_results = sum(row.retrieval_status is EvidenceRetrievalStatus.NO_RESULTS for row in rows)
    unavailable = sum(row.retrieval_status is EvidenceRetrievalStatus.UNAVAILABLE for row in rows)
    passage_count = sum(len(row.evidence) for row in rows)

    outcomes: list[str] = []
    if available:
        outcomes.append(
            f"{passage_count} similarity-ranked passage(s) were returned for {available} limitation(s)"
        )
    if no_results:
        outcomes.append(
            f"retrieval completed with no relevant passages for {no_results} limitation(s)"
        )
    if unavailable:
        outcomes.append(f"retrieval was unavailable for {unavailable} limitation(s)")
    return "Evidence retrieval: " + "; ".join(outcomes) + "."
