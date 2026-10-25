"""Export finished runs from the TinyDB file into the static site's `people.json` and `people.js`.

Run it offline whenever you want the site to change, then commit the result:

    uv run python scripts/export_web_data.py
    git add web/data web/app.js && git commit -m "Update site data"

Only runs with status "done" and a report are exported. Nothing else (errors, running
records) ever reaches the public site.
"""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = ROOT / "data" / "results.json"
DEFAULT_OUT = ROOT / "web" / "data" / "people.json"
TABLE = "research"


def to_person(record: dict[str, Any]) -> dict[str, Any]:
    """Flatten one stored record into the shape the frontend reads."""
    report = record["report"]
    b = report["breakdown"]
    return {
        "id": record["id"],
        "name": report["subject"]["name"],
        "descriptor": report["subject"].get("descriptor"),
        "requested_name": record.get("requested_name"),
        "rated_at": record["updated_at"],
        "tier": report["tier"],
        "score": b["final_score"],
        "harm": b["harm_score"],
        "power": b["power"],
        "agency": b["agency"],
        "influence": b["influence"],
        "benefit_tier": report.get("benefit_tier", "unrated"),
        "benefit": b.get("benefit_score"),
        "benefit_confidence": b.get("benefit_confidence", 0.0),
        "benefit_rubrics": [
            {
                "id": r["rubric_id"],
                "severity": r["severity"],
                "top_dimension": r["top_dimension"],
                "evidence_ids": r["evidence_ids"],
            }
            for r in b.get("benefit_scores", [])
        ],
        "confidence": b["confidence"],
        "coverage": b["coverage"],
        "notes": b["notes"],
        "rubrics": [
            {
                "id": r["rubric_id"],
                "severity": r["severity"],
                "top_dimension": r["top_dimension"],
                "evidence_ids": r["evidence_ids"],
            }
            for r in b["rubric_scores"]
        ],
        "summary": report["summary"],
        "evidence": report["evidence"],
    }


def export(db_path: Path, out_path: Path) -> int:
    raw = json.loads(db_path.read_text(encoding="utf-8"))
    records = raw.get(TABLE, {}).values()
    people = [
        to_person(r) for r in records if r.get("status") == "done" and r.get("report") is not None
    ]
    people.sort(key=lambda p: p["id"])  # stable output keeps git diffs small
    payload = {"generated_at": datetime.now(UTC).isoformat(timespec="seconds"), "people": people}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    out_path.write_text(text, encoding="utf-8")
    # Same data as a classic script, so the site also works when opened from disk (file://).
    # "</" is escaped so scraped text can never close a script tag.
    safe = text.replace("</", "<\\/").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    out_path.with_suffix(".js").write_text(f"window.PEOPLE_DATA={safe};\n", encoding="utf-8")
    return len(people)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="TinyDB results file")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="people.json to write")
    args = parser.parse_args()
    count = export(args.db, args.out)
    print(f"Exported {count} people to {args.out}")


if __name__ == "__main__":
    main()
