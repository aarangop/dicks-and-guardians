"""FastAPI dependency providers, layered settings -> clients -> agents.

Each provider asks for the layer below it with `Depends`, so tests can swap any
layer through `app.dependency_overrides`. Endpoints import the `Annotated`
aliases at the bottom.

Settings and clients are process-wide singletons (`lru_cache`; `Settings` is
frozen, so it is hashable and can be the cache key). Agents are cheap to build
(~1 ms) and take unhashable arguments, so they are built per request.
"""

from collections.abc import Sequence
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langchain_openrouter import ChatOpenRouter
from langgraph.graph.state import CompiledStateGraph
from pydantic import SecretStr
from tavily import TavilyClient

from dont_be_a_dick import tracing
from dont_be_a_dick.agents import build_research_agent
from dont_be_a_dick.agents.judge import LangChainJudge
from dont_be_a_dick.agents.researcher import LangChainResearcher, ResearchBudget
from dont_be_a_dick.agents.resolver import LangChainSubjectResolver
from dont_be_a_dick.agents.summarizer import LangChainSummarizer
from dont_be_a_dick.config import Settings
from dont_be_a_dick.domain.ports import ResultStore
from dont_be_a_dick.domain.rubrics import RUBRICS, Rubric
from dont_be_a_dick.storage.tinydb_store import TinyDBResultStore
from dont_be_a_dick.tools.web_fetch import make_web_fetch_tool
from dont_be_a_dick.tools.web_search import make_web_search_tool
from dont_be_a_dick.workflows.research_runs import ResearchService
from dont_be_a_dick.workflows.scoring import ScoringPipeline


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
    return ChatOpenRouter(
        model=settings.model_for("chat"),
        timeout=60_000,  # milliseconds
        max_retries=settings.llm_max_retries,
        api_key=_require(settings.openrouter_api_key, "DBAD_OPENROUTER_API_KEY"),
    )


ChatModelDep = Annotated[BaseChatModel, Depends(get_chat_model)]


@lru_cache
def _openrouter_model(
    settings: Settings, model_name: str, *, cache_prompt: bool = False
) -> BaseChatModel:
    # No temperature: newer Claude models reject non-default values.
    # Top-level cache_control makes OpenRouter move a cache breakpoint to the end of the prompt on
    # every request, so each step of a tool loop reads the previous steps from cache. Single-call
    # roles leave it off: they would pay the cache-write premium and never read it back.
    return ChatOpenRouter(
        model=model_name,
        timeout=120_000,  # milliseconds
        max_retries=settings.llm_max_retries,
        api_key=_require(settings.openrouter_api_key, "DBAD_OPENROUTER_API_KEY"),
        model_kwargs={"cache_control": {"type": "ephemeral"}} if cache_prompt else {},
    )


def get_researcher_model(settings: SettingsDep) -> BaseChatModel:
    return _openrouter_model(settings, settings.model_for("researcher"), cache_prompt=True)


def get_judge_model(settings: SettingsDep) -> BaseChatModel:
    return _openrouter_model(settings, settings.model_for("judge"))


def get_resolver_model(settings: SettingsDep) -> BaseChatModel:
    return _openrouter_model(settings, settings.model_for("resolver"), cache_prompt=True)


def get_summarizer_model(settings: SettingsDep) -> BaseChatModel:
    return _openrouter_model(settings, settings.model_for("summarizer"))


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
    settings: SettingsDep,
) -> LangChainResearcher:
    budget = ResearchBudget(settings.research_max_searches, settings.research_max_fetches)
    return LangChainResearcher(model, [web_search, web_fetch], budget=budget)


JUDGE_STRUCTURED_OUTPUT = {"method": "json_schema"}
"""Native JSON-schema output: forced tool calling is unsupported on newer Claude models."""


def get_judge(model: Annotated[BaseChatModel, Depends(get_judge_model)]) -> LangChainJudge:
    return LangChainJudge(model, structured_output_kwargs=JUDGE_STRUCTURED_OUTPUT)


def get_summarizer(
    model: Annotated[BaseChatModel, Depends(get_summarizer_model)],
) -> LangChainSummarizer:
    return LangChainSummarizer(model)


def _assemble_pipeline(
    resolver: LangChainSubjectResolver,
    researcher: LangChainResearcher,
    judge: LangChainJudge,
    summarizer: LangChainSummarizer,
    settings: Settings,
    rubrics: Sequence[Rubric],
) -> ScoringPipeline:
    return ScoringPipeline(
        resolver=resolver,
        researcher=researcher,
        judge=judge,
        summarizer=summarizer,
        rubrics=rubrics,
        max_concurrent_research=settings.max_concurrent_research,
    )


def get_scoring_pipeline(
    resolver: Annotated[LangChainSubjectResolver, Depends(get_subject_resolver)],
    researcher: Annotated[LangChainResearcher, Depends(get_researcher)],
    judge: Annotated[LangChainJudge, Depends(get_judge)],
    summarizer: Annotated[LangChainSummarizer, Depends(get_summarizer)],
    settings: SettingsDep,
) -> ScoringPipeline:
    return _assemble_pipeline(resolver, researcher, judge, summarizer, settings, RUBRICS)


ScoringPipelineDep = Annotated[ScoringPipeline, Depends(get_scoring_pipeline)]


# --- stored runs ------------------------------------------------------------


@lru_cache
def get_result_store(settings: SettingsDep) -> ResultStore:
    return TinyDBResultStore(settings.db_path)


ResultStoreDep = Annotated[ResultStore, Depends(get_result_store)]


def get_research_service(pipeline: ScoringPipelineDep, store: ResultStoreDep) -> ResearchService:
    return ResearchService(pipeline, store, session_scope=tracing.session)


ResearchServiceDep = Annotated[ResearchService, Depends(get_research_service)]


def build_scoring_pipeline(
    settings: Settings | None = None, rubrics: Sequence[Rubric] = RUBRICS
) -> ScoringPipeline:
    """Wire the whole pipeline outside FastAPI (scripts, integration tests).

    Mirrors the `Depends` graph above; keep the two in step. `rubrics` lets a caller run a subset.
    """
    settings = settings or get_settings()
    client = get_tavily_client(settings)
    web_search, web_fetch = get_web_search_tool(client), get_web_fetch_tool(client)
    return _assemble_pipeline(
        get_subject_resolver(get_resolver_model(settings), web_search),
        get_researcher(get_researcher_model(settings), web_search, web_fetch, settings),
        get_judge(get_judge_model(settings)),
        get_summarizer(get_summarizer_model(settings)),
        settings,
        rubrics,
    )
