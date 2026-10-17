"""Run the real scoring pipeline on names and print a calibration table.

    uv run python scripts/calibrate.py "Peter Singer:Australian moral philosopher" "Elon Musk"
    uv run python scripts/calibrate.py --save "Elon Musk"      # also store replay fixtures

Each argument is `name` or `name:descriptor`. Uses real APIs (costs credits).
`--save` writes dossiers, verdicts and the breakdown to tests/fixtures/runs/ so scoring
and judge changes can be re-checked offline (see tests/test_golden_runs.py).
"""

import argparse
import asyncio
import json
import re
from pathlib import Path

from dont_be_a_dick import dependencies as deps
from dont_be_a_dick.domain.rubrics import RUBRICS
from dont_be_a_dick.domain.schemas import NeedsDisambiguation, Refused, Scored
from dont_be_a_dick.workflows.scoring import PipelineState

FIXTURES = Path(__file__).parent.parent / "tests" / "fixtures" / "runs"


async def run_one(pipeline, name: str, descriptor: str | None, save: bool) -> list[str]:
    captured: dict[str, PipelineState] = {}
    original = pipeline.score

    def capture(state: PipelineState) -> None:
        captured["state"] = state
        original(state)

    pipeline.score = capture  # observe the intermediate state without changing the pipeline
    try:
        outcome = await pipeline.run(name, descriptor)
    finally:
        pipeline.score = original

    label = f"{name} ({descriptor})" if descriptor else name
    match outcome:
        case NeedsDisambiguation(candidates=candidates):
            return [
                label,
                "AMBIGUOUS",
                "-",
                "-",
                ", ".join(c.descriptor or "?" for c in candidates),
            ]
        case Refused(reason=reason):
            return [label, "REFUSED", "-", "-", reason]
        case Scored(report=report):
            b = report.breakdown
            sev = " ".join(f"{s.rubric_id}={s.severity}" for s in b.rubric_scores)
            if save and "state" in captured:
                save_run(report.subject.name, captured["state"], report)
            final = "-" if b.final_score is None else f"{b.final_score:.2f}"
            return [
                label,
                report.tier,
                final,
                f"{b.confidence:.2f}",
                f"{sev} | {'; '.join(b.notes)}",
            ]
    raise AssertionError("unreachable")


def save_run(name: str, state: PipelineState, report) -> None:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    payload = {
        "subject": report.subject.model_dump(),
        "dossiers": [d.model_dump(mode="json") for d in state.dossiers.values()],
        "verdicts": [v.model_dump(mode="json") for v in state.verdicts.values()],
        "tier": report.tier,
        "final_score": report.breakdown.final_score,
    }
    (FIXTURES / f"{slug}.json").write_text(json.dumps(payload, indent=2))


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("people", nargs="+", help="'name' or 'name:descriptor'")
    parser.add_argument("--save", action="store_true", help="store replay fixtures")
    args = parser.parse_args()

    pipeline = deps.build_scoring_pipeline()
    parsed = [
        (p.partition(":")[0].strip(), p.partition(":")[2].strip() or None) for p in args.people
    ]
    rows = await asyncio.gather(*(run_one(pipeline, n, d, args.save) for n, d in parsed))

    print(f"\nrubrics: {[r.id for r in RUBRICS]}")
    print(f"{'subject':40} {'tier':12} {'score':6} {'conf':5} details")
    for subject, tier, final, conf, details in rows:
        print(f"{subject:40} {tier:12} {final:6} {conf:5} {details}")


if __name__ == "__main__":
    asyncio.run(main())
