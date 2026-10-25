"""Golden cases: frozen dossiers plus what a calibrated judge should conclude from them.

Cases live as JSON under `evals/golden/` (the source of truth, versioned in git) and are
mirrored into a Langfuse dataset by `scripts/sync_golden.py`.
"""

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from dont_be_a_dick.domain.schemas import Dossier, JudgeVerdict, Subject, Tier
from dont_be_a_dick.domain.slug import slugify

GOLDEN_DIR = Path(__file__).resolve().parents[3] / "evals" / "golden"

Status = Literal["baseline", "calibrated"]
"""`baseline`: expectations copied from a model run, not yet reviewed. `calibrated`: a human
reviewed them. Only calibrated cases say anything about correctness."""


class Expected(BaseModel):
    tier: Tier
    final_score: float | None = None
    severities: dict[str, dict[str, int]] = Field(
        default_factory=dict,
        description="Harm-side severity per rubric id, then dimension tag",
    )


class GoldenCase(BaseModel):
    subject: Subject
    status: Status = "baseline"
    notes: str = ""
    dossiers: list[Dossier]
    expected: Expected

    @property
    def id(self) -> str:
        return slugify(self.subject.name)

    def dataset_input(self) -> dict:
        return {
            "subject": self.subject.model_dump(mode="json"),
            "dossiers": [d.model_dump(mode="json") for d in self.dossiers],
        }

    def dataset_metadata(self) -> dict:
        return {"status": self.status, "notes": self.notes}


def from_run(run: dict, *, status: Status = "baseline") -> GoldenCase:
    """Turn a stored run (`tests/fixtures/runs/*.json`) into a case whose expectations are
    that run's own verdicts. Review them by hand and set `status` to `calibrated`."""
    severities: dict[str, dict[str, int]] = {}
    for raw in run["verdicts"]:
        verdict = JudgeVerdict.model_validate(raw)
        if verdict.polarity == "harm" and not verdict.insufficient_evidence:
            severities[verdict.rubric_id] = {
                s.dimension: s.severity for s in verdict.dimension_scores
            }
    return GoldenCase(
        subject=Subject.model_validate(run["subject"]),
        status=status,
        dossiers=[Dossier.model_validate(d) for d in run["dossiers"]],
        expected=Expected(tier=run["tier"], final_score=run["final_score"], severities=severities),
    )


def load_cases(directory: Path = GOLDEN_DIR) -> list[GoldenCase]:
    return [
        GoldenCase.model_validate(json.loads(path.read_text()))
        for path in sorted(directory.glob("*.json"))
    ]
