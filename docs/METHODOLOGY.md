# Methodology: how a person gets scored

This is the overview of the workflow and the scoring method. The rubric anchors, scoring parameters and open questions live in [RUBRIC.md](./RUBRIC.md), which is the source of truth for numbers. If the code and the documents disagree, check which one is newer before trusting either.

## What we are measuring

The project takes its name and core idea from Luke Kemp's *Goliath's Curse* (the "Don't be a dick" pledge about not supporting or working with the Agents of Doom). In this project a "dick" is someone whose **documented behavior** contributes to global catastrophic risk or to the dominance dynamics that Kemp argues drive societal collapse.

The method follows from Kemp's framework:

- **Agents of Doom** (AI labs, fossil fuel, arms) become the catastrophic-risk rubric.
- **Dominance, authoritarianism, inequality and corruption** (the "darker angels" of Goliath states) become the domination, extraction and corruption rubrics.
- **Prestige versus domination** (status earned versus status taken) becomes the counterweight rubric.
- **The dark triad is not scored directly.** Kemp's claim is contested, and diagnosing people from a distance is neither objective nor defensible. Only the observable behaviors it points to (deception, exploitation, coercion) count, and only when documented.

## Principles

1. **Judge behaviors and outcomes, never character.**
2. **Researchers collect, judges rate, code decides.** Same inputs, same score.
3. **Every score cites evidence.** No evidence is `insufficient_evidence`, never a guess.
4. **Symmetry.** Anchors describe acts, not affiliations, ideologies or parties.
5. **Harm is provable, absence isn't.** Evidence of harm is enough to rate someone. "Not a Dick" requires documented searches that found nothing.

## Workflow

```
name (+ optional descriptor)
  -> resolve        who is this? public figure? ambiguous? refuse
  -> research       one agent per rubric, in parallel, using web search and fetch
  -> build dossier  code assigns evidence ids and source tiers, drops duplicates
  -> judge          one judge per rubric rates severity 0-4 per dimension, citing evidence
  -> score          deterministic function combines verdicts and extracted facts
  -> summarize      plain-language summary of the score and its evidence
```

1. **Resolve.** Searches the exact name. If several notable people share it, the service asks for disambiguation. Private individuals are refused: only public figures with substantial independent coverage are in scope.
2. **Research.** Each rubric has its own research agent with its own checklist. It returns sourced findings (claim, verbatim quote, URL, source kind, date), structured facts (roles, seniority, highest office, organization size, net worth), the queries it ran, and the gaps it could not fill. It never rates anything. It is told to record counter-evidence too.
3. **Build dossier.** Code, not an LLM, assigns evidence ids and source tiers, so a judge cannot invent or upgrade evidence.
4. **Judge.** Each judge sees only its rubric's dossier, never outside knowledge. It scores each dimension 0-4, cites evidence ids, and explains why that level and not the next. A score of 1 or more must cite evidence, and cannot rest on tier-3 sources alone. Judges do not output confidence.
5. **Score.** A pure function. All numbers live in a config so calibration means changing configuration, not logic.
6. **Summarize.** Explains the result. A failure here never blocks the score.

A failing research or judge step for one rubric is recorded and does not sink the others.

## Rubrics

| # | Rubric | Measures |
|---|---|---|
| R1 | Catastrophic-risk complicity | Contribution to the Agents of Doom, judged by disregard for danger. Five pathways: P1 AI loss of control, P2 AI weaponization and repression, P3 AI misuse and proliferation, P4 fossil fuel, P5 conventional and nuclear arms |
| R2 | Domination | Coercion, or subverting checks on power (elections, courts, press) |
| R3 | Extraction and inequality | Concentrating wealth by shifting costs onto workers, customers, the public or the environment |
| R4 | Corruption and integrity | Proven fraud, bribery, conflicts of interest, deception of regulators or the public |
| R5 | Counterweight | Costly, executed actions that reduce risk or share power (can only lower a score) |

R1 uses a "disregard for danger" test: working in an AI lab or an oil company is not enough. What matters is documented indicators such as dissolving safety teams, overriding internal warnings, lobbying against safeguards, or climate disinformation. Passive holdings (index funds, pensions) do not count unless they involve control or engagement.

Personal wealth, lifestyle and consumption are never scored. Wealth is a power modifier only.

## Severity scale

Each harm rubric has anchored 0-4 levels with worked examples. The shape is shared:

| Level | Meaning |
|---|---|
| 0 | No documented conduct |
| 1 | Minor or peripheral participation, no documented disregard |
| 2 | Direct participation with documented disregard, or moderate scale |
| 3 | Shapes direction, or uses resources or office to expand harm or weaken safeguards |
| 4 | Founds or leads, or uses state or corporate power at scale against warnings |

Cross-rubric rules:

- Speech alone (op-eds, rhetoric) caps at level 2. Resourced action can go higher.
- Allegations never score. Only adjudicated findings, primary documents or several independent reliable sources count.
- Settlements without admission cap at level 2. Pardons do not erase conduct.
- A hired lobbyist against safeguards counts (level 3), and so does a legislator's decisive vote on a safeguard (level 3). Citizens' votes are never scored.
- Each act is scored in exactly one rubric.

## Evidence tiers

- **Tier 1:** court records, regulatory filings, official orders, primary documents.
- **Tier 2:** major investigative journalism and reliable reporting.
- **Tier 3:** opinion, advocacy, social media. Cannot support a score alone.

Confidence is computed from the tiers and number of evidence items cited, never self-reported by a judge.

## From verdicts to a final score

All values are placeholders to be tuned on calibration. See RUBRIC.md for current numbers.

1. **Severity to strength.** Each harm rubric's severity (0-4) becomes a 0-1 value, multiplied by **agency** and **power**.
   - **Agency:** how much choice and decision authority the person had (rank and file, manager, executive, founder or head of state). Involuntary roles reduce it. Score is proportional to agency, so employees rank below executives.
   - **Power:** organization size, net worth and office, in log-scale bands. Extracted facts, not judged.
2. **R1 breadth.** Contributing to several independent R1 pathways acts as a risk multiplier compared with contributing to one.
3. **R5 offsets.** Counterweight evidence reduces only the rubric it is tagged to, can never push an axis below zero, and can lower the final tier by at most one level.
4. **Combine.** The worst axis dominates and the others add with diminishing returns. A plain average is never used, so one catastrophic act is not diluted by clean scores elsewhere.
5. **Tier.** The 0-100 score maps to a tier, with extra conditions:

| Tier | Meaning |
|---|---|
| Ultimate Dick | Highest harm **and** systemic power: wields immense power, leads or drives an Agent of Doom or another form of dominance at scale |
| Major Dick | Serious documented harm, in a decision-making role or with significant power |
| Unwilling Dick | Contributes from inside the machine with little agency (rank and file) and no other serious findings |
| Minor Dick | Limited or small-scale documented harm |
| Not a Dick | Searched thoroughly across harm rubrics, nothing found |

## Rating rule and coverage

- One rubric with Tier 1 or Tier 2 evidence is enough to rate someone. Rubrics with no evidence contribute zero, so the score is a floor, and the output reports coverage.
- "Not a Dick" requires logged searches on all harm rubrics that found nothing. A researcher that failed or found no data returns `insufficient_evidence`, which is different from a documented zero. With partial coverage the result reads "no harm found (partial coverage)".
- No evidence on any rubric gives `unrated`.
- Severity, not volume, drives the score. Someone widely written about must not score higher because of the number of articles.

## What the output contains

Every result includes the tier, every per-rubric score with its cited evidence and rationale, agency and power, coverage, confidence, and a summary. The evidence links are the part to check.

## Limitations

- Only figures with enough public information can be rated. Coverage is uneven, and well-covered people have more discoverable evidence. This is an inherent limitation.
- Evidence quality depends on web sources found at run time, and on the models doing research and judging.
- Kemp's thesis is contested by critics, including on his history and his psychology claims. This rubric adopts it as a frame, not as established fact.
- All thresholds are untuned. Calibrate on hand-scored people before trusting a tier.
- A tier is a judgment about documented conduct. It is not a verdict on a person's character.

## Calibration

The README lists the calibration people and the tiers expected for them. The plan is to hand-score them per rubric with sources, check that the formula reproduces the intended tiers, then store real runs as fixtures so later changes to weights or cut points are caught by tests.
