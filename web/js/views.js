// Views: pure functions from data to HTML strings. main.js owns state, routing and events.

import {
  GROUPINGS,
  HARM_IDS,
  PATHWAYS,
  RUBRICS,
  SORTS,
  GUARDIAN_TIERS,
  TIERS,
  confidenceBand,
  guardianInfo,
  isGuardian,
  powerBand,
  tierInfo,
} from "./logic.js";
import { domain, esc, formatDate, ordinal, pct, points, renderSummary, safeUrl } from "./format.js";
import { face, sprite } from "./sprites.js";

const rubricName = (id) => RUBRICS.find((r) => r.id === id)?.name ?? id;

// --- small building blocks --------------------------------------------------

export const badge = (tier) =>
  `<span class="badge t-${esc(tier)}">${esc(tierInfo(tier).label)}</span>`;

export const guardianBadge = (tier) =>
  `<span class="badge g-${esc(tier)}">${esc(guardianInfo(tier).label)}</span>`;

/** Four squares, filled up to the severity (0-4). */
const pips = (severity, tier) =>
  `<span class="pips" title="severity ${severity ?? "?"} of 4">${[1, 2, 3, 4]
    .map((n) => `<i class="${n <= (severity ?? 0) ? `on t-${esc(tier)}` : ""}"></i>`)
    .join("")}</span>`;

/** Ten-segment arcade meter for a 0-1 value. */
const meter = (value, cls = "") =>
  `<span class="meter ${cls}" role="img" aria-label="${pct(value)}"><b style="width:${pct(value)}"></b></span>`;

/** `mood` is the tier whose expression to draw, `tone` the color class. Both default to harm. */
const avatar = (p, px = 6, mood = p.tier, tone = `t-${esc(p.tier)}`) =>
  `<span class="avatar ${tone}">${face(p.id, mood, px)}</span>`;

const link = (p) => `#/p/${encodeURIComponent(p.id)}`;

// --- roster -----------------------------------------------------------------

export function rosterControls(state) {
  const tierChips = Object.entries(TIERS)
    .filter(([id]) => id !== "unrated")
    .map(
      ([id, t]) =>
        `<button type="button" class="chip t-${id}${state.tiers.has(id) ? " on" : ""}" data-tier="${id}" aria-pressed="${state.tiers.has(id)}">${esc(t.label)}</button>`,
    )
    .join("");
  const options = (obj, current, extra = "") =>
    extra +
    Object.entries(obj)
      .map(([k, v]) => `<option value="${esc(k)}"${k === current ? " selected" : ""}>${esc(v.label)}</option>`)
      .join("");
  const drivers =
    `<option value="all"${state.driver === "all" ? " selected" : ""}>Any harm</option>` +
    HARM_IDS.map(
      (id) => `<option value="${id}"${state.driver === id ? " selected" : ""}>${esc(rubricName(id))}</option>`,
    ).join("") +
    `<option value="none"${state.driver === "none" ? " selected" : ""}>No harm found</option>`;

  return `
  <section class="panel px controls" aria-label="Search and filters">
    <label class="field grow">
      <span class="lbl">Player search</span>
      <input id="q" type="search" placeholder="Type a name, role or country..." value="${esc(state.q)}" autocomplete="off" spellcheck="false">
    </label>
    <div class="field">
      <span class="lbl">Tier</span>
      <div class="chips">${tierChips}</div>
    </div>
    <label class="field"><span class="lbl">Biggest harm</span><select id="driver">${drivers}</select></label>
    <label class="field"><span class="lbl">Group by</span><select id="by">${options(GROUPINGS, state.by)}</select></label>
    <label class="field"><span class="lbl">Sort</span><select id="sort">${options(SORTS, state.sort)}</select></label>
    <label class="field">
      <span class="lbl">Min confidence <output id="conf-out">${pct(state.minConfidence)}</output></span>
      <input id="conf" type="range" min="0" max="1" step="0.1" value="${state.minConfidence}">
    </label>
    <label class="check"><input id="ev" type="checkbox"${state.inEvidence ? " checked" : ""}> Also search evidence text</label>
    <button type="button" class="btn ghost" id="reset">Reset</button>
  </section>`;
}

function card(p) {
  const sevs = RUBRICS.map(
    (r) =>
      `<span class="sev" title="${esc(r.name)}"><em>${r.short}</em>${pips(p.severities[r.id], p.tier)}</span>`,
  ).join("");
  return `
  <a class="card px t-${esc(p.tier)}" href="${link(p)}">
    <div class="card-top">
      ${avatar(p)}
      <div class="who">
        <h3>${esc(p.name)}</h3>
        <p class="desc">${esc(p.descriptor ?? "")}</p>
      </div>
    </div>
    <div class="card-mid">
      ${badge(p.tier)}
      <span class="pts" title="Dick points">${points(p.points)}</span>
    </div>
    <div class="sevs">${sevs}</div>
    <div class="card-bot"><span>CONF ${meter(p.confidence, "mini")}</span>${isGuardian(p) ? guardianBadge(p.benefit_tier) : ""}${p.provisional ? '<span class="tag warn">PROVISIONAL</span>' : ""}</div>
  </a>`;
}

export function rosterResults(groups, total, shown) {
  if (!shown) {
    return `<div class="empty px"><p class="big">NO PLAYERS FOUND</p><p>Nothing matches those filters. Try loosening them or hit Reset.</p></div>`;
  }
  const body = groups
    .map(
      (g) => `
    <section class="group">
      ${g.label ? `<h2 class="group-h">${esc(g.label)} <span class="count">${g.people.length}</span></h2>` : ""}
      <div class="grid">${g.people.map(card).join("")}</div>
    </section>`,
    )
    .join("");
  return `<p class="meta-line">${shown} of ${total} players</p>${body}`;
}

// --- leaderboards -----------------------------------------------------------

// Each board reads one profile (or both, for ambivalence). `tone` colors the row, `face` is the
// tier whose mood the avatar wears, `figure` is what the board is ranked by.
const BOARDS = {
  dicks: {
    title: "DICKS",
    glow: "glow-pink",
    icon: () => sprite("skull", "#fff7e0", 5),
    podiumIcon: () => sprite("skull", "#fff7e0", 6, "bob"),
    sub: "High score loses. The most documented harm, weighted by power and agency. Benefit is not counted here.",
    empty: ["NO DICKS YET", "Nobody with documented harm has been scored yet."],
    tone: (p) => `t-${esc(p.tier)}`,
    face: (p) => p.tier,
    badges: (p) => badge(p.tier),
    figure: (p) => `<span class="pts" title="Dick points">${points(p.points)}</span>`,
    prov: (p) => p.provisional,
  },
  guardians: {
    title: "GUARDIANS",
    glow: "glow-cyan",
    icon: () => sprite("crown", "#ffd23f", 5),
    podiumIcon: () => sprite("crown", "#ffd23f", 6, "bob"),
    sub: "High score wins. The most documented costly action against catastrophic risk, weighted by agency and power. Harm is not counted here.",
    empty: ["NO GUARDIANS YET", "Nobody with documented benefit has been scored yet."],
    tone: (p) => `g-${esc(p.benefit_tier)}`,
    face: () => "not_a_dick",
    badges: (p) => guardianBadge(p.benefit_tier),
    figure: (p) => `<span class="pts guardian" title="Guardian points">${points(p.benefitPoints)}</span>`,
    prov: (p) => p.benefitProvisional,
  },
  ambivalent: {
    title: "AMBIVALENT",
    glow: "glow-yellow",
    icon: () => `${sprite("skull", "#fff7e0", 4)} ${sprite("crown", "#ffd23f", 4)}`,
    podiumIcon: () => `${sprite("skull", "#fff7e0", 5, "bob")} ${sprite("crown", "#ffd23f", 5, "bob")}`,
    sub: "Both profiles run high at once. Ranked by the weaker of the two, so only people high on harm and on benefit rank high. The two are shown side by side and never netted.",
    empty: ["NO AMBIVALENT PLAYERS", "Nobody has both a harm tier and a Guardian tier yet."],
    tone: (p) => `t-${esc(p.tier)}`,
    face: () => "minor",
    badges: (p) => `${badge(p.tier)} ${guardianBadge(p.benefit_tier)}`,
    figure: (p) =>
      `<span class="pts" title="Dick points">${points(p.points)}</span> <span class="pts guardian" title="Guardian points">${points(p.benefitPoints)}</span>`,
    prov: (p) => p.provisional || p.benefitProvisional,
  },
};

export const BOARD_KINDS = Object.keys(BOARDS);

function podiumSlot(p, index, cfg) {
  const place = index + 1;
  const icon = place === 1 ? cfg.podiumIcon() : sprite("star", place === 2 ? "#c9d4ff" : "#ff9a2e", 5);
  return `
  <a class="slot px place-${place} ${cfg.tone(p)}" href="${link(p)}">
    <span class="place">${ordinal(place)}</span>
    <span class="icon">${icon}</span>
    ${avatar(p, 7, cfg.face(p), cfg.tone(p))}
    <h3>${esc(p.name)}</h3>
    ${cfg.badges(p)}
    <span class="big">${cfg.figure(p)}</span>
    ${cfg.prov(p) ? '<span class="tag warn">PROVISIONAL</span>' : ""}
  </a>`;
}

function boardRow(p, index, cfg) {
  const rank = String(index + 1).padStart(2, "0");
  return `
  <a class="row ${cfg.tone(p)}" href="${link(p)}">
    <span class="rank">${rank}</span>
    ${avatar(p, 3, cfg.face(p), cfg.tone(p))}
    <span class="nm">${esc(p.name)}${cfg.prov(p) ? ' <span class="tag warn">PROV</span>' : ""}</span>
    <span class="leader" aria-hidden="true"></span>
    ${cfg.figure(p)}
    <span class="bd">${cfg.badges(p)}</span>
  </a>`;
}

export function leaderboard(kind, ranked) {
  const cfg = BOARDS[kind];
  const head = `
    <header class="board-head">
      <h1 class="${cfg.glow}">${cfg.icon()} ${cfg.title} ${cfg.icon()}</h1>
      <p>${cfg.sub}</p>
      ${kind === "guardians" ? disclaimer(true) : ""}
    </header>`;
  const tail = kind === "guardians" ? "" : disclaimer(true);
  if (!ranked.length) {
    return `${head}<div class="empty px"><p class="big">${cfg.empty[0]}</p><p>${cfg.empty[1]}</p></div>${tail}`;
  }
  const top = ranked.slice(0, 3).map((p, i) => podiumSlot(p, i, cfg)).join("");
  const rest = ranked.slice(3).map((p, i) => boardRow(p, i + 3, cfg)).join("");
  return `${head}
    <div class="podium">${top}</div>
    ${rest ? `<div class="board px">${rest}</div>` : ""}
    ${tail}`;
}

// --- detail: the final score screen ----------------------------------------

function evidenceItem(e, counted) {
  const dim = PATHWAYS[e.dimension] ? `${e.dimension} ${PATHWAYS[e.dimension]}` : e.dimension;
  const kind = String(e.source_kind ?? "").replaceAll("_", " ");
  return `
  <article class="ev px-s${counted ? " counted" : ""}" id="ev-${esc(e.id)}" data-rubric="${esc(e.id.split("-")[0])}" data-tier="${e.source_tier}">
    <header>
      <span class="tag id">${esc(e.id)}</span>
      <span class="tag">${esc(dim)}</span>
      <span class="tag tier-${e.source_tier}">SOURCE TIER ${e.source_tier}</span>
      ${e.polarity === "benefit" ? '<span class="tag benefit">BENEFIT</span>' : ""}
      ${counted ? '<span class="tag star">COUNTED</span>' : ""}
      <time>${esc(formatDate(e.event_date))}</time>
    </header>
    <p class="claim">${esc(e.claim)}</p>
    ${e.quote ? `<blockquote>${esc(e.quote)}</blockquote>` : ""}
    <footer><a href="${esc(safeUrl(e.source_url))}" target="_blank" rel="noopener noreferrer">${esc(e.source_title || domain(e.source_url))}</a> <span class="dom">${esc(domain(e.source_url))} · ${esc(kind)}</span></footer>
  </article>`;
}

export function evidenceList(p, filter) {
  const items = p.evidence.filter(
    (e) =>
      (filter.rubric === "all" || e.id.startsWith(`${filter.rubric}-`)) &&
      (filter.tier === "all" || String(e.source_tier) === filter.tier) &&
      (!filter.counted || p.countedIds.has(e.id)),
  );
  const list = items.map((e) => evidenceItem(e, p.countedIds.has(e.id))).join("");
  return `<p class="meta-line">${items.length} of ${p.evidence.length} evidence items</p>${list || '<div class="empty px-s"><p>No evidence matches.</p></div>'}`;
}

export function evidenceFilters(p, filter) {
  const present = new Set(p.evidence.map((e) => e.id.split("-")[0]));
  const rub = ["all", ...RUBRICS.map((r) => r.id).filter((id) => present.has(id))]
    .map(
      (id) =>
        `<button type="button" class="chip${filter.rubric === id ? " on" : ""}" data-f-rubric="${id}">${id === "all" ? "All rubrics" : `${id} ${esc(rubricName(id))}`}</button>`,
    )
    .join("");
  const tiers = ["all", "1", "2", "3"]
    .map(
      (t) =>
        `<button type="button" class="chip${filter.tier === t ? " on" : ""}" data-f-tier="${t}">${t === "all" ? "Any source" : `Tier ${t}`}</button>`,
    )
    .join("");
  return `<div class="chips">${rub}</div><div class="chips">${tiers}<button type="button" class="chip${filter.counted ? " on" : ""}" data-f-counted="1">★ Counted only</button></div>`;
}

function statRow(label, value, extra = "") {
  return `<div class="stat"><span class="k">${label}</span>${meter(value)}<span class="v">${pct(value)}</span>${extra}</div>`;
}

/** One half of the score screen. Harm and benefit use the same layout so neither leads. */
function side({ cls, title, icon, badgeHtml, blurb, label, value, count, provisional, stats, rows, empty }) {
  return `
      <section class="side px ${cls}" aria-label="${esc(title)}">
        <h2>${icon} ${esc(title)}</h2>
        <div class="side-tier">${badgeHtml}${provisional ? ' <span class="tag warn">PROVISIONAL</span>' : ""}</div>
        <p class="blurb">${esc(blurb)}</p>
        <div class="scorebox">
          <span class="lbl">${esc(label)}</span>
          <span class="pts huge ${cls.startsWith("g-") ? "guardian" : ""}" data-count="${count ?? ""}">${points(value)}</span>
        </div>
        ${empty ? `<p class="fine">${esc(empty)}</p>` : `<div class="stats">${stats}</div>`}
        <h3 class="sub">Rubrics</h3>
        <div class="rubrics">${rows || '<p class="fine">None scored.</p>'}</div>
      </section>`;
}

export function detail(p, filter) {
  const t = tierInfo(p.tier);
  const g = guardianInfo(p.benefit_tier);
  const rubricRow = (r, s, tier) => {
    const sev = s?.severity;
    const dim = s?.top_dimension;
    return `
    <div class="rrow">
      <span class="rid">${esc(r.id)}</span>
      <span class="rname">${esc(r.name)}</span>
      ${pips(sev, tier)}
      <span class="rval">${sev == null ? "N/A" : `${sev}/4`}</span>
      <span class="rdim">${dim ? esc(PATHWAYS[dim] ?? dim) : ""}</span>
    </div>`;
  };
  const harmRows = RUBRICS.map((r) => rubricRow(r, p.rubrics.find((x) => x.id === r.id), p.tier)).join("");
  const benefitRows = (p.benefit_rubrics ?? [])
    .map((s) => rubricRow(RUBRICS.find((x) => x.id === s.id) ?? { id: s.id, name: s.id }, s, "benefit"))
    .join("");
  const benefitRated = p.benefit_tier !== "unrated";

  const dickSide = side({
    cls: `t-${esc(p.tier)}`,
    title: "Dick side",
    icon: sprite("skull", "#fff7e0", 3),
    badgeHtml: badge(p.tier),
    blurb: t.blurb,
    label: "Dick points",
    value: p.points,
    count: p.points,
    provisional: p.provisional,
    stats: `${statRow("HARM", p.harm ?? 0)}${statRow("CONFIDENCE", p.confidence)}${statRow("COVERAGE", p.coverage)}`,
    rows: harmRows,
  });
  const guardianSide = side({
    cls: `g-${esc(p.benefit_tier)}`,
    title: "Guardian side",
    icon: sprite("crown", "#ffd23f", 3),
    badgeHtml: guardianBadge(p.benefit_tier),
    blurb: g.blurb,
    label: "Guardian points",
    value: p.benefitPoints,
    count: p.benefitPoints,
    provisional: benefitRated && p.benefitProvisional,
    stats: `${statRow("BENEFIT", p.benefit ?? 0)}${statRow("CONFIDENCE", p.benefit_confidence ?? 0)}`,
    rows: benefitRows,
    empty: benefitRated ? "" : "The benefit side could not be rated.",
  });

  return `
  <a class="back" href="#/">◄ Back to roster</a>
  <section class="score-screen px">
    <p class="stage">FINAL SCORE</p>
    <div class="ss-head">
      ${avatar(p, 10, "unrated", "")}
      <div>
        <h1>${esc(p.name)}</h1>
        <p class="desc">${esc(p.descriptor ?? "")}</p>
        <div class="both">${badge(p.tier)} ${guardianBadge(p.benefit_tier)}</div>
      </div>
    </div>

    <div class="sides">${dickSide}${guardianSide}</div>

    <div class="weights">
      <h2>Weight</h2>
      <div class="stats">
        ${statRow("POWER", p.power)}
        ${statRow("AGENCY", p.agency)}
        ${statRow("INFLUENCE", p.influence)}
      </div>
      <p class="fine">Dick points = harm × influence. Power band: ${powerBand(p.power)}. Confidence: ${confidenceBand(p.confidence)}. Guardian points are scored apart from harm and never netted against it.</p>
      ${p.notes?.length ? `<ul class="notes">${p.notes.map((n) => `<li>${esc(n)}</li>`).join("")}</ul>` : ""}
    </div>
  </section>

  <section class="panel px summary">
    <h2>Summary</h2>
    <div class="prose">${renderSummary(p.summary)}</div>
    <p class="fine">Generated by language models from web sources found at the time of the run (${esc(formatDate(p.rated_at))}). The evidence below is the part to check.</p>
  </section>

  ${disclaimer(true)}

  <section class="evidence">
    <h2>Evidence</h2>
    <div id="ev-filters" class="filters">${evidenceFilters(p, filter)}</div>
    <div id="ev-list">${evidenceList(p, filter)}</div>
  </section>`;
}

// --- about ------------------------------------------------------------------

/** The one idea that must never be missed: what this site measures, and what it does not. */
export function disclaimer(compact = false) {
  const link = compact ? ' <a href="#/about">Read the full bar.</a>' : "";
  return `
  <aside class="bar px" role="note">
    <p class="bar-h">⚠ THE BAR: CATASTROPHIC RISK</p>
    <p>This site measures one thing: contribution to <strong>global catastrophic risk</strong> (AI, fossil fuels, arms) and the abuse of power around it.
    <strong>A clean score or a Guardian tier here doesn't necessarily mean this person isn't a dick in other ways.</strong> Someone might be an absolute dick and still not contribute to catastrophic risks, which is what this website focuses on.${link}</p>
  </aside>`;
}

const RUBRIC_DOCS = [
  {
    id: "R1",
    name: "Catastrophic-risk complicity",
    core: true,
    what: "Operating, building, financing, lobbying for, or legislating in favor of activities in five pathways: AI loss of control (P1), AI weaponization and repression (P2), AI misuse and proliferation (P3), fossil fuel (P4), and the arms industry (P5). Judged by documented disregard for danger: dissolving safety teams, overriding safety warnings, lobbying against safeguards, climate disinformation, selling to actors with atrocity records.",
    not: "Passive holdings such as index funds or pension management. Rank and file are in scope but score low through the agency modifier.",
    anchors: [
      "No documented link, or out of scope.",
      "Participates (employment, contracting, small funding) with no documented disregard for risk.",
      "Participates with at least one disregard indicator, or directly builds or sells the harmful capability at moderate scale.",
      "Shapes direction: sets strategy, allocates major capital, or lobbies or legislates to expand the activity or weaken safeguards, with documented disregard.",
      "Founds or leads an agent of doom, or uses state or corporate power to expand it at scale while overriding safety warnings.",
    ],
  },
  {
    id: "R2",
    name: "Domination",
    what: "Using coercion, intimidation or institutional power to suppress opponents, or subverting the checks on power (elections, courts, press, independent institutions). Counted as acts, not opinions.",
    not: "Policy positions, party membership and ideology. Contested policy is not domination; subverting the process that checks policy is.",
    anchors: [
      "No documented coercive or check-subverting conduct.",
      "Retaliation or coercion in a limited setting, such as a workplace.",
      "Repeated coercion of critics, press or opponents with institutional or economic leverage, or advocacy for subverting democratic checks without the power to act.",
      "Uses office to subvert a check: overturning an election, defying courts, purging independent officials, incitement linked to violence.",
      "Sustained dismantling of checks, or violence against civilians or opponents at scale.",
    ],
  },
  {
    id: "R3",
    name: "Extraction and inequality",
    what: "Concentrating wealth by shifting costs onto workers, customers, the public or the environment, or by shaping rules to entrench that. Wage theft, union-busting rulings, large-scale profit shifting, pollution findings, predatory terms, resourced lobbying for extractive rules.",
    not: "Being rich, personal consumption or lifestyle. Wealth is a power modifier, not a behavior.",
    anchors: [
      "No documented extractive practices.",
      "Isolated small-scale violations (fines, settlements).",
      "Repeated violations, a business model that depends on shifting costs, or documented large-scale legal avoidance.",
      "Designs or leads large-scale extraction, or lobbies with resources to entrench it.",
      "Societal-scale extraction through state or market capture, or forced labor and dispossession at scale.",
    ],
  },
  {
    id: "R4",
    name: "Corruption and integrity",
    what: "Proven fraud, bribery, self-dealing, undisclosed conflicts, obstruction, or deceiving regulators and the public on material facts. Only adjudicated findings and primary documents count.",
    not: "Allegations, investigations and rumors. They are recorded as unproven and never score. Lying as a character judgment does not count.",
    anchors: [
      "Nothing proven (allegations may exist).",
      "Minor proven breaches: ethics fines, small undisclosed conflicts.",
      "Proven deception or conflicts at moderate stakes: civil misrepresentation findings, securities settlements.",
      "Conviction or civil liability for fraud, bribery or obstruction, or documented systematic self-dealing.",
      "Large-scale fraud or corruption with major victims, or leading an organization-wide scheme, with conviction.",
    ],
  },
];

const BENEFIT_DOC = {
  id: "R1",
  name: "Benefit side (Guardian)",
  benefit: true,
  what: "Costly, verified actions that reduce catastrophic risk: principled resignations, refusing contracts, whistleblowing at personal risk, divestment, funding independent oversight. Cost is judged relative to the person's means, and agency and power scale each act. Today only R1 has a benefit side; R2 to R4 have none yet.",
  not: "Pledges (only executed actions count), cheap gestures, an organization vouching for itself, and philanthropy that buys influence against safety. Speech alone caps at level 1. Benefit never reduces harm, and harm never reduces benefit: someone can be a Major Dick and a Major Guardian at once.",
  anchors: [
    "None documented. This is the normal case and never a negative.",
    "Low-cost positive actions: modest donations, public support for safety or democratic checks.",
    "Meaningful costly action: resigning on principle, refusing a contract, internal whistleblowing, divestment at a cost.",
    "Major costly action with measurable impact: public whistleblowing at personal risk, refusing major revenue, sustained funding of independent oversight.",
    "Sustained, high-cost, high-impact action that changed policy or industry practice, at serious personal or financial risk.",
  ],
};

function rubricDoc(r) {
  const rows = r.anchors
    .map((a, i) => `<tr><th scope="row">${i}</th><td>${esc(a)}</td></tr>`)
    .join("");
  return `
  <details class="rdoc px-s${r.core ? " core" : ""}"${r.core ? " open" : ""}>
    <summary><span class="rid">${r.id}</span> ${esc(r.name)}${r.core ? ' <span class="tag star">THE CORE BAR</span>' : ""}${r.benefit ? ' <span class="tag benefit">BENEFIT</span>' : ""}</summary>
    <div class="prose">
      <p><strong>What it measures.</strong> ${esc(r.what)}</p>
      <p><strong>What it ignores.</strong> ${esc(r.not)}</p>
      <table class="anchors"><caption>${r.benefit ? "Benefit" : "Severity"} anchors, 0 to 4</caption><tbody>${rows}</tbody></table>
    </div>
  </details>`;
}

export function about() {
  const tiers = Object.entries(TIERS)
    .filter(([id]) => id !== "unrated")
    .map(
      ([id, t]) =>
        `<div class="legend t-${id}"><span class="grade sm">${t.grade}</span>${badge(id)}<p>${esc(t.blurb)}</p></div>`,
    )
    .join("");
  const guardians = Object.entries(GUARDIAN_TIERS)
    .filter(([id]) => id !== "unrated")
    .map(
      ([id, t]) =>
        `<div class="legend g-${id}">${guardianBadge(id)}<p>${esc(t.blurb)}</p></div>`,
    )
    .join("");
  return `
  <header class="board-head"><h1 class="glow-cyan">HOW TO PLAY</h1></header>

  <aside class="bar big px" role="note">
    <p class="bar-h">⚠ READ THIS FIRST: THE BAR IS CATASTROPHIC RISK</p>
    <p>A <strong>Dick</strong>, by the short definition on p. 442 of <em>Goliath's Curse</em>, is someone who significantly contributes to global catastrophic risk: someone who works for, funds, or politically feeds an <strong>agent of doom</strong> (an AGI lab, a fossil fuel company, an arms manufacturer).</p>
    <p><strong>That is the only bar this website measures against.</strong> So:</p>
    <ul>
      <li><strong>A clean score or a Guardian tier here doesn't necessarily mean this person isn't a dick in other ways.</strong> Someone might be an absolute dick, in their private life or in public conduct, and still not contribute to catastrophic risks, which is what this website focuses on.</li>
      <li>A low score means <em>"little documented contribution to catastrophic risk, or to the abuse of power around it, that this method could find and source"</em>. It does not mean "good person", "innocent" or "endorsed".</li>
      <li>A high score means documented, sourced contribution, weighted by power. It is not a verdict on someone's whole character, and we judge behaviors and outcomes, never character.</li>
    </ul>
  </aside>

  <h2 class="group-h">What this site does not measure</h2>
  <section class="panel px prose">
    <ul>
      <li>Private behavior, personality, manners or lifestyle.</li>
      <li>Serious wrongs that sit outside the rubrics below, however real or terrible they are. If an act is not catastrophic risk, domination, extraction or corruption as defined here, it does not move the score.</li>
      <li>Anything that is only alleged. Allegations never score. Only adjudicated findings, primary documents, or multiple independent investigative sources do.</li>
      <li>Wealth, ideology, party or affiliation as such. The same act scores the same whoever does it.</li>
      <li>Anything the research agents could not find. Absence of evidence is not proof, so every score is a floor, and confidence and coverage say how much was actually found.</li>
    </ul>
    <p class="fine">Why dominance, extraction and corruption are in at all: following <em>Goliath's Curse</em>, they are the ways power gets turned against everyone else, and they are what let a few people steer the world toward catastrophe. They are scored only through documented acts.</p>
  </section>

  <h2 class="group-h">How scoring works</h2>
  <section class="panel px prose">
    <ol>
      <li><strong>Resolve</strong> who the person is (public figures only).</li>
      <li><strong>Research:</strong> one agent per rubric collects sourced, dated evidence from the web.</li>
      <li><strong>Judge:</strong> one LLM judge per rubric rates documented behavior from 0 to 4, citing evidence. No evidence means "insufficient evidence", not zero.</li>
      <li><strong>Score:</strong> plain code combines the ratings with the person's power and agency. The same evidence always gives the same score.</li>
    </ol>
    <p><strong>Score</strong> = harm × influence. The worst rubric dominates and the others add with diminishing returns. Points are the score × 1,000,000, so <strong>lower is better</strong>. Influence comes from power (office, organization size, net worth) and agency (rank and file score lower than executives).</p>
    <p><strong>Benefit is separate.</strong> Costly, verified good acts earn their own Guardian tier. It is never subtracted from harm, because harms to different people are not interchangeable. Good done in one area does not cancel harm done in another.</p>
    <p class="fine">The thresholds are first guesses and still being calibrated. Treat the numbers as a demo of the method, not as measurements.</p>
  </section>

  <h2 class="group-h">The rubrics</h2>
  <p class="meta-line">Tap a rubric to see what it counts, what it ignores, and its 0 to 4 anchors.</p>
  ${RUBRIC_DOCS.map(rubricDoc).join("")}
  ${rubricDoc(BENEFIT_DOC)}

  <h2 class="group-h">Tiers</h2>
  <div class="legends">${tiers}</div>
  <h2 class="group-h">Guardian tiers (benefit)</h2>
  <div class="legends">${guardians}</div>

  <h2 class="group-h">Sources and confidence</h2>
  <section class="panel px prose">
    <ul>
      <li><strong>Source tier 1:</strong> court records, regulatory filings, official orders, primary documents.</li>
      <li><strong>Source tier 2:</strong> major investigative journalism with named sourcing.</li>
      <li><strong>Source tier 3:</strong> opinion, advocacy, social media. Cannot support a score alone.</li>
      <li><strong>Counted</strong> evidence is what the judge actually cited for a rating.</li>
      <li><strong>Confidence</strong> is computed in code from source tiers and counts, not self-reported by the model. <strong>Provisional</strong> means under 50%.</li>
      <li><strong>Speech alone caps at level 2</strong> on the harm side and at level 1 on the benefit side, and settlements without admission cap at level 2.</li>
    </ul>
  </section>

  <section class="panel px prose warnbox">
    <p><strong>Everything here is generated by language models from web sources found at the time of each run.</strong> Scores are not verdicts. Check the linked evidence yourself before you rely on anything.</p>
  </section>`;
}

export function notFound() {
  return `<div class="empty px"><p class="big">GAME OVER</p><p>That page does not exist. <a href="#/">Back to the roster</a>.</p></div>`;
}
