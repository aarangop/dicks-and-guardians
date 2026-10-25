import pytest

from dont_be_a_dick.domain.slug import slugify


@pytest.mark.parametrize(
    ("name", "slug"),
    [
        ("Lula Da Silva", "lula-da-silva"),
        ("Álvaro Uribe", "alvaro-uribe"),
        ("Luiz Inácio Lula da Silva", "luiz-inacio-lula-da-silva"),
        ("  Elon   Musk  ", "elon-musk"),
        ("Sam Bankman-Fried", "sam-bankman-fried"),
        ("Abelardo de la Espriella.", "abelardo-de-la-espriella"),
    ],
)
def test_slugify(name: str, slug: str) -> None:
    assert slugify(name) == slug


@pytest.mark.parametrize("name", ["", "   ", "---", "漢字"])
def test_a_name_with_nothing_slugifiable_is_rejected(name: str) -> None:
    with pytest.raises(ValueError):
        slugify(name)
