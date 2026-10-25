"""LangChain adapter for the `Judge` port."""

from collections.abc import Callable, Mapping
from typing import Any

from langchain_core.exceptions import OutputParserException
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from pydantic import ValidationError

from dont_be_a_dick.domain.evidence import VerdictError, check_verdict
from dont_be_a_dick.domain.rubrics import Rubric
from dont_be_a_dick.domain.schemas import Dossier, JudgeVerdict, Polarity
from dont_be_a_dick.prompts import rubric_prompt
from dont_be_a_dick.tracing import callbacks

MAX_ATTEMPTS = 2
"""One answer plus one correction round when the verdict fails validation."""


def _default_prompt(rubric: Rubric, polarity: Polarity) -> str:
    return rubric_prompt(rubric, "judge" if polarity == "harm" else "judge_benefit")


class LangChainJudge:
    """Rates a dossier with a structured-output model call (no tools, no agent loop)."""

    def __init__(
        self,
        model: BaseChatModel,
        *,
        prompt_for: Callable[[Rubric, Polarity], str] = _default_prompt,
        structured_output_kwargs: Mapping[str, Any] | None = None,
    ) -> None:
        """`structured_output_kwargs` go to `with_structured_output`, e.g. a provider's `method`."""
        self._structured = model.with_structured_output(
            JudgeVerdict, **(structured_output_kwargs or {})
        )
        self._prompt_for = prompt_for

    async def judge(
        self, dossier: Dossier, rubric: Rubric, polarity: Polarity = "harm"
    ) -> JudgeVerdict:
        if not dossier.items and not dossier.facts.roles:
            return JudgeVerdict(
                rubric_id=rubric.id,
                polarity=polarity,
                insufficient_evidence=True,
                rationale="The dossier contains no evidence and no documented roles.",
            )

        messages: list[BaseMessage] = [
            SystemMessage(self._prompt_for(rubric, polarity)),
            HumanMessage(
                f"Rubric: {rubric.id}\nSide: {polarity}\n\n"
                f"Dossier:\n{dossier.model_dump_json(indent=2)}"
            ),
        ]
        problems: list[str] = []
        for _ in range(MAX_ATTEMPTS):
            try:
                verdict = await self._structured.ainvoke(
                    messages,
                    config={
                        "callbacks": callbacks(),
                        "run_name": f"judge:{rubric.id}:{polarity}",
                        "tags": ["judge", rubric.id, polarity],
                        "metadata": {
                            "rubric": rubric.id,
                            "polarity": polarity,
                            "subject": dossier.subject.name,
                        },
                    },
                )
            except (ValidationError, OutputParserException) as e:
                problems = [f"invalid structure: {e}"]
            else:
                # The side is decided by the caller, not by the model.
                verdict = verdict.model_copy(update={"polarity": polarity})
                problems = check_verdict(verdict, dossier, rubric, polarity)
                if not problems:
                    return verdict
            messages.append(
                HumanMessage(
                    "Your verdict was rejected:\n"
                    + "\n".join(f"- {p}" for p in problems)
                    + "\nFix these problems and answer again."
                )
            )
        raise VerdictError(problems)
