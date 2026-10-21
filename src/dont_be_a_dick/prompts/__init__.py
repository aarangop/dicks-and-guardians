"""Prompt files, organized by rubric, loaded into agent system prompts.

Markdown files may contain `<!-- authoring notes -->`; those are stripped before
the prompt is sent to a model. The template placeholders are
`{dimension_list}` and `{dimension_tags}`, filled from the rubric so prompt text
and schema cannot drift apart, and `{max_searches}` and `{max_fetches}`, filled from
the research budget.
"""

import re
from importlib.resources import files
from typing import Literal

from dont_be_a_dick.domain.rubrics import Rubric

_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)

RubricRole = Literal["researcher", "judge"]


def _read(*parts: str) -> str:
    resource = files(__name__)
    for part in parts:
        resource = resource / part
    text = resource.read_text(encoding="utf-8")
    return _COMMENT.sub("", text).strip()


def rubric_prompt(
    rubric: Rubric, role: RubricRole, *, max_searches: int = 10, max_fetches: int = 5
) -> str:
    """Prompt for a rubric's researcher or judge, with the rubric's dimensions filled in.

    The budget numbers fill the researcher's `Budget` section, so the prompt always states the
    limit the agent is actually held to.
    """
    text = _read(rubric.prompt_dir, f"{role}.md")
    return (
        text.replace("{dimension_list}", rubric.dimension_list())
        .replace("{dimension_tags}", ", ".join(f"`{tag}`" for tag in rubric.tags))
        .replace("{max_searches}", str(max_searches))
        .replace("{max_fetches}", str(max_fetches))
    )


def shared_prompt(name: Literal["summarizer", "subject_resolution"]) -> str:
    return _read(f"{name}.md")
