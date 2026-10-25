"""Rubrics as data. Adding a rubric means adding a record here and a prompts/ directory."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Dimension:
    tag: str
    name: str
    description: str


@dataclass(frozen=True)
class Rubric:
    id: str
    name: str
    dimensions: tuple[Dimension, ...]
    prompt_dir: str
    """Directory under `prompts/` holding this rubric's researcher.md and judge.md."""
    has_benefit: bool = False
    """Whether the rubric has benefit anchors. If so, the directory also holds judge_benefit.md.

    Every rubric has a harm side. The benefit side reuses the same dimensions and dossier, and is
    judged and scored separately, never netted against harm.
    """

    @property
    def tags(self) -> tuple[str, ...]:
        return tuple(d.tag for d in self.dimensions)

    def dimension_list(self) -> str:
        """Markdown bullet list, for templating into prompts."""
        return "\n".join(f"- `{d.tag}` {d.name}: {d.description}" for d in self.dimensions)


R1 = Rubric(
    id="R1",
    name="Catastrophic-risk complicity",
    prompt_dir="r1_catastrophic_risk",
    has_benefit=True,
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

R2 = Rubric(
    id="R2",
    name="Domination",
    prompt_dir="r2_domination",
    dimensions=(
        Dimension(
            "D1",
            "Retaliation against critics",
            "Documented retaliation against critics, press, whistleblowers or opponents.",
        ),
        Dimension(
            "D2",
            "Subverting checks",
            "Acts against elections, courts, oversight officials, term limits or independent "
            "institutions.",
        ),
        Dimension(
            "D3",
            "Force or incitement",
            "Use of force, or incitement, against civilians or opponents, with sourced outcomes.",
        ),
        Dimension(
            "D4",
            "Dehumanizing rhetoric",
            "Rhetoric that dehumanizes groups, recorded together with whatever action followed. "
            "Speech alone is capped.",
        ),
    ),
)

R3 = Rubric(
    id="R3",
    name="Extraction and inequality",
    prompt_dir="r3_extraction",
    dimensions=(
        Dimension(
            "X1",
            "Labor exploitation",
            "Wage theft, union-busting rulings, safety violations, forced or coerced labor.",
        ),
        Dimension(
            "X2",
            "Tax structuring",
            "Documented large-scale profit shifting or shell structures, with amounts.",
        ),
        Dimension(
            "X3",
            "Externalized costs",
            "Pollution findings, product-harm cases, unpaid cleanup.",
        ),
        Dimension(
            "X4",
            "Consumer exploitation",
            "Predatory pricing or lending, deceptive terms.",
        ),
        Dimension(
            "X5",
            "Lobbying for extractive rules",
            "Lobbying for rules that reduce taxes, labor protections or liability.",
        ),
    ),
)

R4 = Rubric(
    id="R4",
    name="Corruption and integrity",
    prompt_dir="r4_corruption",
    dimensions=(
        Dimension(
            "C1",
            "Fraud and false statements",
            "Proven fraud, or false statements to regulators, courts, investors or the public "
            "on material facts.",
        ),
        Dimension(
            "C2",
            "Bribery and self-dealing",
            "Proven bribery, embezzlement or self-dealing.",
        ),
        Dimension(
            "C3",
            "Obstruction",
            "Proven obstruction of investigations or proceedings.",
        ),
        Dimension(
            "C4",
            "Conflicts and revolving door",
            "Undisclosed conflicts of interest, and moves between regulators and the regulated.",
        ),
    ),
)

RUBRICS: tuple[Rubric, ...] = (R1, R2, R3, R4)
