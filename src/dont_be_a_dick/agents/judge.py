"""LangChain adapter for the `Judge` port."""

from collections.abc import Callable, Mapping
from typing import Any

from langchain_core.exceptions import OutputParserException
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from pydantic import ValidationError

from dont_be_a_dick.domain.evidence import VerdictError, check_verdict
from dont_be_a_dick.domain.rubrics import Rubric
from dont_be_a_dick.domain.schemas import Dossier, JudgeVerdict
from dont_be_a_dick.prompts import rubric_prompt

MAX_ATTEMPTS = 2
"""One answer plus one correction round when the verdict fails validation."""


def _default_prompt(rubric: Rubric) -> str:
    return rubric_prompt(rubric, "judge")


class LangChainJudge:
    """Rates a dossier with a structured-output model call (no tools, no agent loop)."""

    def __init__(
        self,
        model: BaseChatModel,
        *,
        prompt_for: Callable[[Rubric], str] = _default_prompt,
        structured_output_kwargs: Mapping[str, Any] | None = None,
    ) -> None:
        """`structured_output_kwargs` go to `with_structured_output`, e.g. a provider's `method`."""
        self._structured = model.with_structured_output(
            JudgeVerdict, **(structured_output_kwargs or {})
        )
        self._prompt_for = prompt_for

    async def judge(self, dossier: Dossier, rubric: Rubric) -> JudgeVerdict:
        if not dossier.items and not dossier.facts.roles:
            return JudgeVerdict(
                rubric_id=rubric.id,
                insufficient_evidence=True,
                rationale="The dossier contains no evidence and no documented roles.",
            )

        messages: list[BaseMessage] = [
            SystemMessage(self._prompt_for(rubric)),
            HumanMessage(f"Rubric: {rubric.id}\n\nDossier:\n{dossier.model_dump_json(indent=2)}"),
        ]
        problems: list[str] = []
        for _ in range(MAX_ATTEMPTS):
            try:
                verdict = await self._structured.ainvoke(
                    messages,
                    config={
                        "run_name": f"judge:{rubric.id}",
                        "tags": ["judge", rubric.id],
                        "metadata": {"rubric": rubric.id, "subject": dossier.subject.name},
                    },
                )
            except (ValidationError, OutputParserException) as e:
                problems = [f"invalid structure: {e}"]
            else:
                problems = check_verdict(verdict, dossier, rubric)
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
