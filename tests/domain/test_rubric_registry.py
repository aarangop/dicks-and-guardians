from dont_be_a_dick.domain.rubrics import RUBRICS


def test_rubric_ids_are_unique() -> None:
    ids = [r.id for r in RUBRICS]
    assert len(ids) == len(set(ids))


def test_dimension_tags_are_unique_within_a_rubric() -> None:
    for rubric in RUBRICS:
        assert len(rubric.tags) == len(set(rubric.tags)), rubric.id


def test_only_r5_is_a_counterweight() -> None:
    assert [r.id for r in RUBRICS if r.kind == "counterweight"] == ["R5"]
