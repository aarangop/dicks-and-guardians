# Dickness rubric (draft v0.5)

Status: design draft. The numbers in this document are the ones the code uses (`domain/scoring.py`, `ScoringConfig`), and they are still untuned. Every rubric has a harm side and the code supports a benefit side on any of them. Anchors are drafted for all harm sides (R1-R4) and for the R1 benefit side. Benefit anchors for R2-R4 are not yet designed.

## Principles

1. **Judge behaviors and outcomes, never character.** No diagnosis from a distance (no "psychopath", "narcissist"). Traits from the Dark Triad count only through documented acts: deception, exploitation, coercion.
2. **Researchers collect, judges rate severity, code decides everything else.** The same dossier must always produce the same final score.
3. **Every score cites evidence.** No evidence means `insufficient_evidence`, not zero.
4. **Anchored, behavioral scales.** Each level describes what someone did, with a worked example.
5. **Symmetry.** Anchors describe acts, never affiliations, ideologies or parties. The same act scores the same regardless of who did it.
6. **Good and bad are never netted.** Harm and benefit are two separate profiles with their own scores and tiers. Good done in one area does not offset harm done in another, because harms to different victims are not fungible, and reconciling them would need a moral exchange rate nobody can defend. Someone can be a Major Dick and a Major Guardian at once, and the report shows both. This is a deliberate trade-off. Nothing links the two profiles, not even making amends for the same harm.
7. **Inequality of impact is part of the result.** People with more power and more discretion can do more good and more harm, and the score reflects that. The point is to put the spotlight on those who can move outcomes. Agency and power scale both profiles (see Aggregation).

Theoretical grounding: Kemp, *Goliath's Curse* (dominance hierarchies, Goliath fuel, Agents of Doom, prestige vs. domination). Kemp's psychological claims (dark triad) are contested, which is why this rubric only uses their observable behavioral form.

## Pipeline

```
name -> [research agent per rubric]      -> evidence dossier (structured, sourced, dated)
     -> [judge per rubric and polarity]  -> severity 0-4 + evidence IDs + rationale
     -> [deterministic function]         -> modifiers, harm tier, contribution tier, full breakdown
```

One researcher per rubric collects both sides, and every finding carries a `polarity` (`harm` or `benefit`). The dossier is shared, but each judge call sees only the findings of its own side, so a judge cannot net one side against the other. A person can have findings on both sides of the same rubric.

## Shared rules

### Source tiers

- **Tier 1:** court records, regulatory filings, official orders, primary documents.
- **Tier 2:** major investigative journalism with named sourcing.
- **Tier 3:** opinion, advocacy, social media. Cannot support a score alone.

### Judge output schema (all rubrics)

`polarity` (`harm` or `benefit`), `score` (0-4), `evidence_ids`, `rationale`, `insufficient_evidence` (bool). Severity means harm for the harm polarity and positive impact for the benefit polarity.

### Cross-rubric rules

- **One act, one rubric.** An act is scored in exactly one rubric (see the routing table).
- **Speech alone caps at level 2.** Advocacy, rhetoric or op-eds without money, institutional backing or action cap at L2. Resourced lobbying, funding or action can reach L3+.
- **Allegations are not evidence of conduct.** Record them as `unproven`. Only adjudicated findings, primary documents, or multiple independent Tier 2 sources count.
- **Pardons and sealed or expunged records** do not erase documented conduct. Acquittals do.
- **Settlements without admission** count as Tier 1 evidence of the claim but cap the level at 2.
- **Single acts versus patterns:** no special cap for now. Revisit after calibration.

### Routing table

| Act | Rubric |
|---|---|
| Supplying or advancing a sector capability (including surveillance tech) | R1 |
| Wielding power against opponents or citizens (including using that surveillance) | R2 |
| Business model or policy design that shifts costs onto others | R3 |
| Bribery, embezzlement, fraud, lying to regulators, undisclosed conflicts | R4 |
| Costly action reducing catastrophic risk | Benefit side of R1 (same pathway tags) |
| Costly action restraining domination, reducing extraction, or exposing corruption | Benefit sides of R2-R4 (not yet designed) |

### Spec template (one per rubric)

1. Definition and scope
2. Evidence checklist for the researcher
3. Severity anchors 0-4 with worked examples (hypothetical archetypes, not real people)
4. Boundary cases

## R1: Catastrophic-risk complicity

### Scope

Counts: operating, building, financing, lobbying for, or legislating in favor of activities in the pathways below.

Out of scope:
- Passive holdings (index funds, pension management). Board seats or other control or engagement count.
- Rank and file are in scope, but scored low through the agency modifier, not through the anchors.

### Pathways

The researcher tags each fact with exactly one pathway. P1-P5 count equally. Code takes the strongest pathway score for the rubric. There is no breadth multiplier for contributing to several pathways yet, so someone who contributes to several pathways scores the same as someone who contributes to one (see Open questions).

| Tag | Pathway | Examples of disregard for danger |
|---|---|---|
| P1 | AI loss of control: advancing frontier AI without regard for the risks | Dissolving safety teams, shipping over internal warnings, skipping evaluations, lobbying against or blocking AI regulation |
| P2 | AI weaponization and repression: autonomous weapons, AI in nuclear command and control, mass surveillance | Building or selling to actors with atrocity records, pushing to remove human control from lethal or nuclear decisions |
| P3 | AI misuse and proliferation: powerful capability reaching bad actors | Releasing dangerous capabilities without safeguards, selling access without vetting |
| P4 | Fossil fuel | Climate disinformation, lobbying against climate policy, expanding extraction against the company's own science |
| P5 | Conventional and nuclear arms industry | Sales to regimes with atrocity records, lobbying for escalation, blocking arms control |

Cross-cutting channel: **regulatory obstruction** (lobbying, funding opposition, revolving-door moves) applies to every pathway.

### Disregard indicators (closed list)

The judge may only count these as "documented disregard":

- DI-1: dissolving, defunding or sidelining a safety function
- DI-2: overriding internal safety warnings
- DI-3: skipping or falsifying safety evaluations
- DI-4: lobbying or funding opposition to safety or climate regulation
- DI-5: public statements contradicting documented practice
- DI-6: selling or releasing to actors with a documented abuse record
- DI-7: climate disinformation, or contradicting the organization's own science
- DI-8: pursuing removal of human control from lethal or nuclear decisions
- DI-9: voting against safety or climate safeguards, or for their removal, as a legislator or official with a decisive vote

### Scale

Scale comes from labels the researcher reports in `facts` (reach, authority, and the legacy organization size and net worth bands). The judge sees them in the dossier, and code turns them into power. Code does not yet derive the bands from raw numbers (see Open questions).

### Severity anchors

| Level | Anchor |
|---|---|
| 0 | No documented link, or out of scope (passive holdings) |
| 1 | Participates (employment, contracting, services, small-scale funding), with no documented disregard for risk |
| 2 | Participates with at least one disregard indicator, or directly builds, deploys or sells the harmful capability at moderate scale |
| 3 | Shapes direction: sets strategy, allocates major capital, lobbies (with resources) or legislates (including voting) to expand the activity or weaken safeguards, with documented disregard |
| 4 | Founds or leads an Agent of Doom, or uses state or corporate power to expand it at scale while overriding internal or external safety warnings |

### Worked examples (hypothetical archetypes)

Level 0 in every pathway: index-fund manager, pension trustee, journalist covering the sector, someone whose only link was a brief stint years ago (recency modifier).

| | L1 | L2 | L3 | L4 |
|---|---|---|---|---|
| **P1** | Data-pipeline engineer at a frontier lab that publishes evaluations and keeps a working safety team | Team lead who signs off a model release after internal evaluations flagged dangerous capabilities, with no say in strategy | VP who dissolves the safety team, pushes a release over internal warnings, and has the company lobby against a state AI safety bill | Founder-CEO racing to release while overriding board and safety objections, funding a campaign to block all AI regulation |
| **P2** | Engineer on logistics software at a defense-tech firm, no lethal link | Engineer building the target-recognition component for loitering munitions, human still in the loop | Executive whose strategy is to sell autonomous targeting or mass-surveillance suites to regimes with documented atrocities, lobbying against limits on autonomous weapons | Defense leader who deploys lethal systems with no human oversight at scale, or wires AI into nuclear launch decisions over objections |
| **P3** | Customer-support contractor at an AI API company | Product manager who ships API access with weak vetting after abuse reports | Executive who releases open weights despite internal evaluations showing weapons-relevant uplift, dismisses red-team findings, lobbies against release restrictions | Leader who gives frontier capability to hostile actors, or mass-releases it against government and own-board warnings |
| **P4** | Geologist or accountant at an oil company, no disinformation | Manager running a moderate-scale expansion project, or a communications lead running messaging that contradicts the company's own science | Executive who funds climate disinformation, bankrolls opposition to climate policy, or approves major new extraction against their own scientists' findings | CEO of a major producer who does the above across decades, or a head of state who scales up extraction and dismantles climate regulation |
| **P5** | Machinist at a defense contractor | Sales manager closing deals with regimes that have atrocity records | Executive who lobbies for escalation, blocks arms-control measures, or sells into embargoed markets | CEO or head of state who expands arsenals or arms exports at scale and abandons arms-control treaties |

### Boundary cases

1. **Safety researcher at a lab with documented organizational disregard:** P1 L1 on the harm side. They contribute labor but show no personal disregard. Their safety work is scored on the benefit side, separately, and does not reduce the harm score. Agency keeps the harm low ("Unwilling" shape).
2. **Employee who resigned publicly in protest:** the harm side reflects tenure and role, discounted for recency. The resignation is a benefit-side entry, not an offset.
3. **Rank-and-file researcher writing op-eds against regulation:** P1 L2 (speech cap).
4. **Registered lobbyist hired to block AI regulation:** P1 L3. Not an employee, but they choose the client and the work is regulatory obstruction. Agency is high.
5. **Investor with a board seat directing strategy:** L3. A large stake without control: L0.
6. **Legislator voting on safeguards:** L3, even for a single vote (DI-9). A legislator's vote carries orders of magnitude more influence than a citizen's. The vote must be on legislation whose main purpose is a safeguard or its removal, not an omnibus rider. A vote for safeguards is a benefit-side candidate. Citizens' votes are never scored.

### Evidence checklist (researcher)

- Roles held, with dates and seniority
- Capital invested, raised or allocated, with amounts
- Lobbying, political donations, public positions on regulation
- Documented safety decisions (teams, evaluations, release choices)
- Contracts and customers (P2, P3, P5)
- Statements versus actions

## R2: Domination

### Definition

Using coercion, intimidation or institutional power to suppress opponents, or subverting the checks that constrain power (elections, courts, press, independent institutions). This is Kemp's authoritarian and dominance factor expressed as acts.

### Scope

- Counts: acts by the person, acts they ordered, or acts they knowingly led.
- Does not count: policy positions, party membership, or ideology. Contested policy is not domination. Subverting the process by which policy is checked is.
- Routing: using surveillance against opponents is R2. Building the surveillance system is R1.

### Evidence checklist (researcher)

- Official orders, decrees, firings or purges of oversight officials
- Court rulings involving the person's compliance or defiance
- Documented retaliation against critics, press, whistleblowers or opponents
- Actions concerning election results, election administration or term limits
- Use of force or incitement, with sourced outcomes
- Rhetoric that dehumanizes groups, paired with whatever action followed

### Severity anchors

| Level | Anchor | Example (hypothetical) |
|---|---|---|
| 0 | No documented coercive or check-subverting conduct | |
| 1 | Documented retaliation or coercion in a limited setting, such as a workplace or organization | Manager found by a regulator to have retaliated against an employee who reported a violation |
| 2 | Repeated coercion of critics, press or opponents using institutional or economic leverage, or documented advocacy for subverting democratic checks without the power to act | Billionaire who repeatedly files suits to silence journalists; commentator calling for ignoring court rulings |
| 3 | Uses office or organizational power to subvert a check: attempting to overturn an election result, defying court orders, purging independent officials, harassing the press with state power, or incitement linked to violence | Official who orders firing of independent inspectors and defies a court order to reinstate them |
| 4 | Sustained, systematic dismantling of checks, or violence against civilians or opponents at scale: coups, mass repression, persecution of minorities, indefinite postponement of elections, ordering force against peaceful protesters | Leader who suspends elections and jails the opposition |

### Boundary cases

1. **Dehumanizing rhetoric with no follow-up action:** L2 maximum (speech cap).
2. **Disputed election claims:** counts only if actions followed (lawsuits are legitimate, pressuring officials to change results is not). Judge the action, not the belief.
3. **Emergency powers used lawfully and time-limited:** not domination. Open-ended or unreviewable use is.
4. **Contested allegations of violence:** need Tier 1, or two independent Tier 2 sources, for L3 or above.

## R3: Extraction and inequality

### Definition

Concentrating wealth by shifting costs onto workers, customers, the public or the environment, or by shaping rules to entrench that extraction. This is Kemp's extractive-institutions factor expressed as acts.

### Scope

- Counts: business practices, policy design, lobbying for extractive rules.
- Does not count: **being rich**, personal consumption, or lifestyle. Wealth is a modifier (power), not a behavior. Charity goes to the benefit side.
- Routing: bribery, embezzlement and fraud go to R4. The business model or policy that makes extraction systematic goes to R3.

### Evidence checklist (researcher)

- Labor findings: wage theft, union-busting rulings, safety violations, forced or coerced labor
- Tax and structuring: documented profit shifting, use of shell structures, with amounts
- Externalized costs: pollution findings, product-harm cases, unpaid cleanup
- Consumer exploitation: predatory pricing or lending, deceptive terms
- Lobbying for rules that reduce taxes, labor protections or liability
- Size of affected population and the amounts involved

### Severity anchors

| Level | Anchor | Example (hypothetical) |
|---|---|---|
| 0 | No documented extractive practices | |
| 1 | Isolated violations at small scale (fines, settlements) | Owner of a small firm fined once for unpaid overtime |
| 2 | Repeated violations, or a business model that depends on shifting costs, at moderate scale; or documented large-scale legal avoidance | Manager of a chain with multiple wage-theft findings; executive running a profit-shifting structure |
| 3 | Designs or leads large-scale extraction, or lobbies with resources for rules that entrench it | CEO whose company systematically suppresses wages and busts unions across a country, and funds campaigns to weaken labor law |
| 4 | Societal-scale extraction through state or market capture, or forced labor and dispossession at scale | Official who structures the tax and licensing system to channel national resources to allies; operator of a forced-labor supply chain |

### Boundary cases

1. **Legal tax minimization at ordinary scale:** L0. Only documented large-scale structuring counts.
2. **Employee carrying out extractive policies:** the act is scored, and agency scales it. A payroll clerk does not score like the CEO.
3. **Philanthropy alongside extraction:** both are recorded, on separate profiles. Philanthropy does not offset extraction, and neither does restitution: the benefit act is scored on its own side.

## R4: Corruption and integrity

### Definition

Proven fraud, bribery, self-dealing, conflicts of interest, obstruction, or deception of regulators and the public on material facts.

### Scope

- Counts: **adjudicated findings and primary-source documents only**. The test is "has this been established?", not "is this plausible?"
- Allegations, investigations and rumors are recorded as `unproven` and do not score.
- Routing: lying as a character judgment does not count. Lying to a regulator, court, investor or the public on a material fact, with proof, does.

### Evidence checklist (researcher)

- Criminal convictions and sentences
- Civil judgments and regulatory sanctions (securities, antitrust, ethics bodies)
- Official disclosures showing undisclosed conflicts or self-dealing
- Proven false statements to regulators, courts or investors
- Revolving-door moves between regulators and the regulated, with dates
- Victim counts and amounts

### Severity anchors

| Level | Anchor | Example (hypothetical) |
|---|---|---|
| 0 | Nothing proven (allegations may exist) | |
| 1 | Minor proven integrity breaches: ethics fines, undisclosed conflicts of limited size | Official fined for an undisclosed minor conflict |
| 2 | Proven deception or conflicts at moderate stakes: civil findings of misrepresentation, securities settlements, proven false statements to regulators | Executive who settled with a securities regulator over misleading statements |
| 3 | Conviction or civil liability for fraud, bribery or obstruction, or documented systematic self-dealing in primary sources | Official convicted of taking bribes in exchange for contracts |
| 4 | Large-scale fraud or corruption with major victims or harm, or leading an organization-wide scheme, with conviction | Founder convicted of defrauding customers and investors of billions |

### Boundary cases

1. **Settlement without admission:** L2 maximum.
2. **Conviction overturned on technical grounds:** treat as unproven unless the underlying findings stand.
3. **Revolving door:** legal but documented. L1 alone; L3 if paired with documented favorable decisions.
4. **Pardon:** does not erase the conduct. The underlying finding stands.

## Benefit side

### Definition

Costly, verified actions that reduce catastrophic risk (and later: share power, restrain domination, reduce extraction, expose corruption). This is Kemp's prestige-versus-domination distinction: standing earned by giving up power or advantage instead of taking it.

The benefit side produces its own profile with its own tier ladder (Minor, Major and Ultimate Guardian). It never reduces the harm profile, and the harm profile never reduces it. Every rubric has a harm side, and a rubric opts into a benefit side once its benefit anchors exist. Today only R1 has them.

### Scope

- **Pledges are not actions.** Only executed actions count.
- **Independent confirmation.** The person's own organization saying it did something is Tier 3 and cannot support a score. Impact needs a Tier 1 or Tier 2 source.
- **Cost is relative to means.** The researcher records cost as a share of the person's resources or career at stake. A $1M donation by a billionaire is not a costly act.
- **Pathway first.** An act must map to a benefit pathway before it can score. Cost relative to means then sets the level inside the pathway. High personal cost alone never lifts an act above level 1 when it has no measurable effect on a pathway. Recycling, for example, maps to no catastrophic-risk pathway and scores 0.
- **Not counted:** philanthropy that also buys influence against safety or democratic checks (for example funding groups that lobby against regulation).
- **Agency and power scale benefit like they scale harm**, measured per act (see Aggregation). A lab head who funds safety at scale contributes more than an intern doing the same.
- **Zero is the default.** No documented benefit is not a negative. It never feeds the harm score and never lowers any tier.
- **Speech alone caps at L1** (statements of concern, open letters with no action).

### Facts the researcher extracts for a benefit act

Extracted, never judged:

- `against_role`: the act went against what the person's role or incentives expected (a refusal, veto, resignation or disclosure), as opposed to work done as assigned.
- `outcome_scale`: size band of the documented outcome (policy adopted, practice changed, treaty signed), or `unknown`.
- `outcome_attributed`: a source itself links that outcome to this act. Outcomes with many contributors credit each one as a contributor, never as sole cause.

### Pathways (R1 benefit side)

Benefit facts use the same tags as R1, so the two sides read side by side.

| Tag | Pathway | Examples of costly mitigation |
|---|---|---|
| P1 | AI loss of control | Resigning on principle over safety, internal or public safety whistleblowing, funding independent evaluation, ceding control to an external safety body, supporting binding AI regulation against one's own interest |
| P2 | AI weaponization and repression | Refusing a defense or surveillance contract, working to keep human control over lethal and nuclear decisions, disclosing misuse by state actors |
| P3 | AI misuse and proliferation | Withholding or delaying a release over weapons-relevant risk, building and enforcing vetting for access, disclosing dangerous capabilities responsibly |
| P4 | Fossil fuel | Disclosing the company's own climate science, divesting or giving up extraction revenue, backing binding climate policy against one's interest |
| P5 | Conventional and nuclear arms industry | Refusing sales to regimes with atrocity records, supporting arms-control and verification, whistleblowing on illicit transfers |

### Evidence checklist (researcher)

- Resignations, refusals of contracts or deals, and what they cost
- Whistleblowing, with the channel used and the personal risk
- Divestment or revenue given up
- Funding of independent oversight or safety research, with amounts relative to means
- Voluntarily binding commitments and whether they were kept
- Documented outcomes (policies adopted, practices changed), from independent sources

### Severity anchors (benefit)

| Level | Anchor | Example (hypothetical) |
|---|---|---|
| 0 | None documented | |
| 1 | Low-cost positive actions: modest donations, public support for safety or democratic checks | Engineer who signs an open letter and donates modestly |
| 2 | Meaningful costly action: resigning on principle, refusing a contract, internal whistleblowing, divestment at a financial cost, moderate funding of oversight | Researcher who resigns and publicly explains why |
| 3 | Major costly action with measurable impact: public whistleblowing with personal risk, refusing major revenue, sustained funding of independent oversight, binding relinquishment of control | Executive who cedes board control to an external safety body |
| 4 | Sustained, high-cost, high-impact action that changed policy or industry practice, at serious personal or financial risk | Insider whose disclosures led to binding regulation, at the cost of their career |

### Boundary cases

1. **Donation to safety research from wealth earned in the same sector:** counts, but cost-to-means decides the level. It does not offset harm, so it cannot launder it.
2. **Resignation followed by joining a competitor doing the same thing:** zero, unless the departure involved a documented principled objection.
3. **Public statements of concern with no action:** L1 maximum.
4. **Safety funding by someone convicted of fraud:** a benefit finding and a fraud finding. Neither changes the other.
5. **Whistleblower exposing the system they helped build:** a benefit act on the benefit side. It does not reduce the harm of having built the system. Both profiles show.
6. **Making amends for a specific harm** (restitution, a recall): scored as a benefit act at the level its cost supports. It does not reduce the harm score for the same harm.

## Deterministic layer

All of this lives in `ScoringConfig` in `domain/scoring.py`, so calibration means changing configuration and not logic. Scores are on a 0-1 scale.

### Structured facts extracted by researchers (not judged by the LLM)

- Roles: title, organization, seniority (`rank_and_file`, `manager`, `executive`, `founder_or_head_of_state`), dates, and whether the role was voluntary (true, false or unknown).
- Highest office held. Any value counts as holding an office.
- Reach (`unknown`, `organization`, `industry`, `national`, `global`): how far the decisions the person can make or trigger travel.
- Authority (`unknown`, `none`, `shared`, `unilateral`): whether the person can bind people who did not consent, through law or force. `unilateral` by their own decision (head of state or government, agency head, security chief), `shared` through a vote or seat in a body that binds others (legislator, panel judge), `none` if they can only persuade, sell or employ. Owning or running a company is `none`, however large.
- Organization size band (`unknown`, `small`, `large`, `very_large`) and net worth band (`unknown`, `under_10m`, `10m_to_1b`, `1b_to_100b`, `over_100b`). Legacy readings, used for power only when reach is unknown, and still used for the scale of a benefit outcome. The researcher reports the band directly.
- Evidence tier of each item. Code assigns it from the source kind and the URL host, never the model.
- For benefit facts: `against_role`, `outcome_scale` and `outcome_attributed` (see Benefit side).

Not extracted yet: recency or duration of acts, and cost as a share of means as a structured number (the cost is written in the claim and the judge reads it).

### Severity to strength

The judge's level becomes a strength with a lookup table. It is deliberately not linear: a level 1 is small and a level 4 is full strength.

| Severity | 0 | 1 | 2 | 3 | 4 |
|---|---|---|---|---|---|
| Strength | 0 | 0.15 | 0.40 | 0.70 | 1.00 |

### Agency, power and influence

**Agency** is the strongest value among the person's documented roles, halved when a role is documented as involuntary. With no documented roles it defaults to 0.5, and the result says so.

| Seniority | Agency |
|---|---|
| Rank and file | 0.25 |
| Manager | 0.50 |
| Executive | 0.85 |
| Founder or head of state | 1.00 |

**Power** is the highest reading across all rubrics' facts, with a floor of 0.3 (the value for `unknown`). When the researcher reports a reach, power is read from reach and authority. Binding people who did not consent, through law or force, is worth more than persuading or selling to people who can say no. That is the difference between a head of state and a very large company.

| Reach | Authority `none` | `shared` | `unilateral` |
|---|---|---|---|
| organization | 0.20 | 0.30 | 0.40 |
| industry | 0.45 | 0.55 | 0.65 |
| national | 0.65 | 0.75 | 0.90 |
| global | 0.85 | 0.90 | 1.00 |

An unknown authority reads as `none`, so a missing fact never inflates power. Only a global reach with unilateral authority reaches 1.0.

When reach is unknown (older runs), power falls back to legacy readings, capped at 0.85 so wealth or size alone never reaches the top:

| Organization size | Power | Net worth | Power |
|---|---|---|---|
| unknown | 0.30 | unknown | 0.30 |
| small | 0.20 | under $10M | 0.10 |
| large | 0.60 | $10M - $1B | 0.50 |
| very large | 0.85 (capped) | $1B - $100B | 0.85 |
| | | over $100B | 0.85 (capped) |

A documented highest office reads 0.90 in that fallback, above every capped legacy reading.

**Influence** combines them: `influence = agency x (0.4 + 0.6 x power)`. The 0.4 is a floor, so even someone with no power keeps 40% of their agency-weighted influence. Influence runs from about 0.15 (rank and file, unknown power) to 1.0 (founder with maximum power).

### Aggregation

- Within a rubric, the strongest dimension sets the rubric's strength. Dimension weights and rubric weights exist in the config for the harm side and default to 1.0.
- Across rubrics, each side combines max-dominant: `combined = strongest + 0.25 x (1 - strongest) x min(sum of the others, 1)`. The strongest term dominates, and the others add with diminishing returns. A plain average is never used, so one catastrophic act is not diluted. A plain sum is never used either, so many small acts never outweigh one major one. A plain probabilistic OR was tried and rejected: it scored four minor offenses too high.
- **Harm profile:** `harm` is the combined strength, and `final = harm x influence`.
- **Benefit profile:** each benefit dimension is `strength x act-level influence`, where agency and power are measured per act (see Benefit side). The strongest dimension per rubric is combined across rubrics with the same formula. Nothing in either profile enters the other.
- Score severity, not volume of evidence. A famous person with a thick dossier must not score higher just because more was written about them.

### Confidence and coverage

- **Coverage:** the share of harm rubrics with a usable verdict.
- **Confidence per usable rubric:** when the verdict cites evidence, the sum of the cited items' tier quality divided by 3, capped at 1. Tier quality is 1.0 for Tier 1, 0.7 for Tier 2 and 0.3 for Tier 3. When nothing is cited, it is 0.5 if the dossier documents the person's roles (a documented zero) and 0.25 if not.
- **Harm confidence** is coverage times the mean confidence of the usable rubrics. **Benefit confidence** is the same over the benefit rubrics.
- Confidence is computed from evidence and never from the judge's self-report. The website marks results below 0.5 confidence as provisional.

## Final score and tiers

Tuned only on hypothetical archetypes. Recency decay is not in the formula. The report carries two independent results, harm and benefit, and never merges them.

### Harm tiers

Evaluated in this order on `harm`, `influence` and `final`:

| Tier | Rule |
|---|---|
| Unwilling Dick | `harm >= 0.4` and `influence <= 0.3`. Takes precedence over every other tier. |
| Ultimate Dick | `final >= 0.75` |
| Major Dick | `final >= 0.45` |
| Minor Dick | `final >= 0.1` |
| Not a Dick | otherwise |
| Unrated | A required rubric has no usable verdict (see Rating rule) |

There is no separate systemic-power condition. `final >= 0.75` already needs influence of at least 0.75, which takes high agency and high power. The website calls power of 0.75 or more "systemic" for display only.

Two consequences of the rules as implemented. The Unwilling rule applies to any rubric, and needs harm of at least 0.4, which means at least a level 2. And a person with low influence and only a level 1 finding falls below the Minor cut and reads as Not a Dick, even though a documented finding exists.

### Benefit tiers

The ladder mirrors the harm ladder. It uses its own thresholds, which currently equal the harm ones, and there is no counterpart to Unwilling.

The Minor floor exists because influence can push a real, confirmed act below the 0.1 cut: a junior person's level 2 act scores 0.06. The judge only scores 1 or higher with cited evidence, so such an act is documented, and "None documented" must mean none was found. The floor does not apply to the harm side.

| Tier | Rule |
|---|---|
| Ultimate Guardian | `benefit_score >= 0.75` |
| Major Guardian | `benefit_score >= 0.45` |
| Minor Guardian | `benefit_score >= 0.1`, **or** any benefit the judge scored at level 1 or above (the floor) |
| None documented | No benefit scored above 0. The normal case, and never a negative. |
| Unrated | The benefit side failed to run or had insufficient evidence |

### Sanity check (harm archetypes)

These are the real outputs of `compute_score` for hypothetical archetypes.

| Archetype | Final | Tier |
|---|---|---|
| Founder-CEO of a frontier lab, R1 L4, over $100B, very large org | 1.00 | Ultimate |
| Lab VP, R1 L3, large org | 0.45 | Major (on the edge of the cut) |
| Legislator, one decisive vote against safeguards (R1 L3, national office) | 0.52 | Major |
| Team lead who signed off a risky release (R1 L2, manager, large org) | 0.15 | Minor |
| Rank and file, R1 L1, large org | 0.03 | Not a Dick (documented, below the Minor cut) |
| Rank and file, R1 L2, large org | 0.08 | Unwilling |
| Rank and file with R1 L2 and R4 L2, large org | 0.09 | Unwilling |
| Founder convicted of large-scale fraud (R4 L4), small org | 0.58 | Major |
| Executive at a very large org, L1 on R1, R3 and R4 | 0.17 | Minor |
| Executive at a very large org, L2 on R1, R3 and R4 | 0.42 | Minor (just under the Major cut) |
| Head of state, R2 L4, R1 L3, R3 L2, R4 L1 | 0.88 | Ultimate |

### Sanity check (benefit archetypes)

Real outputs for the benefit profile alone, with a level 1 to 4 act. "Against the role" is `against_role = true`. "Outcome" adds an attributed outcome of `large` scale from a Tier 1 or Tier 2 source. Pair each row with the same person's harm profile, never net them.

| Subject | Level | Role-based | Against the role | Against the role, with outcome |
|---|---|---|---|---|
| Rank and file, small org | L2 | 0.06 Minor (floor) | 0.23 Minor | 0.30 Minor |
| Rank and file, small org | L3 | 0.10 Minor | 0.41 Minor | 0.53 Major |
| Rank and file, small org | L4 | 0.15 Minor | 0.58 Major | 0.76 Ultimate |
| Manager, large org | L3 | 0.27 Minor | 0.53 Major | 0.53 Major |
| Manager, large org | L4 | 0.38 Minor | 0.76 Ultimate | 0.76 Ultimate |
| Executive, very large org | L2 | 0.32 Minor | 0.38 Minor | 0.38 Minor |
| Executive, very large org | L3 | 0.56 Major | 0.66 Major | 0.66 Major |
| Executive, very large org | L4 | 0.80 Ultimate | 0.94 Ultimate | 0.94 Ultimate |
| Founder, over $100B | L2 | 0.40 Minor | 0.40 Minor | 0.40 Minor |
| Founder, over $100B | L3 | 0.70 Major | 0.70 Major | 0.70 Major |
| Founder, over $100B | L4 | 1.00 Ultimate | 1.00 Ultimate | 1.00 Ultimate |

What the numbers show:

- A level 2 act can never reach Major Guardian, because the strongest case is 0.40.
- Major Guardian takes a level 3 act with influence of about 0.64 or more, or a junior person's level 3 act with a documented attributed outcome.
- Ultimate Guardian takes a level 4 act with influence of at least 0.75. For a junior person that comes from acting against the role plus a documented outcome. For a manager at a large organization, acting against the role alone is already enough.
- A documented act at level 1 or 2 by someone with little influence scores below 0.1. The Minor floor keeps it from reading as None documented.

Combined reports, for illustration. The two results are listed side by side and never merged:

| Person | Harm | Benefit |
|---|---|---|
| Founder-CEO, R1 L4, over $100B, who also funds independent safety evaluation (L2) | 1.00, Ultimate Dick | 0.40, Minor Guardian |
| Lab VP, R1 L3, large org, who later blows the whistle publicly (L3, against the role) | 0.45, Major Dick | 0.53, Major Guardian |
| Same VP, no documented benefit | 0.45, Major Dick | None documented |

### Rating rule (as implemented)

- **Required rubrics.** `required_rubric_ids` in the config, by default R1 and R2. If a required rubric is among the ones run and has no usable harm verdict, the result is `unrated`. The other rubrics are optional: a failed one only lowers coverage. A usable verdict is one that is not `insufficient_evidence`.
- **Rubrics with no evidence contribute 0**, so the harm score is a floor. Coverage and confidence are reported, and a documented zero is more confident than an undocumented one.
- **Minimum evidence.** A score of 1 or more must cite evidence, and cannot rest on Tier 3 sources alone. Tier 3 alone therefore cannot raise anyone above zero.
- **"Not a Dick" is a score rule** (`final < 0.1`). Code does not yet require logged searches on every harm rubric before using the label. A researcher that failed or found nothing leaves that rubric out of coverage, which lowers confidence, and low-confidence results show as provisional.
- **The benefit profile has its own rating.** At least one Tier 1 or Tier 2 item must confirm the act. No benefit evidence gives None documented, which is not a harm finding. A failed or insufficient benefit side gives Unrated for the benefit tier only, and never changes the harm result.

## Decisions log

- Big Tech scope: narrowed to behavior (disregard for danger) across AI pathways P1-P3, not membership in a sector.
- Passive holdings: out of scope unless control or engagement.
- One R1 rubric with pathway tags, not one rubric per sector.
- Group acts: attributed to individuals proportionally to agency.
- Speech alone caps at L2 across rubrics.
- Hired lobbyists against safeguards score L3 (P1) even when not employees.
- No single-act cap for now. Revisit after calibration.
- Personal wealth and consumption are not scored. Wealth is a power modifier.
- Allegations never score. Settlements without admission cap at L2.
- Pathways P1-P5 weigh equally, and the strongest dominates. There is no breadth multiplier yet.
- Scale is categorical. The researcher reports reach, authority, size and net worth bands and code maps them to power. Deriving bands from raw numbers is future work.
- Good and bad are never netted. Harm and benefit are separate profiles with separate tiers (Minor, Major and Ultimate Guardian, mirroring the Dick ladder). Nothing links them: no remediation offset either.
- R5 is retired. Every rubric has a harm side, and a rubric opts into a benefit side once its anchors exist. First iteration: R1 only, with pathways P1-P5.
- One researcher per rubric collects both sides, and each finding carries a polarity. One judge call per side, and each judge sees only its own side's findings.
- Benefit facts need independent confirmation. The person's own organization's claims are Tier 3.
- Each side aggregates max-dominant, not as a sum. Volume does not inflate a score.
- Agency and power stay on the benefit side, measured per act: acting against the role gives high agency, and an attributed, independently sourced outcome lifts power. Inequality of impact is part of the result by design.
- A benefit act must map to a pathway. Cost relative to means sets the level inside it.
- Output includes every per-rubric score with evidence, plus the final tier.
- Scope is figures with enough public data. Below a minimum evidence threshold the result is `unrated`. This is an inherent limitation.
- A legislator voting on safeguards scores L3 (DI-9).
- A vote and the donations received are separate facts, scored separately.
- R1 and R2 are required to rate someone. The other rubrics are optional and only lower coverage when missing.
- Score combination is max-dominant with diminishing additions, not a plain probabilistic OR.
- Ultimate (harm and benefit) needs a score of 0.75. There is no separate systemic-power condition. Influence of at least 0.75 already takes high agency and power.

## Open questions

- All numbers are placeholders to tune on calibration against hand-scored people: strengths, agency, power, the influence floor, the combination weight and the cut points.
- **Guardian cut points.** Keep Minor at 0.1, Major at 0.45 and Ultimate at 0.75 for now. They give a sensible shape: level 2 tops out at Minor, level 3 reaches Major with real influence or an attributed outcome, and Ultimate needs a level 4 act. Changes so far: (1) Done: a documented, confirmed benefit at level 1 or above has a Minor Guardian floor. (2) Not done: gate both Ultimate tiers on power of at least 0.75, so Ultimate means a systemic role or a systemic outcome. Today a manager at a large organization reaches Ultimate Guardian with a level 4 act against the role and no documented outcome. Re-tune the benefit cuts separately from the harm cuts once there are real runs.
- **Low-influence harm.** A documented level 1 finding by someone with low influence reads as Not a Dick, and the Unwilling rule only starts at level 2. Decide whether a documented minor finding should have a tier of its own.
- **Breadth multiplier.** Contributing to several R1 pathways does not raise the score yet. The same question applies to the benefit side.
- **Bands from numbers.** Have the researcher extract raw numbers and let code compute the bands, as originally designed, instead of the researcher choosing a band. The size scale could also gain a moderate band.
- **Systemic-power condition and the Unwilling rule.** The code decides Ultimate by score alone and Unwilling by harm and influence thresholds. Decide whether to restore the stricter definitions from earlier drafts (Unwilling: low agency, R1 severity of at least 1, no other rubric at level 2 or above).
- **Rating coverage.** Whether "Not a Dick" should require logged searches on every harm rubric, and whether the label "No harm found (partial coverage)" should exist.
- **Recency decay.** How fast old acts fade. Not yet in the formula.
- Low priority: R1 anchors L1-L2 describe junior roles and the agency value then discounts again. Junior roles are not the target population, so this is parked.
- Whether the team-lead archetype should sit in Minor or Major.
- Should making amends for a specific harm be recognized on the harm side? Today it is not, because the two profiles have no link.
- Should the Guardian ladder get a counterpart to Unwilling, or is a three-tier ladder enough?
- Benefit sides for R2-R4: defending checks, fair labor, exposing fraud.
