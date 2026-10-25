"""Tracing seam: agents ask for callbacks and never import Langfuse directly."""

from collections.abc import Iterator
from contextlib import contextmanager

from langchain_core.callbacks import BaseCallbackHandler

from dont_be_a_dick.config import langfuse_settings


def callbacks() -> list[BaseCallbackHandler]:
    """A fresh Langfuse handler when tracing is active, otherwise nothing.

    Each handler nests under the span opened by `session`, so one run's calls share a trace.
    """
    if not langfuse_settings.active:
        return []
    from langfuse.langchain import CallbackHandler

    return [CallbackHandler()]


@contextmanager
def session(session_id: str, *, name: str = "score_subject") -> Iterator[None]:
    """Put every trace made inside the block into one Langfuse session.

    Opens a root span so the researcher, judge and summarizer calls nest under a single trace,
    and tags it with `session_id` (US-ASCII, under 200 characters). A no-op when tracing is off.
    """
    if not langfuse_settings.active:
        yield
        return
    from langfuse import get_client, propagate_attributes

    with (
        get_client().start_as_current_observation(as_type="span", name=name),
        propagate_attributes(session_id=session_id, trace_name=name),
    ):
        yield
