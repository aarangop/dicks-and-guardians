"""End-to-end runs of the real pipeline (OpenRouter + Tavily). Slow and costs credits."""

import pytest

from dont_be_a_dick import dependencies as deps
from dont_be_a_dick.config import Settings
from dont_be_a_dick.domain.rubrics import R1
from dont_be_a_dick.domain.schemas import DickScoreReport, Scored
from dont_be_a_dick.workflows.scoring import SUMMARY_UNAVAILABLE

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def pipeline():
    settings = Settings()
    if not (
        settings.openrouter_api_key.get_secret_value()
        and settings.tavily_api_key.get_secret_value()
    ):
        pytest.skip("DBAD_OPENROUTER_API_KEY and DBAD_TAVILY_API_KEY must be set")
    # One rubric is enough to exercise the machinery; the research agents differ only by prompt.
    return deps.build_scoring_pipeline(settings, rubrics=(R1,))


def assert_sound(report: DickScoreReport) -> None:
    """Structure and traceability, independent of what the models concluded."""
    assert report.tier == report.breakdown.tier != "unrated"
    assert 0 <= report.breakdown.confidence <= 1
    assert report.summary and report.summary != SUMMARY_UNAVAILABLE

    evidence_ids = {e.id for e in report.evidence}
    assert len(evidence_ids) == len(report.evidence), "evidence ids must be unique"
    for item in report.evidence:
        assert item.source_url.startswith("http")
        assert item.source_tier in (1, 2, 3)
    for rubric_score in report.breakdown.rubric_scores:
        assert set(rubric_score.evidence_ids) <= evidence_ids, "score cites unknown evidence"


@pytest.mark.anyio
async def test_real_pipeline_orders_a_low_and_a_high_case(pipeline) -> None:
    # Sequential, to stay under API rate limits.
    low = await pipeline.run("Peter Singer", "Australian moral philosopher")
    high = await pipeline.run("Elon Musk")

    assert isinstance(low, Scored)
    assert isinstance(high, Scored)
    assert_sound(low.report)
    assert_sound(high.report)
    assert low.report.breakdown.final_score < high.report.breakdown.final_score
    assert low.report.tier in ("not_a_dick", "minor")
    # the high case cites real evidence for what it concluded
    top = max(high.report.breakdown.rubric_scores, key=lambda s: s.severity or 0)
    assert top.severity and top.severity >= 1
    assert top.evidence_ids
