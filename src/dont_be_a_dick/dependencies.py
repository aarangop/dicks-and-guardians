"""FastAPI dependency providers, layered settings -> clients -> agents.

Each provider asks for the layer below it with `Depends`, so tests can swap any
layer through `app.dependency_overrides`. Endpoints import the `Annotated`
aliases at the bottom.

Settings and clients are process-wide singletons (`lru_cache`; `Settings` is
frozen, so it is hashable and can be the cache key). Agents are cheap to build
(~1 ms) and take unhashable arguments, so they are built per request.
"""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langgraph.graph.state import CompiledStateGraph
from pydantic import SecretStr
from tavily import TavilyClient

from dont_be_a_dick.agents import build_research_agent
from dont_be_a_dick.agents.judge import LangChainJudge
from dont_be_a_dick.agents.researcher import LangChainResearcher
from dont_be_a_dick.agents.resolver import LangChainSubjectResolver
from dont_be_a_dick.agents.summarizer import LangChainSummarizer
from dont_be_a_dick.config import Settings
from dont_be_a_dick.domain.rubrics import RUBRICS
from dont_be_a_dick.tools.web_fetch import make_web_fetch_tool
from dont_be_a_dick.tools.web_search import make_web_search_tool
from dont_be_a_dick.workflows.scoring import ScoringPipeline

DEFAULT_MODEL = "claude-sonnet-5-5"


def _require(secret: SecretStr, env_var: str) -> SecretStr:
    if not secret.get_secret_value():
        raise HTTPException(status_code=503, detail=f"{env_var} is not configured")
    return secret


# --- settings ---------------------------------------------------------------


@lru_cache
def get_settings() -> Settings:
    return Settings()


SettingsDep = Annotated[Settings, Depends(get_settings)]


# --- clients ----------------------------------------------------------------


@lru_cache
def get_tavily_client(settings: SettingsDep) -> TavilyClient:
    api_key = _require(settings.tavily_api_key, "DBAD_TAVILY_API_KEY")
    return TavilyClient(api_key=api_key.get_secret_value())


TavilyClientDep = Annotated[TavilyClient, Depends(get_tavily_client)]


@lru_cache
def get_chat_model(settings: SettingsDep) -> BaseChatModel:
    return ChatAnthropic(
        model_name=DEFAULT_MODEL,
        timeout=60.0,
        stop=None,
        api_key=_require(settings.anthropic_api_key, "DBAD_ANTHROPIC_API_KEY"),
    )


ChatModelDep = Annotated[BaseChatModel, Depends(get_chat_model)]


@lru_cache
def _anthropic_model(settings: Settings, model_name: str) -> BaseChatModel:
    # No temperature: newer Claude models reject non-default values.
    return ChatAnthropic(
        model_name=model_name,
        timeout=120.0,
        stop=None,
        api_key=_require(settings.anthropic_api_key, "DBAD_ANTHROPIC_API_KEY"),
    )


def get_researcher_model(settings: SettingsDep) -> BaseChatModel:
    return _anthropic_model(settings, settings.researcher_model)


def get_judge_model(settings: SettingsDep) -> BaseChatModel:
    return _anthropic_model(settings, settings.judge_model)


def get_resolver_model(settings: SettingsDep) -> BaseChatModel:
    return _anthropic_model(settings, settings.resolver_model)


def get_summarizer_model(settings: SettingsDep) -> BaseChatModel:
    return _anthropic_model(settings, settings.summarizer_model)


# --- tools ------------------------------------------------------------------


def get_web_search_tool(client: TavilyClientDep) -> BaseTool:
    return make_web_search_tool(client)


WebSearchToolDep = Annotated[BaseTool, Depends(get_web_search_tool)]


def get_web_fetch_tool(client: TavilyClientDep) -> BaseTool:
    return make_web_fetch_tool(client)


WebFetchToolDep = Annotated[BaseTool, Depends(get_web_fetch_tool)]


# --- agents -----------------------------------------------------------------


def get_research_agent(model: ChatModelDep, web_search: WebSearchToolDep) -> CompiledStateGraph:
    return build_research_agent(model=model, tools=[web_search])


ResearchAgentDep = Annotated[CompiledStateGraph, Depends(get_research_agent)]


# --- scoring pipeline -------------------------------------------------------


def get_subject_resolver(
    model: Annotated[BaseChatModel, Depends(get_resolver_model)], web_search: WebSearchToolDep
) -> LangChainSubjectResolver:
    return LangChainSubjectResolver(model, [web_search])


def get_researcher(
    model: Annotated[BaseChatModel, Depends(get_researcher_model)],
    web_search: WebSearchToolDep,
    web_fetch: WebFetchToolDep,
) -> LangChainResearcher:
    return LangChainResearcher(model, [web_search, web_fetch])


def get_judge(model: Annotated[BaseChatModel, Depends(get_judge_model)]) -> LangChainJudge:
    # Native JSON-schema output: forced tool calling is unsupported on newer Claude models.
    return LangChainJudge(model, structured_output_kwargs={"method": "json_schema"})


def get_summarizer(
    model: Annotated[BaseChatModel, Depends(get_summarizer_model)],
) -> LangChainSummarizer:
    return LangChainSummarizer(model)


def get_scoring_pipeline(
    resolver: Annotated[LangChainSubjectResolver, Depends(get_subject_resolver)],
    researcher: Annotated[LangChainResearcher, Depends(get_researcher)],
    judge: Annotated[LangChainJudge, Depends(get_judge)],
    summarizer: Annotated[LangChainSummarizer, Depends(get_summarizer)],
) -> ScoringPipeline:
    return ScoringPipeline(
        resolver=resolver,
        researcher=researcher,
        judge=judge,
        summarizer=summarizer,
        rubrics=RUBRICS,
    )


ScoringPipelineDep = Annotated[ScoringPipeline, Depends(get_scoring_pipeline)]


def build_scoring_pipeline(settings: Settings | None = None) -> ScoringPipeline:
    """Wire the whole pipeline outside FastAPI (scripts, integration tests).

    Mirrors the `Depends` graph above; keep the two in step.
    """
    settings = settings or get_settings()
    client = get_tavily_client(settings)
    web_search, web_fetch = get_web_search_tool(client), get_web_fetch_tool(client)
    return get_scoring_pipeline(
        get_subject_resolver(get_resolver_model(settings), web_search),
        get_researcher(get_researcher_model(settings), web_search, web_fetch),
        get_judge(get_judge_model(settings)),
        get_summarizer(get_summarizer_model(settings)),
    )
