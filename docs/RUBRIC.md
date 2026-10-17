# Dickness rubric (draft v0.2)

Status: design draft. Anchors for all five rubrics are drafted. Numeric weights and size-band thresholds are not set yet.

## Principles

1. **Judge behaviors and outcomes, never character.** No diagnosis from a distance (no "psychopath", "narcissist"). Traits from the Dark Triad count only through documented acts: deception, exploitation, coercion.
2. **Researchers collect, judges rate severity, code decides everything else.** The same dossier must always produce the same final score.
3. **Every score cites evidence.** No evidence means `insufficient_evidence`, not zero.
4. **Anchored, behavioral scales.** Each level describes what someone did, with a worked example.
5. **Symmetry.** Anchors describe acts, never affiliations, ideologies or parties. The same act scores the same regardless of who did it.

Theoretical grounding: Kemp, *Goliath's Curse* (dominance hierarchies, Goliath fuel, Agents of Doom, prestige vs. domination). Kemp's psychological claims (dark triad) are contested, which is why this rubric only uses their observable behavioral form.

## Pipeline

```
name -> [research agent per rubric] -> evidence dossier (structured, sourced, dated)
     -> [judge per rubric]          -> severity 0-4 + evidence IDs + rationale
     -> [deterministic function]    -> modifiers, final tier, full breakdown
```

## Shared rules

### Source tiers

- **Tier 1:** court records, regulatory filings, official orders, primary documents.
- **Tier 2:** major investigative journalism with named sourcing.
- **Tier 3:** opinion, advocacy, social media. Cannot support a score alone.

### Judge output schema (all rubrics)

`score` (0-4), `evidence_ids`, `rationale`, `insufficient_evidence` (bool).

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
| Costly action reducing harm or sharing power | R5 |

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

The researcher tags each fact with one pathway. Code takes the max across pathways.

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

### Scale

"Moderate scale" and "large scale" come from structured size bands extracted by the researcher (revenue, units, users, spend). Thresholds TBD.

### Severity anchors

| Level | Anchor |
|---|---|
| 0 | No documented link, or out of scope (passive holdings) |
| 1 | Participates (employment, contracting, services, small-scale funding), with no documented disregard for risk |
| 2 | Participates with at least one disregard indicator, or directly builds, deploys or sells the harmful capability at moderate scale |
| 3 | Shapes direction: sets strategy, allocates major capital, or lobbies or legislates (with resources) to expand the activity or weaken safeguards, with documented disregard |
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

1. **Safety researcher at a lab with documented organizational disregard:** P1 L1. They contribute labor but show no personal disregard. R5 evidence offsets. Agency keeps them low ("Unwilling" shape).
2. **Employee who resigned publicly in protest:** R1 reflects tenure and role, discounted for recency. R5 gets a positive entry.
3. **Rank-and-file researcher writing op-eds against regulation:** P1 L2 (speech cap).
4. **Registered lobbyist hired to block AI regulation:** P1 L3. Not an employee, but they choose the client and the work is regulatory obstruction. Agency is high.
5. **Investor with a board seat directing strategy:** L3. A large stake without control: L0.
6. **Legislator with a single vote against safeguards:** unresolved. A pattern with industry funding is L3 (legislating). A single vote is probably L2.

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
- Does not count: **being rich**, personal consumption, or lifestyle. Wealth is a modifier (power), not a behavior. Charity goes to R5.
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
3. **Philanthropy alongside extraction:** both are recorded. R5 offsets only within its cap.

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

## R5: Counterweight

### Definition

Costly, verified actions that reduce catastrophic risk, share power, or restrain domination. This is Kemp's prestige-versus-domination distinction: standing earned by giving up power or advantage instead of taking it.

### Scope

- R5 can only reduce the final score, up to a fixed cap set in code.
- **Pledges are not actions.** Only executed actions count.
- **Cost is relative to means.** The researcher records cost as a share of the person's resources or career at stake. A $1M donation by a billionaire is not a costly act.
- Not counted: philanthropy that also buys influence against safety or democratic checks (for example funding groups that lobby against regulation).
- Each entry is tagged with the rubric it offsets (R1-R4). Offsets across rubrics count less than within the same rubric.

### Evidence checklist (researcher)

- Resignations, refusals of contracts or deals, and what they cost
- Whistleblowing, with the channel used and the personal risk
- Divestment or revenue given up
- Funding of independent oversight, safety research, or democratic institutions, with amounts relative to means
- Voluntarily binding commitments and whether they were kept
- Documented outcomes (policies adopted, practices changed)

### Severity anchors (benefit)

| Level | Anchor | Example (hypothetical) |
|---|---|---|
| 0 | None documented | |
| 1 | Low-cost positive actions: modest donations, public support for safety or democratic checks | Engineer who signs an open letter and donates modestly |
| 2 | Meaningful costly action: resigning on principle, refusing a contract, internal whistleblowing, divestment at a financial cost, moderate funding of oversight | Researcher who resigns and publicly explains why |
| 3 | Major costly action with measurable impact: public whistleblowing with personal risk, refusing major revenue, sustained funding of independent oversight, binding relinquishment of control | Executive who cedes board control to an external safety body |
| 4 | Sustained, high-cost, high-impact action that changed policy or industry practice, at serious personal or financial risk | Insider whose disclosures led to binding regulation, at the cost of their career |

### Boundary cases

1. **Donation to safety research from wealth earned in the same sector:** counts, but cost-to-means decides the level, and the cap prevents laundering.
2. **Resignation followed by joining a competitor doing the same thing:** zero, unless the departure involved a documented principled objection.
3. **Public statements of concern with no action:** L1 maximum.

## Deterministic layer

### Structured facts extracted by researchers (not judged by the LLM)

- Power: office held, organization size, net worth band
- Agency: seniority, voluntariness, time in role. Score scales proportionally to agency, so rank and file rank lower than executives.
- Recency and duration of each act
- Evidence tier of each item
- For R5: cost as a share of means

### Aggregation principles (numbers to be tuned on calibration)

- Do not average axes. Use a max-like combination (for example a weighted probabilistic OR) so one catastrophic act is not diluted.
- Power and agency multiply the harm axes (R1-R4).
- R5 only reduces the score, up to a fixed cap. In-axis offsets count more than cross-axis offsets.
- Missing evidence means unknown. Report coverage. Return `unrated` if R1 and R2 both have no usable evidence.
- Confidence is computed from evidence tiers and counts, not from the judge's self-report.
- Final tiers: Ultimate, Major, Unwilling, Minor, Not a Dick. "Unwilling" means a high harm score with low agency and power.

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

## Open questions

- Pathway weights: should P1-P3 count equally against P4-P5?
- Size-band thresholds for "moderate" and "large" scale.
- How much should cross-axis R5 offsets count versus in-axis?
- Whether to publish per-rubric scores only, or also the final tier.
- Scope limit: public figures only?
- Legislator with a single vote: L2 or L3?
