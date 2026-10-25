"""Stable identifiers for people, derived from their canonical name."""

import re
import unicodedata

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def slugify(name: str) -> str:
    """`"Álvaro Uribe"` -> `"alvaro-uribe"`. Pure, so the same name always gives the same id."""
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    slug = _NON_ALNUM.sub("-", ascii_name.lower()).strip("-")
    if not slug:
        raise ValueError(f"cannot make a slug from {name!r}")
    return slug
