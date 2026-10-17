"""Research agent.

Built with LangChain's functional `create_agent`. Everything the agent needs
(model, tools, prompt) is passed in, so tests can supply a fake model and fake
tools, and the real wiring lives in one place (`dont_be_a_dick.dependencies`).
"""

from collections.abc import Sequence

from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from pydantic import BaseModel

SYSTEM_PROMPT = """You are a research agent that gathers information about people.

Search for the person, then summarize their background, and work.

Using the web_search tool, research information about the person's
affiliations to, cooperation, or involvement with AGI labs, fossil fuel
compannies, arms manufacturers or the military industrial complex, and
associated organizations, like think tanks, or lobbying groups.

Be objective, stick to verifiable information and cite your sources (URLs)."""


def build_research_agent(
    model: BaseChatModel | str,
    tools: Sequence[BaseTool],
    system_prompt: str = SYSTEM_PROMPT,
    response_format: type[BaseModel] | None = None,
):
    """Create the research agent from injected dependencies.

    Returns a compiled LangGraph graph. Invoke it with
    `{"messages": [{"role": "user", "content": "..."}]}`. With `response_format`, the
    validated schema instance is returned under `result["structured_response"]`.
    """
    return create_agent(
        model=model,
        tools=list(tools),
        system_prompt=system_prompt,
        response_format=response_format,
    )
