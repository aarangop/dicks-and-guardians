"""Rubrics as data. Adding a rubric means adding a record here and a prompts/ directory."""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Dimension:
    tag: str
    name: str
    description: str


@dataclass(frozen=True)
class Rubric:
    id: str
    name: str
    kind: Literal["harm", "counterweight"]
    dimensions: tuple[Dimension, ...]
    prompt_dir: str
    """Directory under `prompts/` holding this rubric's researcher.md and judge.md."""

    @property
    def tags(self) -> tuple[str, ...]:
        return tuple(d.tag for d in self.dimensions)

    def dimension_list(self) -> str:
        """Markdown bullet list, for templating into prompts."""
        return "\n".join(f"- `{d.tag}` {d.name}: {d.description}" for d in self.dimensions)


R1 = Rubric(
    id="R1",
    name="Catastrophic-risk complicity",
    kind="harm",
    prompt_dir="r1_catastrophic_risk",
    dimensions=(
        Dimension(
            "P1",
            "AI loss of control",
            "Advancing frontier AI without regard for the risks (dissolving safety teams, "
            "shipping over internal warnings, lobbying against AI regulation).",
        ),
        Dimension(
            "P2",
            "AI weaponization and repression",
            "Autonomous weapons, AI in nuclear command and control, mass surveillance; building "
            "or selling to actors with atrocity records.",
        ),
        Dimension(
            "P3",
            "AI misuse and proliferation",
            "Releasing dangerous capabilities without safeguards, selling access without vetting.",
        ),
        Dimension(
            "P4",
            "Fossil fuel",
            "Climate disinformation, lobbying against climate policy, expanding extraction "
            "against the company's own science.",
        ),
        Dimension(
            "P5",
            "Conventional and nuclear arms industry",
            "Sales to regimes with atrocity records, lobbying for escalation, blocking arms "
            "control.",
        ),
    ),
)

RUBRICS: tuple[Rubric, ...] = (R1,)
