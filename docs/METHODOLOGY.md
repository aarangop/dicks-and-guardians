# Methodology: how a person gets scored

This is the overview of the workflow and the scoring method. The rubric anchors, scoring parameters and open questions live in [RUBRIC.md](./RUBRIC.md), which is the source of truth for numbers. If the code and the documents disagree, check which one is newer before trusting either.

## What we are measuring

The project takes its name and core idea from Luke Kemp's *Goliath's Curse* (the "Don't be a dick" pledge about not supporting or working with the Agents of Doom). In this project a "dick" is someone whose **documented behavior** contributes to global catastrophic risk or to the dominance dynamics that Kemp argues drive societal collapse.

The method follows from Kemp's framework:

- **Agents of Doom** (AI labs, fossil fuel, arms) become the catastrophic-risk rubric.
- **Dominance, authoritarianism, inequality and corruption** (the "darker angels" of Goliath states) become the domination, extraction and corruption rubrics.
- **Prestige versus domination** (status earned versus status taken) becomes the benefit side of each rubric: costly acts that reduce risk or share power.
- **The dark triad is not scored directly.** Kemp's claim is contested, and diagnosing people from a distance is neither objective nor defensible. Only the observable behaviors it points to (deception, exploitation, coercion) count, and only when documented.

## Purpose and stance

The project exists to connect abstract catastrophic and existential risks to actual people, decisions and outcomes. It is an information tool for citizens, journalists and researchers: a way to see what people who wield real power are doing, both how they contribute to catastrophic risk and how they help reduce it. That has a few consequences, which are choices and not accidents.

1. **Unequal impact is part of the result.** People differ enormously in how much they can affect the world, and the score reflects that. The same act counts for more when the person had the discretion and the power to do otherwise, or to do more. Scores are unequal because the world is. The pressure belongs on those who can move outcomes.
2. **The same logic applies to good.** Agency and power amplify good acts as they amplify harm, so a lab head who funds independent safety work at scale registers far above someone doing a small hard-won thing. Without this, a difficult personal act and a field-moving decision would sit on one scale, which would be false in the other direction. Two safeguards keep this from being unfair to people with little power. An act that goes against what the person's role expects (a refusal, a veto, a resignation, a disclosure) counts as high agency, because the person alone chose it. And a documented outcome that independent sources attribute to the act lifts its power to the size of the outcome. Real cases exist where a person with little formal power changed a great deal. They are rare, so the method should notice them without making them the norm.
3. **Good and bad are never netted.** Harm and benefit are separate profiles, and nothing converts one into the other. A person can be a Major Dick and a Major Guardian at once, which looks contradictory but describes real people: someone who funds safety research while racing a release, or who whistleblows on a system they helped build. Reconciling the two would need an exchange rate between harms to different people that no one can defend. We choose to show both and to merge nothing.
4. **Position is not destiny, and a score is not a verdict.** The profiles describe documented conduct in a role, not a person's worth. People can change their conduct, and they can change how much leverage they hold, by moving into roles where their choices count for more. The tool is meant to make that visible, not to rank virtue.

## Principles

1. **Judge behaviors and outcomes, never character.**
2. **Researchers collect, judges rate, code decides.** Same inputs, same score.
3. **Every score cites evidence.** No evidence is `insufficient_evidence`, never a guess.
4. **Symmetry.** Anchors describe acts, not affiliations, ideologies or parties.
5. **Harm is provable, absence isn't.** Evidence of harm is enough to rate someone. "Not a Dick" requires documented searches that found nothing.
6. **Good and bad are never netted.** Harm and benefit are scored and reported separately.

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
2. **Research.** Each rubric has its own research agent with its own checklist. It returns sourced findings (claim, verbatim quote, URL, source kind, date, and a polarity: `harm` or `benefit`), structured facts (roles, seniority, highest office, reach, authority, organization size, net worth), the queries it ran, and the gaps it could not fill. For benefit findings it also records whether the act went against the person's role, and the scale and attribution of any documented outcome. It never rates anything. It records both sides, and part of its search budget is reserved for benefit evidence.
3. **Build dossier.** Code, not an LLM, assigns evidence ids and source tiers, so a judge cannot invent or upgrade evidence.
4. **Judge.** One judge call per rubric and side. Each judge sees only its rubric's findings of its own polarity, never outside knowledge and never the other side. It scores each dimension 0-4, cites evidence ids, and explains why that level and not the next. A score of 1 or more must cite evidence, and cannot rest on tier-3 sources alone. Judges do not output confidence, and the side of a verdict is set by the calling code, not by the model.
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

Every rubric has a harm side. A rubric also has a benefit side once its benefit anchors exist, and today only R1 does (the same five pathways, read as costly acts that reduce the risk). Benefit sides for R2-R4 are future work.

R1 uses a "disregard for danger" test: working in an AI lab or an oil company is not enough. What matters is documented indicators such as dissolving safety teams, overriding internal warnings, lobbying against safeguards, or climate disinformation. Passive holdings (index funds, pensions) do not count unless they involve control or engagement.

Personal wealth, lifestyle and consumption are never scored. Wealth is a power modifier only.

## Severity scale

Each rubric side has anchored 0-4 levels with worked examples. The harm shape is shared:

| Level | Meaning |
|---|---|
| 0 | No documented conduct |
| 1 | Minor or peripheral participation, no documented disregard |
| 2 | Direct participation with documented disregard, or moderate scale |
| 3 | Shapes direction, or uses resources or office to expand harm or weaken safeguards |
| 4 | Founds or leads, or uses state or corporate power at scale against warnings |

The benefit side has its own anchors: 0 none documented; 1 low-cost positive action (a modest donation, public support for safety); 2 meaningful costly action (resigning on principle, refusing a contract, internal whistleblowing); 3 major costly action with measurable impact (public whistleblowing at personal risk, refusing major revenue, binding relinquishment of control); 4 sustained, high-cost, high-impact action that changed policy or industry practice. Pledges are not acts. Cost is relative to means. An act must map to a benefit pathway to score at all.

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

All values are placeholders to be tuned on calibration, and they live in one config. RUBRIC.md has the full tables, and it matches the code.

1. **Severity to strength.** A judge's level (0-4) becomes a strength through a lookup table: 0, 0.15, 0.40, 0.70, 1.00. It is deliberately not linear.
2. **Influence.** `influence = agency x (0.4 + 0.6 x power)`, on a 0-1 scale.
   - **Agency:** how much choice and decision authority the person had, by seniority: rank and file 0.25, manager 0.50, executive 0.85, founder or head of state 1.00. A role documented as involuntary halves it.
   - **Power:** read from two extracted facts, how far the person's decisions reach (organization, industry, national, global) and whether they can bind people who did not consent, through law or force (none, shared, unilateral). A head of state binds and a CEO persuades or sells, so a global head of state reads 1.0 and a global CEO 0.85. The highest reading across rubrics counts, with a floor of 0.3 when facts are unknown. Older runs without a reach fall back to organization size and net worth, capped below the top. Extracted facts, not judged.
3. **Combine.** On each side separately, the strongest term dominates and the others add with diminishing returns: `strongest + 0.25 x (1 - strongest) x min(sum of the others, 1)`. A plain average or sum is never used, so one catastrophic act is not diluted by clean scores elsewhere, and many small acts never outweigh one major one.
4. **Harm profile.** `final = harm x influence`.
5. **Benefit profile.** Scored on its own from its own verdicts, as `strength x act-level influence` per dimension (see below). Nothing in it reduces harm, and nothing in harm reduces it.
6. **Tier.** Each score maps to a tier. Harm, evaluated in this order:

| Tier | Meaning |
|---|---|
| Unwilling Dick | `harm >= 0.4` and `influence <= 0.3`: contributes from inside the machine with little agency and power. Takes precedence over every other tier |
| Ultimate Dick | `final >= 0.75`: needs influence of at least 0.75, so high agency and high power. Wields immense power, and leads or drives an Agent of Doom or another form of dominance at scale |
| Major Dick | `final >= 0.45`: serious documented harm, in a decision-making role or with significant power |
| Minor Dick | `final >= 0.1`: limited or small-scale documented harm |
| Not a Dick | Below 0.1. See the rating rule for what this label does and does not claim |

Benefit, a separate ladder that mirrors the harm one with its own thresholds (currently the same numbers):

| Tier | Meaning |
|---|---|
| Ultimate Guardian | `benefit_score >= 0.75`: costly, high-impact action that reduced catastrophic risk at scale |
| Major Guardian | `>= 0.45`: significant documented costly action that reduced risk |
| Minor Guardian | `>= 0.1`, or any benefit the judge scored at level 1 or above (a floor, so a real but low-influence act is never lost): limited or small-scale documented costly action |
| None documented | No benefit scored above 0. The normal case, and never a negative |
| Unrated | The benefit side failed to run or had insufficient evidence |

There is no counterpart to "Unwilling". The cut points are untuned, and RUBRIC.md lists proposed changes to them.

## Rewarding good acts: power, agency and rare high-impact cases

The benefit side uses the same agency and power values as harm. Decision: **keep agency and power on benefit.** Without them, a hard-won small act would sit on the same scale as a wealthy person's act that moves a whole field. The score is meant to place people by capacity to affect outcomes as well as by what they chose to do (see Purpose and stance).

Two refinements, implemented in the scoring code, handle the rare person with little formal power who has a large documented effect.

1. **Agency is measured per act, not per job title.** For harm, low agency means the person was carrying out decisions made above them. For benefit the question is whether the person had discretion over *this act*. An act done as part of an assigned job takes the role-based agency. An act against the role's expectations or incentives (a refusal, a veto, a resignation, a disclosure) is high agency by definition, because the person alone chose it. This can only raise agency, never lower it.
2. **A documented outcome can lift power.** When Tier 1 or Tier 2 sources document an outcome (a policy adopted, a practice changed, a treaty signed) and link it to the act, power for that act is the higher of the role-based power and the power for the outcome's scale. The researcher extracts the outcome's scale and whether a source itself attributes it to the act, and code applies it, so the judge never estimates scale. The outcome must come from a Tier 1 or Tier 2 source. Without a documented, attributed outcome, nothing changes. The harm profile always uses role-based power.

Guardrails:

- Pathway relevance comes first. An act must map to a benefit pathway before it can score. Cost relative to means then sets the level inside the pathway. High personal cost alone never lifts an act above level 1 when it has no measurable effect on a pathway.
- Attribution must be stated in the sources, not inferred from timing. Outcomes with many contributors credit each one as a contribution, never as sole cause.
- Cost counts career, legal, financial and positional risk. The rubric never rewards self-injury.
- Credit that sources dispute (for example, whether a decision actually averted escalation) does not trigger the outcome lift. The act-level agency rule still applies.

### Calibration cases

The rubric's own worked examples are hypothetical archetypes. These are real, documented cases chosen to test the two refinements. They are not scored here. They are checks that the method gives a sensible order. Several fall outside the current catastrophic-risk pathways and belong to benefit sides not yet designed. They illustrate the mechanism, not the pathway anchors.

| Case | What happened | Role-based power and agency | What it tests |
|---|---|---|---|
| **Stanislav Petrov, 1983** | A duty officer at the Soviet early-warning center judged an alert of incoming US missiles to be a false alarm and did not report it as an attack. | Mid-rank officer, little formal power. High agency over the act: the call was the person's alone. | Act-level agency at a chokepoint. Credit for averting escalation is disputed, so no outcome floor. |
| **Frances Kelsey, 1960-62** | An FDA reviewer refused to approve thalidomide despite manufacturer pressure, repeatedly requiring more data. The 1962 Kefauver-Harris Amendments strengthened drug safety and efficacy rules afterwards. | Newly hired reviewer, low power, role-based agency 0.25. Refusing was against the pressure the role faced, so act-level agency is high. | Both refinements together. Documented policy outcome at national scale. |
| **Joseph Rotblat, 1944 and after** | Left the Manhattan Project on moral grounds, later co-founded the Pugwash conferences and shared the 1995 Nobel Peace Prize with them. | Researcher, low formal power. A resignation is an act-level high-agency choice. | Two separate facts scored separately: the resignation (a costly single act) and decades of sustained work. Recency decay applies to the first. |
| **Mario Molina and F. Sherwood Rowland, 1974** | Published the CFC ozone-depletion mechanism, then faced industry pushback. The 1987 Montreal Protocol followed, and both shared the 1995 Nobel Prize in Chemistry. | University researchers, low power. The research itself is within the role. | Shared attribution: many actors contributed to the treaty, so each is credited as a contributor. |
| **Mohamed Bouazizi, 2010** | A street vendor set himself on fire after confrontation with local officials. Protests spread and the Tunisian government fell weeks later, followed by the wider Arab Spring. | No formal power. | Limits of the method. The outcome is enormous, but the act is self-injury, which the rubric never rewards. It also has many downstream causes, so attribution would be disputed. |

### The extremes

- **Recycling versus aligned-AGI funding.** Take a person for whom recycling is very hard, and a billionaire who gives away their fortune to fund aligned-AGI safety and cedes control. The recycling act does not map to any catastrophic-risk pathway, so it scores 0 on the benefit side. The pathway test, not agency, keeps it off the scale. The billionaire's act matches the level 3 anchor ("binding relinquishment of control"). With agency 1.0 and power 1.0, influence is 1.0 and the benefit score is `0.70 × 1.0 = 0.70`, Major Guardian. Reaching Ultimate Guardian would take a level 4 act.
- **Kelsey, with and without the refinements.** Under role-based values (level 3, rank and file agency 0.25, unknown power 0.3): influence is `0.25 × (0.4 + 0.6 × 0.3) = 0.145`, so the score is `0.70 × 0.145 = 0.10`, Minor Guardian by a hair. With act-level agency 1.0 and an attributed national outcome (power 0.6): influence is `1.0 × (0.4 + 0.6 × 0.6) = 0.76`, so the score is `0.70 × 0.76 = 0.53`, Major Guardian. The difference between 0.10 and 0.53 is what the refinements do.

## Rating rule and coverage

- **Required rubrics.** By default R1 and R2 are required. If one of them is among the rubrics run and has no usable harm verdict, the result is `unrated`. The other rubrics are optional, and a failed one only lowers coverage. A usable verdict is one that is not `insufficient_evidence`.
- **Rubrics with no evidence contribute zero**, so the harm score is a floor, and the output reports coverage and confidence. A documented zero (the dossier lists the person's roles) is more confident than an undocumented one.
- **Minimum evidence.** A score of 1 or more must cite evidence and cannot rest on Tier 3 sources alone.
- **"Not a Dick" is a score rule**: the final score is below 0.1. Code does not yet require logged searches on every harm rubric before using the label, so read it together with coverage and confidence. The website marks low-confidence results as provisional.
- **Benefit is rated separately.** No benefit evidence gives None documented. A failed or insufficient benefit side gives Unrated for the benefit tier only, and never changes the harm result.
- Severity, not volume, drives the score. Someone widely written about must not score higher because of the number of articles.

## What the output contains

Every result includes the harm tier and the benefit tier, every per-rubric score for each side with its cited evidence and rationale, agency and power, coverage, confidence for each profile, and a summary that reports both profiles and never nets one against the other. The evidence links are the part to check.

## Limitations

- Only figures with enough public information can be rated. Coverage is uneven, and well-covered people have more discoverable evidence. This is an inherent limitation.
- Evidence quality depends on web sources found at run time, and on the models doing research and judging.
- Benefit evidence is harder to verify than harm. Good acts are cheap to claim, so the benefit side requires independent confirmation and treats an organization's own account of itself as opinion.
- Kemp's thesis is contested by critics, including on his history and his psychology claims. This rubric adopts it as a frame, not as established fact.
- All thresholds are untuned. Calibrate on hand-scored people before trusting a tier. In particular, a person with low influence and only a minor documented finding can read as Not a Dick.
- Not built yet: a breadth multiplier for contributing to several R1 pathways, bands computed from raw numbers, and recency decay.
- A tier is a judgment about documented conduct. It is not a verdict on a person's character.

## Calibration

The README lists the calibration people and the tiers expected for them. The plan is to hand-score them per rubric with sources, check that the formula reproduces the intended tiers, then store real runs as fixtures so later changes to weights or cut points are caught by tests.
