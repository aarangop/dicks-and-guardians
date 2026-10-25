import asyncio

import pytest

from dont_be_a_dick.domain.rubrics import R1, Dimension, Rubric
from dont_be_a_dick.domain.schemas import (
    Ambiguous,
    DimensionScore,
    Dossier,
    EvidenceItem,
    JudgeVerdict,
    NeedsDisambiguation,
    PersonFacts,
    Refused,
    Resolved,
    Role,
    Scored,
    Subject,
)
from dont_be_a_dick.workflows.scoring import SUMMARY_UNAVAILABLE, ScoringPipeline

R3 = Rubric(
    id="R3",
    name="Extraction",
    prompt_dir="r3",
    dimensions=(Dimension("X1", "Labor", "x"),),
)
SUBJECT = Subject(name="Test Person", descriptor="CEO")


def make_dossier(subject: Subject, rubric: Rubric) -> Dossier:
    tag = rubric.tags[0]
    return Dossier(
        rubric_id=rubric.id,
        subject=subject,
        items=[
            EvidenceItem(
                id=f"{rubric.id}-E01",
                claim="c",
                dimension=tag,
                quote="q",
                source_url="https://example.com",
                source_title="t",
                source_kind="court_record",
                source_tier=1,
            )
        ],
        facts=PersonFacts(
            roles=[Role(title="CEO", organization="X", seniority="founder_or_head_of_state")],
            organization_size="very_large",
        ),
    )


class FakeResolver:
    def __init__(self, resolution) -> None:
        self.resolution = resolution
        self.calls: list[tuple[str, str | None]] = []

    async def resolve(self, name, descriptor=None):
        self.calls.append((name, descriptor))
        return self.resolution


class FakeResearcher:
    def __init__(self, fail_for: set[str] = frozenset(), barrier: asyncio.Barrier | None = None):
        self.fail_for = fail_for
        self.barrier = barrier
        self.calls: list[str] = []

    async def research(self, subject, rubric):
        self.calls.append(rubric.id)
        if self.barrier is not None:
            await asyncio.wait_for(self.barrier.wait(), timeout=2)
        if rubric.id in self.fail_for:
            raise RuntimeError("search down")
        return make_dossier(subject, rubric)


class FakeJudge:
    def __init__(self, severity: int = 3, fail_for: set[str] = frozenset()) -> None:
        self.severity = severity
        self.fail_for = fail_for  # entries are "R1" for harm or "R1 benefit"
        self.calls: list[tuple[str, str, list[str]]] = []

    async def judge(self, dossier, rubric, polarity="harm"):
        self.calls.append((rubric.id, polarity, [i.id for i in dossier.items]))
        label = rubric.id if polarity == "harm" else f"{rubric.id} benefit"
        if label in self.fail_for:
            raise RuntimeError("judge down")
        return JudgeVerdict(
            rubric_id=rubric.id,
            polarity=polarity,
            insufficient_evidence=False,
            dimension_scores=[
                DimensionScore(
                    dimension=rubric.tags[0],
                    severity=self.severity,
                    evidence_ids=[f"{rubric.id}-E01"],
                    rationale="r",
                )
            ],
            rationale="overall",
        )


class FakeSummarizer:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.seen: list = []

    async def summarize(self, subject, breakdown, evidence):
        self.seen.append((subject, breakdown, list(evidence)))
        if self.fail:
            raise RuntimeError("summarizer down")
        return "A summary."


def pipeline(
    *,
    resolution=None,
    researcher=None,
    judge=None,
    summarizer=None,
    rubrics=(R1,),
) -> tuple[ScoringPipeline, FakeResolver, FakeResearcher, FakeSummarizer]:
    resolver = FakeResolver(resolution or Resolved(subject=SUBJECT))
    researcher = researcher or FakeResearcher()
    summarizer = summarizer or FakeSummarizer()
    built = ScoringPipeline(
        resolver=resolver,
        researcher=researcher,
        judge=judge or FakeJudge(),
        summarizer=summarizer,
        rubrics=rubrics,
    )
    return built, resolver, researcher, summarizer


@pytest.mark.anyio
async def test_happy_path_returns_a_scored_report() -> None:
    built, _, _, summarizer = pipeline()

    outcome = await built.run("Test Person")

    assert isinstance(outcome, Scored)
    report = outcome.report
    assert report.subject == SUBJECT
    assert report.tier == "major"
    assert report.breakdown.tier == report.tier
    assert [e.id for e in report.evidence] == ["R1-E01"]
    assert report.summary == "A summary."
    [(_, seen_breakdown, seen_evidence)] = summarizer.seen
    assert seen_breakdown == report.breakdown
    assert [e.id for e in seen_evidence] == ["R1-E01"]


@pytest.mark.anyio
async def test_name_and_descriptor_reach_the_resolver() -> None:
    built, resolver, _, _ = pipeline()

    await built.run("Test Person", "CEO")

    assert resolver.calls == [("Test Person", "CEO")]


@pytest.mark.anyio
async def test_ambiguous_subject_stops_the_run_with_candidates() -> None:
    candidates = [Subject(name="P", descriptor="a"), Subject(name="P", descriptor="b")]
    built, _, researcher, summarizer = pipeline(resolution=Ambiguous(candidates=candidates))

    outcome = await built.run("P")

    assert outcome == NeedsDisambiguation(candidates=candidates)
    assert researcher.calls == []
    assert summarizer.seen == []


@pytest.mark.anyio
async def test_refused_subject_stops_the_run() -> None:
    refused = Refused(reason="private individual")
    built, _, researcher, _ = pipeline(resolution=refused)

    outcome = await built.run("Nobody")

    assert outcome == refused
    assert researcher.calls == []


@pytest.mark.anyio
async def test_researchers_run_concurrently() -> None:
    barrier = asyncio.Barrier(2)  # both must be running at once, or wait_for times out
    built, _, researcher, _ = pipeline(researcher=FakeResearcher(barrier=barrier), rubrics=(R1, R3))

    outcome = await built.run("Test Person")

    assert isinstance(outcome, Scored)
    assert sorted(researcher.calls) == ["R1", "R3"]


@pytest.mark.anyio
async def test_research_concurrency_is_capped() -> None:
    class CountingResearcher(FakeResearcher):
        running = peak = 0

        async def research(self, subject, rubric):
            self.running += 1
            self.peak = max(self.peak, self.running)
            await asyncio.sleep(0.01)
            self.running -= 1
            return make_dossier(subject, rubric)

    researcher = CountingResearcher()
    built = ScoringPipeline(
        resolver=FakeResolver(Resolved(subject=SUBJECT)),
        researcher=researcher,
        judge=FakeJudge(),
        summarizer=FakeSummarizer(),
        rubrics=(R1, R3),
        max_concurrent_research=1,
    )

    outcome = await built.run("Test Person")

    assert isinstance(outcome, Scored)
    assert researcher.peak == 1


@pytest.mark.anyio
async def test_research_failure_for_r1_makes_the_result_unrated() -> None:
    built, *_ = pipeline(researcher=FakeResearcher(fail_for={"R1"}))

    outcome = await built.run("Test Person")

    assert isinstance(outcome, Scored)
    assert outcome.report.tier == "unrated"
    assert any("R1: research failed (RuntimeError)" in n for n in outcome.report.breakdown.notes)


@pytest.mark.anyio
async def test_judge_failure_for_r1_makes_the_result_unrated() -> None:
    built, *_ = pipeline(judge=FakeJudge(fail_for={"R1"}))

    outcome = await built.run("Test Person")

    assert outcome.report.tier == "unrated"
    assert any("judging failed" in n for n in outcome.report.breakdown.notes)


@pytest.mark.anyio
async def test_a_failing_optional_rubric_only_lowers_coverage() -> None:
    built, *_ = pipeline(researcher=FakeResearcher(fail_for={"R3"}), rubrics=(R1, R3))

    outcome = await built.run("Test Person")

    assert outcome.report.tier == "major"
    assert outcome.report.breakdown.coverage == 0.5
    assert any("R3: research failed" in n for n in outcome.report.breakdown.notes)


@pytest.mark.anyio
async def test_summarizer_failure_does_not_lose_the_score() -> None:
    built, *_ = pipeline(summarizer=FakeSummarizer(fail=True))

    outcome = await built.run("Test Person")

    assert isinstance(outcome, Scored)
    assert outcome.report.tier == "major"
    assert outcome.report.summary == SUMMARY_UNAVAILABLE


@pytest.mark.anyio
async def test_resolver_errors_propagate() -> None:
    class BrokenResolver:
        async def resolve(self, name, descriptor=None):
            raise RuntimeError("llm down")

    built = ScoringPipeline(
        resolver=BrokenResolver(),
        researcher=FakeResearcher(),
        judge=FakeJudge(),
        summarizer=FakeSummarizer(),
        rubrics=(R1,),
    )

    with pytest.raises(RuntimeError):
        await built.run("Test Person")


@pytest.mark.anyio
async def test_resolve_alone_does_no_research() -> None:
    built, resolver, researcher, _ = pipeline()

    resolved = await built.resolve("Test Person", "CEO")

    assert resolved == Resolved(subject=SUBJECT)
    assert resolver.calls == [("Test Person", "CEO")]
    assert researcher.calls == []


@pytest.mark.anyio
async def test_resolve_reports_ambiguity_and_refusal_as_outcomes() -> None:
    candidates = [Subject(name="P", descriptor="a"), Subject(name="P", descriptor="b")]
    built, *_ = pipeline(resolution=Ambiguous(candidates=candidates))
    assert await built.resolve("P") == NeedsDisambiguation(candidates=candidates)

    built, *_ = pipeline(resolution=Refused(reason="private"))
    assert await built.resolve("P") == Refused(reason="private")


@pytest.mark.anyio
async def test_score_subject_skips_resolution() -> None:
    built, resolver, researcher, _ = pipeline()

    scored = await built.score_subject(SUBJECT)

    assert isinstance(scored, Scored)
    assert resolver.calls == []
    assert researcher.calls == ["R1"]


def dossier_with_both_sides(subject: Subject, rubric: Rubric) -> Dossier:
    base = make_dossier(subject, rubric)
    good = base.items[0].model_copy(
        update={"id": f"{rubric.id}-E02", "polarity": "benefit", "claim": "resigned"}
    )
    return base.model_copy(update={"items": [*base.items, good]})


class BothSidesResearcher(FakeResearcher):
    async def research(self, subject, rubric):
        await super().research(subject, rubric)
        return dossier_with_both_sides(subject, rubric)


@pytest.mark.anyio
async def test_each_judge_sees_only_its_own_side() -> None:
    judge = FakeJudge()
    built, *_ = pipeline(researcher=BothSidesResearcher(), judge=judge)

    await built.run("Test Person")

    assert sorted(judge.calls) == [("R1", "benefit", ["R1-E02"]), ("R1", "harm", ["R1-E01"])]


@pytest.mark.anyio
async def test_rubrics_without_a_benefit_side_are_judged_once() -> None:
    judge = FakeJudge()
    built, *_ = pipeline(judge=judge, rubrics=(R1, R3))

    await built.run("Test Person")

    assert sorted((rid, side) for rid, side, _ in judge.calls) == [
        ("R1", "benefit"),
        ("R1", "harm"),
        ("R3", "harm"),
    ]


@pytest.mark.anyio
async def test_the_report_carries_both_tiers() -> None:
    built, *_ = pipeline()

    outcome = await built.run("Test Person")

    assert outcome.report.tier == "major"
    assert outcome.report.benefit_tier == outcome.report.breakdown.benefit_tier
    assert outcome.report.benefit_tier != "unrated"


@pytest.mark.anyio
async def test_a_failing_benefit_judge_leaves_the_harm_rating_alone() -> None:
    built, *_ = pipeline(judge=FakeJudge(fail_for={"R1 benefit"}))

    outcome = await built.run("Test Person")

    assert outcome.report.tier == "major"
    assert outcome.report.benefit_tier == "unrated"
    assert any("R1 benefit: judging failed" in n for n in outcome.report.breakdown.notes)
