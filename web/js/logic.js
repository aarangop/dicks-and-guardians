// Pure data logic: no DOM, no fetch. Everything here is unit-tested in tests/web/.

export const RUBRICS = [
  { id: "R1", name: "Catastrophic risk", short: "RISK" },
  { id: "R2", name: "Domination", short: "DOM" },
  { id: "R3", name: "Extraction", short: "EXT" },
  { id: "R4", name: "Corruption", short: "COR" },
];
export const HARM_IDS = RUBRICS.map((r) => r.id);

// Dimension tags per rubric, as in domain/rubrics.py. R1's are the catastrophic-risk pathways.
export const PATHWAYS = {
  P1: "AI loss of control",
  P2: "AI weaponization",
  P3: "AI misuse",
  P4: "Fossil fuel",
  P5: "Arms industry",
  D1: "Retaliation against critics",
  D2: "Subverting checks",
  D3: "Force or incitement",
  D4: "Dehumanizing rhetoric",
  X1: "Labor exploitation",
  X2: "Tax structuring",
  X3: "Externalized costs",
  X4: "Consumer exploitation",
  X5: "Lobbying for extractive rules",
  C1: "Fraud and false statements",
  C2: "Bribery and self-dealing",
  C3: "Obstruction",
  C4: "Conflicts and revolving door",
};

// Ordered worst to best, matching docs/RUBRIC.md.
export const TIERS = {
  ultimate: {
    label: "Ultimate Dick",
    grade: "F",
    order: 0,
    blurb: "Wields immense power and feeds the agents of doom.",
  },
  major: {
    label: "Major Dick",
    grade: "C",
    order: 1,
    blurb: "Serious documented harm, in a decision-making role or with real power.",
  },
  unwilling: {
    label: "Unwilling Dick",
    grade: "B",
    order: 2,
    blurb: "Contributes from inside the machine with little agency.",
  },
  minor: {
    label: "Minor Dick",
    grade: "A",
    order: 3,
    blurb: "Limited or small-scale documented harm.",
  },
  not_a_dick: {
    label: "Not a Dick",
    grade: "S",
    order: 4,
    blurb: "Searched across the harm rubrics, and nothing was found.",
  },
  unrated: {
    label: "Unrated",
    grade: "?",
    order: 5,
    blurb: "Not enough evidence to rate.",
  },
};

// The benefit profile has its own ladder. It is never netted against harm (docs/RUBRIC.md).
export const GUARDIAN_TIERS = {
  ultimate_guardian: { label: "Ultimate Guardian", order: 0, blurb: "Sustained, high-cost action that changed policy or practice." },
  major_guardian: { label: "Major Guardian", order: 1, blurb: "Major costly action with measurable impact." },
  minor_guardian: { label: "Minor Guardian", order: 2, blurb: "Some costly or protective action is documented." },
  none_documented: { label: "None documented", order: 3, blurb: "No benefit found. This is never a negative." },
  unrated: { label: "Unrated", order: 4, blurb: "The benefit side could not be rated." },
};

export function guardianInfo(tier) {
  return GUARDIAN_TIERS[tier] ?? GUARDIAN_TIERS.unrated;
}

/** True when the benefit profile has something to show. */
export const isGuardian = (p) => ["ultimate_guardian", "major_guardian", "minor_guardian"].includes(p.benefit_tier);

export const PROVISIONAL_BELOW = 0.5; // confidence under this marks a result as provisional

export function tierInfo(tier) {
  return TIERS[tier] ?? TIERS.unrated;
}

/** Lowercase and strip accents so "Álvaro" matches "alvaro". */
export function normalize(text) {
  return String(text ?? "")
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase();
}

/** Add derived fields once at load time. */
export function enrich(raw) {
  const severities = Object.fromEntries((raw.rubrics ?? []).map((r) => [r.id, r.severity]));
  let driver = "none";
  let best = 0;
  for (const id of HARM_IDS) {
    const sev = severities[id] ?? 0;
    if (sev > best) {
      best = sev;
      driver = id;
    }
  }
  const benefitSeverities = Object.fromEntries(
    (raw.benefit_rubrics ?? []).map((r) => [r.id, r.severity]),
  );
  const countedIds = new Set(
    [...(raw.rubrics ?? []), ...(raw.benefit_rubrics ?? [])].flatMap((r) => r.evidence_ids ?? []),
  );
  return {
    ...raw,
    severities,
    benefitSeverities,
    driver,
    countedIds,
    points: raw.score == null ? null : Math.round(raw.score * 1_000_000),
    benefitPoints: raw.benefit == null ? null : Math.round(raw.benefit * 1_000_000),
    benefitProvisional: (raw.benefit_confidence ?? 0) < PROVISIONAL_BELOW,
    provisional: raw.confidence < PROVISIONAL_BELOW,
    _who: normalize(`${raw.name} ${raw.descriptor ?? ""} ${raw.requested_name ?? ""}`),
    _evidence: normalize((raw.evidence ?? []).map((e) => e.claim).join(" ")),
  };
}

// --- search & filter --------------------------------------------------------

export function matchesQuery(person, query, inEvidence = false) {
  const tokens = normalize(query).split(/\s+/).filter(Boolean);
  return tokens.every(
    (t) => person._who.includes(t) || (inEvidence && person._evidence.includes(t)),
  );
}

/**
 * filters: { q, inEvidence, tiers: Set<string> (empty = all), driver: "all"|id|"none",
 *            minConfidence: number }
 */
export function applyFilters(people, f) {
  return people.filter((p) => {
    if (f.q && !matchesQuery(p, f.q, f.inEvidence)) return false;
    if (f.tiers?.size && !f.tiers.has(p.tier)) return false;
    if (f.driver && f.driver !== "all" && p.driver !== f.driver) return false;
    if (f.minConfidence && p.confidence < f.minConfidence) return false;
    return true;
  });
}

// --- sorting ----------------------------------------------------------------

const byName = (a, b) => a.name.localeCompare(b.name);
// Unrated people have no score; they always sink to the bottom whatever the direction.
const scoreOrMinus = (p) => p.score ?? -1;

export const SORTS = {
  score: { label: "Highest score", cmp: (a, b) => scoreOrMinus(b) - scoreOrMinus(a) || byName(a, b) },
  score_asc: { label: "Lowest score", cmp: (a, b) => (a.score ?? 2) - (b.score ?? 2) || byName(a, b) },
  name: { label: "Name A-Z", cmp: byName },
  confidence: { label: "Most confident", cmp: (a, b) => b.confidence - a.confidence || byName(a, b) },
  power: { label: "Most power", cmp: (a, b) => b.power - a.power || byName(a, b) },
  newest: { label: "Newest", cmp: (a, b) => b.rated_at.localeCompare(a.rated_at) || byName(a, b) },
};

export function sortPeople(people, key) {
  return [...people].sort((SORTS[key] ?? SORTS.score).cmp);
}

// --- grouping ---------------------------------------------------------------

export function powerBand(power) {
  if (power >= 0.75) return "systemic";
  if (power >= 0.5) return "high";
  if (power >= 0.25) return "some";
  return "minimal";
}

export function confidenceBand(confidence) {
  if (confidence >= 0.8) return "high";
  if (confidence >= PROVISIONAL_BELOW) return "medium";
  return "low";
}

/** Each grouping returns a [sortOrder, label] pair for a person. */
export const GROUPINGS = {
  none: { label: "No grouping", of: () => [0, ""] },
  tier: { label: "Tier", of: (p) => [tierInfo(p.tier).order, tierInfo(p.tier).label] },
  driver: {
    label: "Biggest harm",
    of: (p) => {
      const idx = HARM_IDS.indexOf(p.driver);
      return idx < 0 ? [9, "No harm found"] : [idx, RUBRICS[idx].name];
    },
  },
  power: {
    label: "Power",
    of: (p) => {
      const band = powerBand(p.power);
      const order = ["systemic", "high", "some", "minimal"].indexOf(band);
      return [order, `${band[0].toUpperCase()}${band.slice(1)} power`];
    },
  },
  confidence: {
    label: "Confidence",
    of: (p) => {
      const band = confidenceBand(p.confidence);
      const order = ["high", "medium", "low"].indexOf(band);
      return [order, `${band[0].toUpperCase()}${band.slice(1)} confidence`];
    },
  },
  month: {
    label: "Month rated",
    of: (p) => [-Number(p.rated_at.slice(0, 7).replace("-", "")), p.rated_at.slice(0, 7)],
  },
};

/** Split an already-sorted list into labelled groups, keeping the order inside each group. */
export function groupPeople(people, key) {
  const grouping = GROUPINGS[key] ?? GROUPINGS.none;
  if (key === "none" || !GROUPINGS[key]) return [{ label: "", people }];
  const groups = new Map();
  for (const p of people) {
    const [order, label] = grouping.of(p);
    if (!groups.has(label)) groups.set(label, { order, label, people: [] });
    groups.get(label).people.push(p);
  }
  return [...groups.values()].sort((a, b) => a.order - b.order || a.label.localeCompare(b.label));
}

// --- rankings ---------------------------------------------------------------

const rated = (p) => p.score != null && p.tier !== "unrated";
const isDick = (p) => rated(p) && p.tier !== "not_a_dick";

/** Harm only, worst first. Evidence of harm is provable, so low confidence does not demote anyone. */
export function rankDicks(people) {
  return people
    .filter(isDick)
    .sort((a, b) => b.score - a.score || b.confidence - a.confidence || byName(a, b));
}

/**
 * Benefit only, best first. Harm is never looked at: a Guardian is anyone with documented benefit,
 * ranked by their benefit score. Like harm, a documented act does not lose rank for low confidence.
 */
export function rankGuardians(people) {
  return people
    .filter((p) => isGuardian(p) && p.benefit != null)
    .sort(
      (a, b) =>
        b.benefit - a.benefit || (b.benefit_confidence ?? 0) - (a.benefit_confidence ?? 0) || byName(a, b),
    );
}

/** How torn a person is: the weaker of their two profiles, so only high on both ranks high. */
export const ambivalence = (p) => Math.min(p.score ?? 0, p.benefit ?? 0);

/** People with both a harm tier and a Guardian tier, most conflicted first. */
export function rankAmbivalent(people) {
  return people
    .filter((p) => isDick(p) && isGuardian(p) && p.benefit != null)
    .sort(
      (a, b) =>
        ambivalence(b) - ambivalence(a) ||
        b.score + b.benefit - (a.score + a.benefit) ||
        byName(a, b),
    );
}

// --- URL state --------------------------------------------------------------

export const DEFAULT_STATE = {
  q: "",
  inEvidence: false,
  tiers: new Set(),
  driver: "all",
  minConfidence: 0,
  sort: "score",
  by: "none",
};

export function stateToParams(state) {
  const params = new URLSearchParams();
  if (state.q) params.set("q", state.q);
  if (state.inEvidence) params.set("ev", "1");
  if (state.tiers.size) params.set("tier", [...state.tiers].join(","));
  if (state.driver !== "all") params.set("driver", state.driver);
  if (state.minConfidence) params.set("conf", String(state.minConfidence));
  if (state.sort !== "score") params.set("sort", state.sort);
  if (state.by !== "none") params.set("by", state.by);
  return params;
}

export function paramsToState(params) {
  const sort = params.get("sort");
  const by = params.get("by");
  const conf = Number(params.get("conf"));
  return {
    q: params.get("q") ?? "",
    inEvidence: params.get("ev") === "1",
    tiers: new Set((params.get("tier") ?? "").split(",").filter((t) => t in TIERS)),
    driver: params.get("driver") ?? "all",
    minConfidence: Number.isFinite(conf) ? Math.min(Math.max(conf, 0), 1) : 0,
    sort: sort in SORTS ? sort : "score",
    by: by in GROUPINGS ? by : "none",
  };
}
