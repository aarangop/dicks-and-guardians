import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI, HTTPException, Response
from pydantic import BaseModel, Field, field_validator

from dont_be_a_dick.config import settings
from dont_be_a_dick.dependencies import (
    ResearchAgentDep,
    ResearchServiceDep,
    ResultStoreDep,
    get_result_store,
    get_settings,
)
from dont_be_a_dick.domain.schemas import NeedsDisambiguation, Refused, ResearchRecord, RunStatus
from dont_be_a_dick.workflows.research_runs import Accepted

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Runs left `running` by a crash can never finish, so mark them failed on startup."""
    provide_store = app.dependency_overrides.get(get_result_store)
    store = provide_store() if provide_store else get_result_store(get_settings())
    swept = await store.fail_unfinished("interrupted by restart")
    if swept:
        logger.warning("Marked %d interrupted scoring run(s) as failed", swept)
    yield


app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)


class ResearchRequest(BaseModel):
    name: str = Field(min_length=1, description="Name of the person to research")


class ResearchResponse(BaseModel):
    name: str
    summary: str = Field(description="The research agent's final answer, as plain text")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/research")
def research(request: ResearchRequest, research_agent: ResearchAgentDep) -> ResearchResponse:
    name = request.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="name cannot be blank")

    try:
        result = research_agent.invoke(
            {"messages": [{"role": "user", "content": f"Research this person: {name}"}]}
        )
    except Exception as e:
        logger.exception("Research agent failed for %r", name)
        raise HTTPException(status_code=502, detail="Research agent failed") from e

    return ResearchResponse(name=name, summary=str(result["messages"][-1].text))


class ScoreRequest(BaseModel):
    name: str = Field(min_length=1, description="Name of the public figure to score")
    descriptor: str | None = Field(
        default=None, description="Disambiguator, e.g. 'Australian moral philosopher'"
    )

    @field_validator("descriptor")
    @classmethod
    def blank_descriptor_means_none(cls, value: str | None) -> str | None:
        return (value or "").strip() or None


class SubmissionResponse(BaseModel):
    id: str = Field(description="Slug of the subject's canonical name; poll GET /score/{id}")
    status: RunStatus


@app.post(
    "/score",
    status_code=202,
    responses={
        409: {"description": "The name matches several public figures; resubmit with a descriptor"},
        422: {"description": "Invalid request, or not a notable public figure"},
        502: {"description": "An upstream model or search call failed while resolving the name"},
    },
)
async def score(
    request: ScoreRequest,
    response: Response,
    background_tasks: BackgroundTasks,
    service: ResearchServiceDep,
    refresh: bool = False,
) -> SubmissionResponse:
    """Resolve the name, then research in the background; poll the returned id for the result.

    A subject that is already `running` or `done` is returned as it is. Pass `refresh=true` to
    rerun a finished one.
    """
    name = request.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="name cannot be blank")

    try:
        outcome = await service.submit(name, request.descriptor, refresh=refresh)
    except Exception as e:
        logger.exception("Resolving %r failed", name)
        raise HTTPException(status_code=502, detail="Scoring pipeline failed") from e

    match outcome:
        case Accepted(record=record, claimed=claimed):
            if claimed:
                background_tasks.add_task(service.execute, record)
            response.headers["Location"] = f"/score/{record.id}"
            return SubmissionResponse(id=record.id, status=record.status)
        case NeedsDisambiguation(candidates=candidates):
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "Several public figures match; resubmit with a descriptor",
                    "candidates": [c.model_dump() for c in candidates],
                },
            )
        case Refused(reason=reason):
            raise HTTPException(status_code=422, detail=reason)


@app.get("/score/{id}", responses={404: {"description": "No run is stored under this id"}})
async def get_score(id: str, store: ResultStoreDep) -> ResearchRecord:
    record = await store.get(id)
    if record is None:
        raise HTTPException(status_code=404, detail="unknown id")
    return record
