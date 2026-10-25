"""Mirror the golden cases in evals/golden/ into a Langfuse dataset (idempotent upsert).

    uv run python scripts/sync_golden.py                    # sync evals/golden/*.json
    uv run python scripts/sync_golden.py --import-fixtures  # turn tests/fixtures/runs/*.json
                                                            # into baseline golden files

The JSON files are the source of truth; the dataset can be rebuilt from them at any time.
`--import-fixtures` copies a run's own verdicts as expectations, marked `baseline`: review them
and set `"status": "calibrated"` before trusting a result against them.
"""

import argparse
import json
from pathlib import Path

from langfuse import get_client

from dont_be_a_dick import config  # noqa: F401  (exports LANGFUSE_* from .env)
from dont_be_a_dick.evals.golden import GOLDEN_DIR, from_run, load_cases

DATASET = "golden-judge"
FIXTURES = Path(__file__).parent.parent / "tests" / "fixtures" / "runs"


def import_fixtures() -> None:
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    for path in sorted(FIXTURES.glob("*.json")):
        target = GOLDEN_DIR / path.name
        if target.exists():
            print(f"skip {target.name}: already exists")
            continue
        case = from_run(json.loads(path.read_text()))
        target.write_text(case.model_dump_json(indent=2, exclude_none=True))
        print(f"wrote {target.relative_to(GOLDEN_DIR.parent.parent)}")


def sync() -> None:
    cases = load_cases()
    langfuse = get_client()
    langfuse.create_dataset(
        name=DATASET, description="Frozen dossiers with calibrated expected judge outcomes"
    )
    for case in cases:
        langfuse.create_dataset_item(
            dataset_name=DATASET,
            id=f"{DATASET}:{case.id}",
            input=case.dataset_input(),
            expected_output=case.expected.model_dump(mode="json"),
            metadata=case.dataset_metadata(),
        )
    langfuse.flush()
    print(f"synced {len(cases)} cases to dataset {DATASET!r}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--import-fixtures", action="store_true")
    args = parser.parse_args()
    import_fixtures() if args.import_fixtures else sync()
