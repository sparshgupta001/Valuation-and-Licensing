"""Parallel assessment workflow with optional LangGraph compilation."""

import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Annotated, Any, TypedDict

from app.modules.claim_chart.service import build_claim_charts
from app.modules.competitor_intelligence.service import find_competitor_targets
from app.modules.negotiation.service import build_negotiation_brief
from app.modules.patent_intelligence.service import build_patent_profile
from app.modules.valuation.service import value_assessment
from app.reports.builder import build_report
from app.schemas.assessment import AssessmentCreate, CommercialInfo
from app.schemas.common import StepState, StepStatus
from app.schemas.report import AssessmentResults

STEP_NAMES = (
    "patent_intelligence",
    "competitor_intelligence",
    "claim_chart",
    "valuation",
    "negotiation",
    "report_builder",
    "human_review_checkpoint",
)


def _utc_now() -> datetime:
    """Return a timezone-aware timestamp for workflow records."""

    return datetime.now(timezone.utc)


def _merge_statuses(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    """Merge independent LangGraph branch step-status updates."""

    return {**left, **right}


class AssessmentGraphState(TypedDict, total=False):
    """Values passed between graph nodes."""

    assessment_id: str
    assessment: AssessmentCreate
    commercial_info: CommercialInfo
    patent_text: str
    patent_profile: Any
    competitors: Any
    claim_charts: Any
    valuation: Any
    negotiation: Any
    report: Any
    step_statuses: Annotated[dict[str, Any], _merge_statuses]
    human_review_pending: bool
    errors: list[str]


class WorkflowOutcome(TypedDict):
    """Outputs persisted by the assessment service."""

    results: AssessmentResults
    steps: list[StepStatus]
    human_review_pending: bool


async def run_assessment_workflow(
    assessment_id: str,
    assessment: AssessmentCreate,
    commercial_info: CommercialInfo,
    *,
    patent_text: str = "",
) -> WorkflowOutcome:
    """Execute Patent Intelligence, parallel branches, dependent steps, and review."""

    results = AssessmentResults()
    statuses: dict[str, StepStatus] = {
        name: StepStatus(name=name, state=StepState.PENDING) for name in STEP_NAMES
    }
    errors: list[str] = []

    async def run_step(name: str, operation: Callable[[], Awaitable[Any]]) -> Any:
        """Run one step, recording its state and allowing partial completion."""

        started = _utc_now()
        statuses[name] = StepStatus(name=name, state=StepState.RUNNING, started_at=started)
        await asyncio.sleep(0)  # Yield so sibling branches can start concurrently.
        try:
            output = await operation()
        except Exception as exc:  # Partial results are kept; errors are reportable.
            finished = _utc_now()
            statuses[name] = StepStatus(
                name=name, state=StepState.FAILED, started_at=started,
                completed_at=finished, error=f"{type(exc).__name__}: {exc}",
            )
            errors.append(f"{name}: {type(exc).__name__}: {exc}")
            return None
        statuses[name] = StepStatus(
            name=name, state=StepState.COMPLETED, started_at=started, completed_at=_utc_now()
        )
        return output

    profile = await run_step("patent_intelligence", lambda: build_patent_profile(assessment, patent_text))
    results.patent_profile = profile

    if profile is None:
        for name in ("competitor_intelligence", "claim_chart"):
            statuses[name] = StepStatus(name=name, state=StepState.SKIPPED, error="Patent profile unavailable.")
        competitors, charts = [], []
    else:
        competitor_task = run_step("competitor_intelligence", lambda: find_competitor_targets(profile))
        chart_task = run_step("claim_chart", lambda: build_claim_charts(profile))
        valuation_task = run_step("valuation", lambda: _run_valuation(assessment_id, commercial_info))
        competitors, charts, valuation = await asyncio.gather(competitor_task, chart_task, valuation_task)
    if profile is None:
        valuation = await run_step("valuation", lambda: _run_valuation(assessment_id, commercial_info))
    results.competitors = competitors or []
    results.claim_charts = charts or []
    results.valuation = valuation

    if valuation is None:
        negotiation = None
        statuses["negotiation"] = StepStatus(name="negotiation", state=StepState.SKIPPED, error="Valuation unavailable.")
    else:
        negotiation = await run_step(
            "negotiation",
            lambda: build_negotiation_brief(assessment_id, valuation, commercial_info),
        )
    results.negotiation = negotiation

    report = await run_step("report_builder", lambda: _build_report(assessment_id, assessment, results))
    results.report = report
    await run_step("human_review_checkpoint", _checkpoint)
    results.errors = errors
    return {
        "results": results,
        "steps": [statuses[name] for name in STEP_NAMES],
        "human_review_pending": True,
    }


async def _run_valuation(assessment_id: str, commercial_info: CommercialInfo) -> Any:
    """Run CPU-only deterministic valuation in the valuation branch."""

    return value_assessment(assessment_id, commercial_info)


async def _build_report(assessment_id: str, assessment: AssessmentCreate, results: AssessmentResults) -> Any:
    """Build the final report after the required branches have settled."""

    return build_report(assessment_id, assessment, results)


async def _checkpoint() -> bool:
    """Signal that reviewable AI and placeholder outputs await human review."""

    return True


def build_langgraph():
    """Compile the equivalent LangGraph when the optional package is installed."""

    try:
        from langgraph.graph import END, START, StateGraph
    except ImportError as exc:
        raise RuntimeError("Install LangGraph to compile the optional StateGraph adapter.") from exc

    builder = StateGraph(AssessmentGraphState)

    async def patent_node(state: AssessmentGraphState) -> dict[str, Any]:
        """Create the initial profile node result."""

        profile = await build_patent_profile(state["assessment"], state.get("patent_text", ""))
        return {"patent_profile": profile, "step_statuses": {"patent_intelligence": StepState.COMPLETED.value}}

    async def competitor_node(state: AssessmentGraphState) -> dict[str, Any]:
        """Find commercially evidenced target candidates."""

        profile = state.get("patent_profile")
        output = await find_competitor_targets(profile) if profile else []
        return {"competitors": output, "step_statuses": {"competitor_intelligence": StepState.COMPLETED.value}}

    async def chart_node(state: AssessmentGraphState) -> dict[str, Any]:
        """Build reviewable claim chart rows."""

        profile = state.get("patent_profile")
        output = await build_claim_charts(profile) if profile else []
        return {"claim_charts": output, "step_statuses": {"claim_chart": StepState.COMPLETED.value}}

    async def valuation_node(state: AssessmentGraphState) -> dict[str, Any]:
        """Calculate valuation independently of the intelligence branches."""

        output = value_assessment(state["assessment_id"], state["commercial_info"])
        return {"valuation": output, "step_statuses": {"valuation": StepState.COMPLETED.value}}

    async def negotiation_node(state: AssessmentGraphState) -> dict[str, Any]:
        """Wait for valuation and competitor outputs before negotiation."""

        output = await build_negotiation_brief(state["assessment_id"], state["valuation"], state["commercial_info"])
        return {"negotiation": output, "step_statuses": {"negotiation": StepState.COMPLETED.value}}

    async def report_node(state: AssessmentGraphState) -> dict[str, Any]:
        """Assemble the final report after negotiation and claim chart outputs."""

        results = AssessmentResults(
            patent_profile=state.get("patent_profile"), competitors=state.get("competitors", []),
            claim_charts=state.get("claim_charts", []), valuation=state.get("valuation"),
            negotiation=state.get("negotiation"),
        )
        report = build_report(state["assessment_id"], state["assessment"], results)
        return {"report": report, "step_statuses": {"report_builder": StepState.COMPLETED.value}}

    async def review_node(state: AssessmentGraphState) -> dict[str, Any]:
        """End at a human-review checkpoint after report assembly."""

        del state
        return {"human_review_pending": True, "step_statuses": {"human_review_checkpoint": StepState.COMPLETED.value}}

    builder.add_node("patent_intelligence", patent_node)
    builder.add_node("competitor_intelligence", competitor_node)
    builder.add_node("claim_chart", chart_node)
    builder.add_node("valuation", valuation_node)
    builder.add_node("negotiation", negotiation_node)
    builder.add_node("report_builder", report_node)
    builder.add_node("human_review_checkpoint", review_node)
    builder.add_edge(START, "patent_intelligence")
    builder.add_edge("patent_intelligence", "competitor_intelligence")
    builder.add_edge("patent_intelligence", "claim_chart")
    builder.add_edge("patent_intelligence", "valuation")
    builder.add_edge(["competitor_intelligence", "valuation"], "negotiation")
    builder.add_edge(["negotiation", "claim_chart"], "report_builder")
    builder.add_edge("report_builder", "human_review_checkpoint")
    builder.add_edge("human_review_checkpoint", END)
    return builder.compile()
