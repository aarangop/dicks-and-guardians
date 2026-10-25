"""LangChain adapter for the `Summarizer` port."""

import json
from collections.abc import Sequence

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from dont_be_a_dick.domain.schemas import EvidenceItem, ScoreBreakdown, Subject
from dont_be_a_dick.prompts import shared_prompt
from dont_be_a_dick.tracing import callbacks


class LangChainSummarizer:
    """Writes the plain-text summary from the breakdown and evidence. No tools."""

    def __init__(self, model: BaseChatModel, *, prompt: str | None = None) -> None:
        self._model = model
        self._prompt = prompt if prompt is not None else shared_prompt("summarizer")

    async def summarize(
        self, subject: Subject, breakdown: ScoreBreakdown, evidence: Sequence[EvidenceItem]
    ) -> str:
        payload = {
            "subject": subject.model_dump(),
            "result": breakdown.model_dump(),
            "evidence": [
                {
                    "id": e.id,
                    "claim": e.claim,
                    "dimension": e.dimension,
                    "source_url": e.source_url,
                    "source_tier": e.source_tier,
                    "event_date": e.event_date.isoformat() if e.event_date else None,
                }
                for e in evidence
            ],
        }
        response = await self._model.ainvoke(
            [SystemMessage(self._prompt), HumanMessage(json.dumps(payload, indent=2))],
            config={
                "callbacks": callbacks(),
                "run_name": "summarize",
                "tags": ["summarize"],
                "metadata": {"subject": subject.name},
            },
        )
        return str(response.text).strip()
