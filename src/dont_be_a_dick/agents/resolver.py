"""LangChain adapter for the `SubjectResolver` port.

The LLM fills a flat `ResolutionDecision` (friendlier to structured output than a
union); this module maps it to the domain `Resolution` types and rejects
inconsistent decisions.
"""

from collections.abc import Sequence
from typing import Literal

from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from dont_be_a_dick.agents.research_agent import build_research_agent
from dont_be_a_dick.domain.schemas import Ambiguous, Refused, Resolution, Resolved, Subject
from dont_be_a_dick.prompts import shared_prompt
from dont_be_a_dick.tracing import callbacks

DEFAULT_RECURSION_LIMIT = 12


class ResolutionError(Exception):
    pass


class ResolutionDecision(BaseModel):
    outcome: Literal["resolved", "ambiguous", "refused"]
    candidates: list[Subject] = Field(
        default_factory=list,
        description="One subject if resolved, two or more if ambiguous, none if refused",
    )
    reason: str | None = Field(default=None, description="Required when refused")


def to_resolution(decision: ResolutionDecision) -> Resolution:
    match decision.outcome:
        case "resolved":
            if len(decision.candidates) != 1:
                raise ResolutionError("a resolved decision needs exactly one candidate")
            return Resolved(subject=decision.candidates[0])
        case "ambiguous":
            if len(decision.candidates) < 2:
                raise ResolutionError("an ambiguous decision needs at least two candidates")
            return Ambiguous(candidates=decision.candidates)
        case "refused":
            if not decision.reason:
                raise ResolutionError("a refused decision needs a reason")
            return Refused(reason=decision.reason)


class LangChainSubjectResolver:
    def __init__(
        self,
        model: BaseChatModel,
        tools: Sequence[BaseTool],
        *,
        prompt: str | None = None,
        recursion_limit: int = DEFAULT_RECURSION_LIMIT,
    ) -> None:
        self._agent = build_research_agent(
            model=model,
            tools=tools,
            system_prompt=prompt if prompt is not None else shared_prompt("subject_resolution"),
            response_format=ResolutionDecision,
        )
        self._recursion_limit = recursion_limit

    async def resolve(self, name: str, descriptor: str | None = None) -> Resolution:
        request = f"Name: {name}" + (f"\nDescriptor: {descriptor}" if descriptor else "")
        result = await self._agent.ainvoke(
            {"messages": [{"role": "user", "content": request}]},
            config={
                "recursion_limit": self._recursion_limit,
                "callbacks": callbacks(),
                "run_name": "resolve_subject",
                "tags": ["resolve"],
                "metadata": {"subject": name},
            },
        )
        decision = result.get("structured_response")
        if not isinstance(decision, ResolutionDecision):
            raise ResolutionError("resolver returned no structured decision")
        return to_resolution(decision)
