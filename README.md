# Don't be a dick

## Who's a Dick?

By a short definition provided in p. 442 of Goliath's Curse, a Dick is someone who significantly contributes to global catastrophic risk. That is someone who works for an Agent of Doom:

- AGI lab
- Fossil fuel company
- Arms manufacturer

## Overview

This project is simple. Give a name, find out if they're a Dick, decide for yourself if you should support them in any way.

## How it works

API based first. For a given name the service runs a pipeline:

1. **Resolve** who the person is (public figures only, ambiguous names are disambiguated).
2. **Research**: one agent per rubric collects sourced evidence from the web, in parallel.
3. **Judge**: one LLM judge per rubric rates documented behavior from 0 to 4, citing evidence.
4. **Score**: a deterministic function combines the verdicts with the person's role and power into a tier.
5. **Summarize** the result, with every score and its evidence.

We judge behaviors and outcomes, never character. The rubrics are catastrophic-risk complicity (the Agents of Doom), domination, extraction and inequality, and corruption. Each rubric has a harm side and, where its anchors exist, a benefit side for costly acts that reduce the risk. Today that is catastrophic risk. See [docs/METHODOLOGY.md](docs/METHODOLOGY.md) for the workflow and scoring method, and [docs/RUBRIC.md](docs/RUBRIC.md) for the rubric anchors and parameters.

We'll calibrate with people like:

- Donald Trump -> Major Dick
- Elon Musk -> Kind of a Dick (maybe major Dick cos he seems to be an asshole?)
- Abelardo de la Espriella -> Fucking Dick
- Peter Singer -> Not a Dick
- Samuel Bankman Fried -> Corrupt Dick, etc.

## Dickness score

- Ultimate Dick: Wields immense power, supports the agents of doom (big tech, military industrial complex, and fossil fuel industry) through their investments or political power.
- Major Dick: Serious documented harm, in a decision-making role or with significant power.
- Unwilling Dick: Contributes from inside the machine with little agency (rank and file), and has no other serious findings.
- Minor Dick: Limited or small-scale documented harm.
- Not a Dick: Searched across the harm rubrics, and nothing was found.

Scores come from documented acts, weighted by the person's agency and power. Harm and benefit are two separate profiles, a Dick tier and a Guardian tier, and are never netted against each other: someone can be both. Details in [docs/METHODOLOGY.md](docs/METHODOLOGY.md).

## Running and polling

Scoring takes minutes, so the API answers in two steps. Results are stored in a local TinyDB file (`DBAD_DB_PATH`, default `data/results.json` in the project root, wherever the server is started from), keyed by the slug of the person's canonical name.

```sh
# 1. Resolve the name (a few seconds), start the research in the background
curl -i -X POST localhost:8000/score -H 'content-type: application/json' -d '{"name": "Lula"}'
# 202 {"id": "luiz-inacio-lula-da-silva", "status": "running"}, Location: /score/luiz-inacio-lula-da-silva

# 2. Poll until status is "done" (or "failed"); the report is in `report`
curl localhost:8000/score/luiz-inacio-lula-da-silva
```

- An ambiguous name (409, with candidates) or a name that is not a public figure (422) is answered immediately and nothing is stored.
- Posting a subject that is already `running` or `done` returns its id without a new run, so repeats cost nothing. Add `?refresh=true` to rerun a finished one. A `failed` run is rerun on the next post.
- A run always ends as `done` or `failed`. If the server is killed mid-run, the record is marked `failed` ("interrupted by restart") on the next startup.
- TinyDB is not safe across processes: run a single uvicorn worker.

## Tracing and evals (local Langfuse)

Tracing and offline evals run against a self-hosted Langfuse, on demand.

```bash
cd docker/langfuse && cp .env.example .env && docker compose up -d   # UI: http://localhost:3000
```

Put the `LANGFUSE_*` lines from the root `.env.example` in `.env` (they match the headless-init
keys in `docker/langfuse/.env.example`). Tracing is off unless `LANGFUSE_TRACING_ENABLED=true` and
both keys are set; tests always run with it off.

Golden cases live in `evals/golden/*.json`: frozen dossiers plus the expected tier and severities.
`status: baseline` means the expectations were copied from a model run; only `calibrated` cases
(reviewed by hand) say anything about correctness.

```bash
uv run python scripts/sync_golden.py --import-fixtures   # once: fixtures -> golden JSON
uv run python scripts/sync_golden.py                     # mirror golden JSON into Langfuse
uv run python scripts/run_eval.py --run-name baseline
uv run python scripts/run_eval.py --run-name glm --judge-model z-ai/glm-5.3-flash
uv run python scripts/run_eval.py --run-name v2 --prompt-root path/to/prompt_variant
```

`run_eval.py` re-judges the frozen dossiers with the chosen judge model and prompt variant and
scores tier match, score error and severity error. Compare runs under Datasets > `golden-judge`.
Evals spend OpenRouter credits and are not part of `pytest`.

## Example output

Real runs of `POST /score` on 2026-10-17, made when the endpoint still returned the report directly (it now returns an id to poll, as above). Only rubric R1 (catastrophic-risk complicity) is implemented so far, and the tier thresholds are an untuned first guess, so read these as a demo of the pipeline's output, not as verdicts. Everything below is generated by models from web sources found at the time of the run; the evidence links are the part to check.

```sh
curl -X POST localhost:8000/score -H 'content-type: application/json' \
  -d '{"name": "Peter Singer", "descriptor": "Australian moral philosopher"}'
```

### Elon Musk: `ultimate`

| | |
|---|---|
| R1 severity | 4 of 4 (dimension P1, AI loss of control), citing 7 evidence items |
| Harm / agency / power | 1.00 / 1.00 / 1.00 |
| Final score | 1.00 |
| Coverage / confidence | 1.00 / 1.00 (25 evidence items, many tier 1-2) |

A few of the 25 evidence items the report returned:

| ID | Dimension | Tier | Claim | Source |
|---|---|---|---|---|
| R1-E01 | P1 | 2 | xAI released Grok 4 in July 2025 without a system card (the industry-standard safety report). Researchers at Anthropic and OpenAI publicly criticised the omission as reckless. | [Fortune](https://fortune.com/2025/07/17/elon-musk-xai-grok-4-no-safety-report) |
| R1-E13 | P2 | 1 | In July 2025 the DoD awarded contracts of up to $200 million each to Anthropic, Google, OpenAI and xAI to accelerate adoption of advanced AI. | [CRS](https://www.congress.gov/crs-product/IN12669) |
| R1-E16 | P1 | 2 | SpaceX acquired xAI in Feb 2026, creating a combined $1.25T entity. | [CNBC](https://www.cnbc.com/2026/02/03/musk-xai-spacex-biggest-merger-ever.html) |
| R1-E18 | P1 | 2 | Musk publicly endorsed California's SB 1047 frontier-AI safety bill in Aug 2024. This cuts against a picture of opposing AI regulation. | [The Hill](https://thehill.com/policy/technology/4847956-california-bill-ai-safety) |

Summary (excerpt, as generated):

> Musk reaches the ultimate tier primarily through documented control over dual-use AI and defense infrastructure, combined with patterns of deprioritizing safety safeguards. [...] **Counterweight evidence:** Musk endorsed California's SB 1047 AI safety bill in August 2024 and publicly advocated for some AI regulation [R1-E18].

### Peter Singer (Australian moral philosopher): `not_a_dick`

| | |
|---|---|
| R1 severity | 0 of 4 (dimension P1), citing 1 evidence item |
| Harm / agency / power | 0.00 / 1.00 / 0.80 |
| Final score | 0.00 |
| Coverage / confidence | 1.00 / 0.10 (a single tier-3 source) |

| ID | Dimension | Tier | Claim | Source |
|---|---|---|---|---|
| R1-E01 | P1 | 3 | In a 2019 interview, Singer said AI existential risk was too uncertain to justify diverting funds from existing global-poverty charities. This is a public position on AI risk prioritisation, not an act of building or lobbying for AI. | [Oxford Political Review](https://oxfordpoliticalreview.com/2019/08/25/is-ai-safety-rather-speculative-long-termism) |

Summary (excerpt, as generated):

> The only documented behavior comes from a 2019 interview [...] This represents a stated view on cause prioritization, not concrete harmful conduct. [...] This result should be treated as provisional.

The score is zero because nothing the researcher found touches the R1 pathways, and the low confidence reflects how little evidence was cited, not a hedge by the model: confidence is computed in code from evidence tiers and counts.


## Website

A static site in [web/](web/) shows the stored results: search, filters, grouping, and Dicks, Guardians and Ambivalent leaderboards, in an arcade final-score style. See [web/README.md](web/README.md) for exporting data and deploying.
