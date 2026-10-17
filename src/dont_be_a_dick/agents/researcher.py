"""LangChain adapter for the `Researcher` port."""

from collections.abc import Callable, Sequence

from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool

from dont_be_a_dick.agents.research_agent import build_research_agent
from dont_be_a_dick.domain.evidence import build_dossier
from dont_be_a_dick.domain.rubrics import Rubric
from dont_be_a_dick.domain.schemas import Dossier, ResearchFindings, Subject
from dont_be_a_dick.prompts import rubric_prompt

DEFAULT_RECURSION_LIMIT = 30
"""LangGraph steps per run (roughly two per tool round). Bounds cost if an agent loops."""


class ResearchError(Exception):
    pass


def _default_prompt(rubric: Rubric) -> str:
    return rubric_prompt(rubric, "researcher")


class LangChainResearcher:
    """One `create_agent` per rubric, differing only by system prompt."""

    def __init__(
        self,
        model: BaseChatModel,
        tools: Sequence[BaseTool],
        *,
        prompt_for: Callable[[Rubric], str] = _default_prompt,
        recursion_limit: int = DEFAULT_RECURSION_LIMIT,
    ) -> None:
        self._model = model
        self._tools = list(tools)
        self._prompt_for = prompt_for
        self._recursion_limit = recursion_limit
        self._agents: dict[str, object] = {}

    def _agent_for(self, rubric: Rubric):
        if rubric.id not in self._agents:
            self._agents[rubric.id] = build_research_agent(
                model=self._model,
                tools=self._tools,
                system_prompt=self._prompt_for(rubric),
                response_format=ResearchFindings,
            )
        return self._agents[rubric.id]

    async def research(self, subject: Subject, rubric: Rubric) -> Dossier:
        agent = self._agent_for(rubric)
        result = await agent.ainvoke(  # type: ignore[attr-defined]
            {"messages": [{"role": "user", "content": _request(subject, rubric)}]},
            config={"recursion_limit": self._recursion_limit},
        )
        findings = result.get("structured_response")
        if not isinstance(findings, ResearchFindings):
            raise ResearchError(f"researcher for {rubric.id} returned no structured findings")
        return build_dossier(subject, rubric, findings)


def _request(subject: Subject, rubric: Rubric) -> str:
    who = subject.name if not subject.descriptor else f"{subject.name} ({subject.descriptor})"
    return f"Collect evidence for rubric {rubric.id} ({rubric.name}) about: {who}"
