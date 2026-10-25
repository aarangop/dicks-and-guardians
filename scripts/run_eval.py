"""Run a judge-level experiment on the golden dataset and print a result table.

    uv run python scripts/run_eval.py --run-name baseline
    uv run python scripts/run_eval.py --run-name glm --judge-model z-ai/glm-5.3-flash
    uv run python scripts/run_eval.py --run-name v2 --prompt-root prompts_variants/v2

Needs the Langfuse stack up (docker/langfuse) and the dataset synced (scripts/sync_golden.py).
Calls the judge model through OpenRouter, so it costs credits. Compare runs in the Langfuse UI
under Datasets > golden-judge.
"""

import argparse
from pathlib import Path

from langfuse import get_client

from dont_be_a_dick.config import Settings  # importing config exports LANGFUSE_* from .env
from dont_be_a_dick.domain.schemas import Dossier
from dont_be_a_dick.evals.experiment import EVALUATORS, ExperimentConfig, build_judge, judge_case

DATASET = "golden-judge"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--run-name", required=True)
    parser.add_argument("--judge-model")
    parser.add_argument("--prompt-root", type=Path)
    args = parser.parse_args()

    settings = Settings()
    config = ExperimentConfig(
        judge_model=args.judge_model, prompt_root=args.prompt_root, label=args.run_name
    )
    judge = build_judge(config, settings)

    async def task(*, item, **_) -> dict:
        data = item["input"] if isinstance(item, dict) else item.input
        dossiers = [Dossier.model_validate(d) for d in data["dossiers"]]
        return await judge_case(judge, dossiers)

    langfuse = get_client()
    try:
        result = langfuse.get_dataset(DATASET).run_experiment(
            name="judge",
            run_name=args.run_name,
            description=f"judge={config.metadata(settings)['judge_model']}",
            task=task,
            evaluators=EVALUATORS,
            metadata=config.metadata(settings),
        )
        print(result.format())
    finally:
        langfuse.flush()


if __name__ == "__main__":
    main()
