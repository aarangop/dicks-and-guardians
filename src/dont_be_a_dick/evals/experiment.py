"""Judge-level experiments: frozen dossiers in, verdicts and tier out, compared to the golden case.

Only the judge varies (model, prompt variant). Dossiers are frozen, so differences between
runs come from the configuration under test and not from search nondeterminism.
"""

import asyncio
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from langfuse import Evaluation

from dont_be_a_dick import dependencies as deps
from dont_be_a_dick.agents.judge import LangChainJudge
from dont_be_a_dick.config import Settings
from dont_be_a_dick.domain.rubrics import RUBRICS, Rubric
from dont_be_a_dick.domain.schemas import Dossier, JudgeVerdict, Polarity
from dont_be_a_dick.domain.scoring import compute_score
from dont_be_a_dick.prompts import rubric_prompt

MAX_SEVERITY = 4


@dataclass(frozen=True)
class ExperimentConfig:
    """What an experiment varies. `None` keeps the app's own setting or prompt."""

    judge_model: str | None = None
    prompt_root: Path | None = None
    """A prompt variant laid out like `dont_be_a_dick/prompts` (see `rubric_prompt`)."""
    label: str = "default"

    def metadata(self, settings: Settings) -> dict[str, Any]:
        return {
            "label": self.label,
            "judge_model": self.judge_model or settings.model_for("judge"),
            "prompt_root": str(self.prompt_root) if self.prompt_root else "packaged",
            "git_commit": _git_commit(),
        }


def _git_commit() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return out.stdout.strip()


def build_judge(config: ExperimentConfig, settings: Settings) -> LangChainJudge:
    if config.judge_model:
        settings = settings.model_copy(update={"judge_model": config.judge_model})
    root = config.prompt_root

    def prompt_for(rubric: Rubric, polarity: Polarity) -> str:
        return rubric_prompt(rubric, "judge" if polarity == "harm" else "judge_benefit", root=root)

    return LangChainJudge(
        deps.get_judge_model(settings),
        prompt_for=prompt_for,
        structured_output_kwargs=deps.JUDGE_STRUCTURED_OUTPUT,
    )


async def judge_case(
    judge: LangChainJudge,
    dossiers: Sequence[Dossier],
    rubrics: Sequence[Rubric] = RUBRICS,
) -> dict[str, Any]:
    """Judge every dossier on each side, then score, as `ScoringPipeline` does."""
    by_id = {d.rubric_id: d for d in dossiers}
    jobs: list[tuple[Rubric, Polarity]] = [
        (rubric, polarity)
        for rubric in rubrics
        if rubric.id in by_id
        for polarity in (("harm", "benefit") if rubric.has_benefit else ("harm",))
    ]
    results = await asyncio.gather(
        *(judge.judge(by_id[r.id].with_polarity(p), r, p) for r, p in jobs),
        return_exceptions=True,
    )
    verdicts: list[JudgeVerdict] = []
    failures: list[str] = []
    for (rubric, polarity), result in zip(jobs, results, strict=True):
        if isinstance(result, BaseException):
            failures.append(f"{rubric.id}/{polarity}: {type(result).__name__}")
        else:
            verdicts.append(result)

    judged = [r for r in rubrics if r.id in by_id]
    breakdown = compute_score(verdicts, list(by_id.values()), judged)
    return {
        "tier": breakdown.tier,
        "final_score": breakdown.final_score,
        "severities": {
            v.rubric_id: {s.dimension: s.severity for s in v.dimension_scores}
            for v in verdicts
            if v.polarity == "harm" and not v.insufficient_evidence
        },
        "failures": failures,
    }


# --- evaluators (pure; no LLM) ----------------------------------------------


def tier_match(*, output: dict, expected_output: dict, **_: Any) -> Evaluation:
    hit = output["tier"] == expected_output["tier"]
    return Evaluation(
        name="tier_match",
        value=1.0 if hit else 0.0,
        comment=f"got {output['tier']}, expected {expected_output['tier']}",
    )


def score_error(*, output: dict, expected_output: dict, **_: Any) -> Evaluation | None:
    got, want = output["final_score"], expected_output.get("final_score")
    if want is None:
        return None
    if got is None:
        return Evaluation(name="score_abs_error", value=1.0, comment="no score produced")
    return Evaluation(
        name="score_abs_error", value=abs(got - want), comment=f"{got:.2f} vs {want:.2f}"
    )


def severity_mae(*, output: dict, expected_output: dict, **_: Any) -> Evaluation | None:
    """Mean absolute severity gap over the expected dimensions; a missing dimension costs the
    maximum gap, so a judge cannot score well by skipping dimensions."""
    gaps: list[int] = []
    for rubric_id, dims in expected_output.get("severities", {}).items():
        got = output["severities"].get(rubric_id, {})
        gaps += [abs(got[d] - want) if d in got else MAX_SEVERITY for d, want in dims.items()]
    if not gaps:
        return None
    return Evaluation(
        name="severity_mae", value=sum(gaps) / len(gaps), comment=f"{len(gaps)} dimensions"
    )


def judge_failures(*, output: dict, **_: Any) -> Evaluation:
    return Evaluation(
        name="judge_failures",
        value=float(len(output["failures"])),
        comment=", ".join(output["failures"]),
    )


EVALUATORS = [tier_match, score_error, severity_mae, judge_failures]
