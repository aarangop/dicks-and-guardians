import pytest

from dont_be_a_dick.domain.rubrics import RUBRICS
from dont_be_a_dick.prompts import rubric_prompt, shared_prompt


@pytest.mark.parametrize("rubric", RUBRICS, ids=lambda r: r.id)
@pytest.mark.parametrize("role", ["researcher", "judge"])
def test_every_rubric_has_both_prompts(rubric, role) -> None:
    assert rubric_prompt(rubric, role).strip()


@pytest.mark.parametrize("rubric", RUBRICS, ids=lambda r: r.id)
@pytest.mark.parametrize("role", ["researcher", "judge"])
def test_prompts_mention_every_dimension_and_have_no_leftovers(rubric, role) -> None:
    text = rubric_prompt(rubric, role)

    for tag in rubric.tags:
        assert f"`{tag}`" in text
    assert "{dimension_list}" not in text
    assert "{dimension_tags}" not in text


def test_authoring_comments_are_stripped() -> None:
    from dont_be_a_dick.domain.rubrics import R1

    assert "REVIEW" not in rubric_prompt(R1, "judge")
    assert "<!--" not in rubric_prompt(R1, "judge")


@pytest.mark.parametrize("name", ["summarizer", "subject_resolution"])
def test_shared_prompts_load(name) -> None:
    assert shared_prompt(name)


@pytest.mark.parametrize("rubric", RUBRICS, ids=lambda r: r.id)
def test_researcher_prompt_states_the_budget(rubric) -> None:
    text = rubric_prompt(rubric, "researcher", max_searches=7, max_fetches=3)

    assert "7 searches and 3 fetches" in text
    assert "{max_searches}" not in text
    assert "{max_fetches}" not in text
