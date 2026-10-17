"""Re-score stored real runs offline.

`scripts/calibrate.py --save` stores each run's dossiers and judge verdicts under
tests/fixtures/runs/. Re-computing the score from them needs no network or LLM, so a
change to scoring weights or tier thresholds that moves a stored tier fails here.
When a change is intended, re-save the fixtures (or edit the expected tier).
"""

import json
from pathlib import Path

import pytest

from dont_be_a_dick.domain.rubrics import RUBRICS
from dont_be_a_dick.domain.schemas import Dossier, JudgeVerdict
from dont_be_a_dick.domain.scoring import compute_score

FIXTURES = sorted((Path(__file__).parent / "fixtures" / "runs").glob("*.json"))


@pytest.mark.parametrize("path", FIXTURES, ids=lambda p: p.stem)
def test_stored_runs_keep_their_tier(path: Path) -> None:
    run = json.loads(path.read_text())
    dossiers = [Dossier.model_validate(d) for d in run["dossiers"]]
    verdicts = [JudgeVerdict.model_validate(v) for v in run["verdicts"]]

    breakdown = compute_score(verdicts, dossiers, RUBRICS)

    assert breakdown.tier == run["tier"]
    assert breakdown.final_score == pytest.approx(run["final_score"])


def test_scoring_is_deterministic_on_stored_runs() -> None:
    for path in FIXTURES:
        run = json.loads(path.read_text())
        dossiers = [Dossier.model_validate(d) for d in run["dossiers"]]
        verdicts = [JudgeVerdict.model_validate(v) for v in run["verdicts"]]

        assert compute_score(verdicts, dossiers, RUBRICS) == compute_score(
            verdicts, dossiers, RUBRICS
        )
