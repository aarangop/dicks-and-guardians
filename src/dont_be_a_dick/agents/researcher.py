"""LangChain adapter for the `Researcher` port."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from langchain.agents.middleware import AgentMiddleware, ToolCallLimitMiddleware
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool

from dont_be_a_dick.agents.research_agent import build_research_agent
from dont_be_a_dick.domain.evidence import build_dossier
from dont_be_a_dick.domain.rubrics import Rubric
from dont_be_a_dick.domain.schemas import Dossier, ResearchFindings, Subject
from dont_be_a_dick.prompts import rubric_prompt

SEARCH_TOOL = "web_search"
FETCH_TOOL = "web_fetch"

_STEPS_PER_ROUND = 4
"""Graph steps in one tool round: the model, one per limit middleware (two), and the tools."""

_EXTRA_ROUNDS = 5
"""Rounds beyond the budget: refused calls still cost a round, and the final answer needs one."""


@dataclass(frozen=True)
class ResearchBudget:
    """How much tool use one researcher may spend on one rubric.

    The limits are enforced by middleware and stated in the prompt, so the agent knows them.
    """

    searches: int = 10
    fetches: int = 5

    @property
    def recursion_limit(self) -> int:
        """LangGraph steps per run. A safety net: the tool limits are what bound the cost."""
        return _STEPS_PER_ROUND * (self.searches + self.fetches + _EXTRA_ROUNDS)


class ResearchError(Exception):
    pass


def _limit_middleware(budget: ResearchBudget) -> list[AgentMiddleware]:
    # "continue" refuses the excess call with an error message instead of raising, so the agent
    # can still stop searching and return the findings it has.
    return [
        ToolCallLimitMiddleware(tool_name=SEARCH_TOOL, run_limit=budget.searches),
        ToolCallLimitMiddleware(tool_name=FETCH_TOOL, run_limit=budget.fetches),
    ]


class LangChainResearcher:
    """One `create_agent` per rubric, differing only by system prompt."""

    def __init__(
        self,
        model: BaseChatModel,
        tools: Sequence[BaseTool],
        *,
        budget: ResearchBudget | None = None,
        prompt_for: Callable[[Rubric], str] | None = None,
        recursion_limit: int | None = None,
    ) -> None:
        self._model = model
        self._tools = list(tools)
        self._budget = budget = budget or ResearchBudget()
        self._prompt_for = prompt_for or self._budgeted_prompt
        self._recursion_limit = recursion_limit or budget.recursion_limit
        self._agents: dict[str, object] = {}

    def _budgeted_prompt(self, rubric: Rubric) -> str:
        return rubric_prompt(
            rubric,
            "researcher",
            max_searches=self._budget.searches,
            max_fetches=self._budget.fetches,
        )

    def _agent_for(self, rubric: Rubric):
        if rubric.id not in self._agents:
            self._agents[rubric.id] = build_research_agent(
                model=self._model,
                tools=self._tools,
                system_prompt=self._prompt_for(rubric),
                response_format=ResearchFindings,
                middleware=_limit_middleware(self._budget),
            )
        return self._agents[rubric.id]

    async def research(self, subject: Subject, rubric: Rubric) -> Dossier:
        agent = self._agent_for(rubric)
        result = await agent.ainvoke(  # type: ignore[attr-defined]
            {"messages": [{"role": "user", "content": _request(subject, rubric)}]},
            config={
                "recursion_limit": self._recursion_limit,
                "run_name": f"research:{rubric.id}",
                "tags": ["research", rubric.id],
                "metadata": {"rubric": rubric.id, "subject": subject.name},
            },
        )
        findings = result.get("structured_response")
        if not isinstance(findings, ResearchFindings):
            raise ResearchError(f"researcher for {rubric.id} returned no structured findings")
        return build_dossier(subject, rubric, findings)


def _request(subject: Subject, rubric: Rubric) -> str:
    who = subject.name if not subject.descriptor else f"{subject.name} ({subject.descriptor})"
    return f"Collect evidence for rubric {rubric.id} ({rubric.name}) about: {who}"
