"""Re-apply the scoring to the stored results without calling any agent.

    uv run python scripts/rescore_stored.py            # dry run: print before and after
    uv run python scripts/rescore_stored.py --write    # update data/results.json in place

The stored reports keep each rubric's top severity and the evidence, but not the extracted
facts, so reach and authority come from the table below. They are hand entered, not sourced
by a researcher: review them, and drop an entry once a fresh research run reports its own.
Agency, harm severities and evidence are read from the stored record, and the real
`compute_score` does the arithmetic, so a config change is picked up by running this again.
"""

import argparse
import json
from pathlib import Path
from typing import Any

from dont_be_a_dick.domain.rubrics import RUBRICS
from dont_be_a_dick.domain.schemas import (
    DimensionScore,
    Dossier,
    EvidenceItem,
    JudgeVerdict,
    PersonFacts,
    Role,
    Subject,
)
from dont_be_a_dick.domain.scoring import compute_score

DEFAULT_DB = Path(__file__).resolve().parent.parent / "data" / "results.json"
TABLE = "research"
NOTE = "power backfilled from hand-entered reach and authority, not from a research run"

# name -> (reach, authority)
FACTS: dict[str, tuple[str, str]] = {
    "Donald Trump": ("global", "unilateral"),
    "Mohammed bin Salman": ("national", "unilateral"),
    "Benjamin Netanyahu": ("national", "unilateral"),
    "Javier Milei": ("national", "unilateral"),
    "Luiz Inácio Lula da Silva": ("national", "unilateral"),
    "Bernie Sanders": ("national", "shared"),
    "Flávio Bolsonaro": ("national", "shared"),
    "Alice Weidel": ("national", "shared"),
    "Álvaro Uribe": ("national", "none"),
    "Sam Altman": ("global", "none"),
    "Dario Amodei": ("global", "none"),
    "Elon Musk": ("global", "none"),
    "Jeff Bezos": ("global", "none"),
    "Mark Zuckerberg": ("global", "none"),
    "Bill Gates": ("global", "none"),
    "Sam Bankman-Fried": ("industry", "none"),
    "Joe Rogan": ("national", "none"),
    "Tucker Carlson": ("national", "none"),
    "Jon Stewart": ("national", "none"),
    "MrBeast": ("national", "none"),
    "Andrew Tate": ("industry", "none"),
    "Rutger Bregman": ("organization", "none"),
    "Daniel Kokotajlo": ("organization", "none"),
}

SENIORITY_BY_AGENCY = {
    0.25: "rank_and_file",
    0.5: "manager",
    0.85: "executive",
    1.0: "founder_or_head_of_state",
}


def _verdict(rubric_id: str, polarity: str, score: dict[str, Any]) -> JudgeVerdict:
    if score["severity"] is None:
        return JudgeVerdict(
            rubric_id=rubric_id,
            polarity=polarity,
            insufficient_evidence=True,
            rationale="stored",
        )
    return JudgeVerdict(
        rubric_id=rubric_id,
        polarity=polarity,
        insufficient_evidence=False,
        dimension_scores=[
            DimensionScore(
                dimension=score["top_dimension"],
                severity=score["severity"],
                evidence_ids=score["evidence_ids"],
                rationale="stored",
            )
        ],
        rationale="stored",
    )


def rescore(record: dict[str, Any]) -> dict[str, Any] | None:
    """The updated breakdown, or None when the record cannot or need not be rescored."""
    report = record.get("report")
    if report is None:
        return None
    breakdown = report["breakdown"]
    name = report["subject"]["name"]
    if name not in FACTS or breakdown["harm_score"] is None:
        return None
    reach, authority = FACTS[name]
    seniority = SENIORITY_BY_AGENCY[breakdown["agency"]]
    facts = PersonFacts(
        roles=[Role(title="stored", organization="stored", seniority=seniority)],
        reach=reach,
        authority=authority,
    )
    subject = Subject(name=name)
    items = [EvidenceItem.model_validate(e) for e in report["evidence"]]
    dossiers = [
        Dossier(
            rubric_id=r.id,
            subject=subject,
            items=[i for i in items if i.id.startswith(f"{r.id}-")],
            facts=facts,
        )
        for r in RUBRICS
    ]
    verdicts = [_verdict(s["rubric_id"], "harm", s) for s in breakdown["rubric_scores"]]
    verdicts += [_verdict(s["rubric_id"], "benefit", s) for s in breakdown["benefit_scores"]]

    fresh = compute_score(verdicts, dossiers, RUBRICS)
    assert fresh.harm_score is not None
    assert abs(fresh.harm_score - breakdown["harm_score"]) < 1e-9, f"{name}: harm drifted"
    assert fresh.agency == breakdown["agency"], f"{name}: agency drifted"

    notes = [n for n in breakdown["notes"] if n != NOTE] + [NOTE]
    return {
        **breakdown,
        "power": fresh.power,
        "influence": fresh.influence,
        "final_score": fresh.final_score,
        "tier": fresh.tier,
        "benefit_score": fresh.benefit_score,
        "benefit_tier": fresh.benefit_tier,
        "notes": notes,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--write", action="store_true", help="update the file in place")
    args = parser.parse_args()

    data = json.loads(args.db.read_text())
    print(f"{'name':28} {'power':>11} {'final':>11} {'tier':>24} {'benefit':>11}")
    for record in data[TABLE].values():
        updated = rescore(record)
        name = (record.get("report") or record)["subject"]["name"]
        if updated is None:
            print(f"{name:28} skipped")
            continue
        old = record["report"]["breakdown"]
        print(
            f"{name:28} {old['power']:.2f}>{updated['power']:.2f} "
            f"{old['final_score']:.2f}>{updated['final_score']:.2f} "
            f"{old['tier']:>11}>{updated['tier']:<11} "
            f"{old['benefit_score']:.2f}>{updated['benefit_score']:.2f}"
        )
        record["report"]["breakdown"] = updated
        record["report"]["tier"] = updated["tier"]
        record["report"]["benefit_tier"] = updated["benefit_tier"]

    if args.write:
        args.db.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        print(f"wrote {args.db}")
    else:
        print("dry run: pass --write to update the file")


if __name__ == "__main__":
    main()
