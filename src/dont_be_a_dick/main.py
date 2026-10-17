import logging

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from dont_be_a_dick.config import settings
from dont_be_a_dick.dependencies import ResearchAgentDep, ScoringPipelineDep
from dont_be_a_dick.domain.schemas import DickScoreReport, NeedsDisambiguation, Refused, Scored

logger = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name, debug=settings.debug)


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


@app.post(
    "/score",
    responses={
        409: {"description": "The name matches several public figures; resubmit with a descriptor"},
        422: {"description": "Invalid request, or not a notable public figure"},
        502: {"description": "An upstream model or search call failed"},
    },
)
async def score(request: ScoreRequest, pipeline: ScoringPipelineDep) -> DickScoreReport:
    name = request.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="name cannot be blank")

    try:
        outcome = await pipeline.run(name, request.descriptor)
    except Exception as e:
        logger.exception("Scoring pipeline failed for %r", name)
        raise HTTPException(status_code=502, detail="Scoring pipeline failed") from e

    match outcome:
        case Scored(report=report):
            return report
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
