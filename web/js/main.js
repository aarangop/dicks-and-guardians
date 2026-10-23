import {
  DEFAULT_STATE,
  applyFilters,
  enrich,
  groupPeople,
  paramsToState,
  rankAmbivalent,
  rankDicks,
  rankGuardians,
  sortPeople,
  stateToParams,
} from "./logic.js";
import { esc, formatDate, points } from "./format.js";
import * as views from "./views.js";

const { BOARD_KINDS } = views;
const RANKERS = { dicks: rankDicks, guardians: rankGuardians, ambivalent: rankAmbivalent };

const app = document.getElementById("app");
const ticker = document.getElementById("ticker");
const foot = document.getElementById("data-info");

let people = [];
let generatedAt = "";
let roster = { ...DEFAULT_STATE, tiers: new Set() };
let evFilter = { rubric: "all", tier: "all", counted: false };
let currentPerson = null;

// --- data -------------------------------------------------------------------

/** `?data=` lets you preview another JSON file, but only from this same origin. */
function dataUrl() {
  const override = new URLSearchParams(location.search).get("data");
  if (override) {
    const u = new URL(override, location.href);
    if (u.origin === location.origin) return u.href;
  }
  return new URL("./data/people.json", location.href).href;
}

async function load() {
  // data/people.js embeds the data so the site also works opened straight from disk (file://),
  // where browsers block fetch(). An explicit ?data= override or a missing script falls back.
  const override = new URLSearchParams(location.search).has("data");
  let json = override ? null : window.PEOPLE_DATA;
  if (!json) {
    const res = await fetch(dataUrl(), { cache: "no-cache" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    json = await res.json();
  }
  people = json.people.map(enrich);
  generatedAt = json.generated_at ?? "";
}

// --- routing ----------------------------------------------------------------

function parseHash() {
  const raw = location.hash.replace(/^#/, "") || "/";
  const [path, query = ""] = raw.split("?");
  return { parts: path.split("/").filter(Boolean), params: new URLSearchParams(query) };
}

function setActiveNav(name) {
  document.querySelectorAll("nav a").forEach((a) => {
    a.classList.toggle("active", a.dataset.nav === name);
    a.toggleAttribute("aria-current", a.dataset.nav === name);
  });
}

function route() {
  const { parts, params } = parseHash();
  const [head, arg] = parts;
  window.scrollTo(0, 0);
  if (!head) return showRoster(params);
  if (head === "saints") return showBoard("guardians"); // old bookmarks
  if (BOARD_KINDS.includes(head)) return showBoard(head);
  if (head === "about") return show("about", views.about());
  if (head === "p" && arg) return showPerson(decodeURIComponent(arg));
  show("", views.notFound());
}

function show(nav, html) {
  setActiveNav(nav);
  app.innerHTML = html;
  app.focus({ preventScroll: true });
}

// --- roster -----------------------------------------------------------------

function showRoster(params) {
  roster = paramsToState(params);
  show("roster", `${views.rosterControls(roster)}<div id="results"></div>`);
  renderResults();
}

function renderResults() {
  const filtered = applyFilters(people, roster);
  const sorted = sortPeople(filtered, roster.sort);
  const groups = groupPeople(sorted, roster.by);
  document.getElementById("results").innerHTML = views.rosterResults(groups, people.length, filtered.length);
}

/** Keep the URL in sync so a filtered view can be bookmarked or shared. */
function syncUrl() {
  const qs = stateToParams(roster).toString();
  history.replaceState(null, "", `#/${qs ? `?${qs}` : ""}`);
}

function onRosterInput(e) {
  const t = e.target;
  if (t.id === "q") roster.q = t.value;
  else if (t.id === "driver") roster.driver = t.value;
  else if (t.id === "by") roster.by = t.value;
  else if (t.id === "sort") roster.sort = t.value;
  else if (t.id === "ev") roster.inEvidence = t.checked;
  else if (t.id === "conf") {
    roster.minConfidence = Number(t.value);
    document.getElementById("conf-out").textContent = `${Math.round(roster.minConfidence * 100)}%`;
  } else return;
  syncUrl();
  renderResults();
}

// --- boards -----------------------------------------------------------------

function showBoard(kind) {
  show(kind, views.leaderboard(kind, RANKERS[kind](people)));
}

// --- detail -----------------------------------------------------------------

function showPerson(id) {
  const person = people.find((p) => p.id === id);
  if (!person) return show("", views.notFound());
  currentPerson = person;
  evFilter = { rubric: "all", tier: "all", counted: false };
  show("", views.detail(person, evFilter));
  document.title = `${person.name} · Dicks and Guardians`;
  document.querySelectorAll("[data-count]").forEach(countUp);
}

function rerenderEvidence() {
  document.getElementById("ev-filters").innerHTML = views.evidenceFilters(currentPerson, evFilter);
  document.getElementById("ev-list").innerHTML = views.evidenceList(currentPerson, evFilter);
}

/** Arcade-style score counter. Skipped for people who prefer reduced motion. */
function countUp(el) {
  const target = Number(el?.dataset.target);
  if (!el || !Number.isFinite(target) || target <= 0) return;
  if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  const start = performance.now();
  const duration = 1100;
  const tick = (now) => {
    const k = Math.min((now - start) / duration, 1);
    const eased = 1 - (1 - k) ** 3;
    el.textContent = points(Math.round(target * eased));
    if (k < 1) requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
}

function jumpToEvidence(id) {
  // The cited item may be hidden by the current filter, so reset it first.
  if (!document.getElementById(`ev-${id}`)) {
    evFilter = { rubric: "all", tier: "all", counted: false };
    rerenderEvidence();
  }
  const el = document.getElementById(`ev-${id}`);
  if (!el) return;
  el.scrollIntoView({ behavior: "smooth", block: "center" });
  el.classList.add("flash");
  setTimeout(() => el.classList.remove("flash"), 1600);
}

// --- chrome -----------------------------------------------------------------

function renderChrome() {
  const dick = rankDicks(people)[0];
  const guardian = rankGuardians(people)[0];
  const item = (cls, label, p, value) =>
    p ? `<a class="hi ${cls}" href="#/p/${encodeURIComponent(p.id)}">${label} <b>${esc(p.name)}</b> ${points(value)}</a>` : "";
  ticker.innerHTML = `<span class="hi">HI-SCORE</span>${item("dick", "TOP DICK", dick, dick?.points)}${item("guardian", "TOP GUARDIAN", guardian, guardian?.benefitPoints)}<span class="hi blink">INSERT COIN</span>`;
  foot.textContent = `${people.length} players · data from ${formatDate(generatedAt) || "unknown date"}`;
}

function onClick(e) {
  const cite = e.target.closest("[data-ev]");
  if (cite) {
    e.preventDefault();
    return jumpToEvidence(cite.dataset.ev);
  }
  const tier = e.target.closest("[data-tier].chip");
  if (tier) {
    const id = tier.dataset.tier;
    roster.tiers.has(id) ? roster.tiers.delete(id) : roster.tiers.add(id);
    tier.classList.toggle("on", roster.tiers.has(id));
    tier.setAttribute("aria-pressed", String(roster.tiers.has(id)));
    syncUrl();
    return renderResults();
  }
  if (e.target.id === "reset") {
    roster = { ...DEFAULT_STATE, tiers: new Set() };
    history.replaceState(null, "", "#/");
    return showRoster(new URLSearchParams());
  }
  const d = e.target.closest("[data-f-rubric],[data-f-tier],[data-f-counted]");
  if (d && currentPerson) {
    if (d.dataset.fRubric) evFilter.rubric = d.dataset.fRubric;
    if (d.dataset.fTier) evFilter.tier = d.dataset.fTier;
    if (d.dataset.fCounted) evFilter.counted = !evFilter.counted;
    rerenderEvidence();
  }
}

async function main() {
  app.addEventListener("input", onRosterInput);
  app.addEventListener("click", onClick);
  try {
    await load();
  } catch (err) {
    app.innerHTML = `<div class="empty px"><p class="big">LOAD ERROR</p><p>Could not load the data file (${esc(err.message)}). If you opened index.html straight from disk, run <code>uv run python scripts/export_web_data.py</code> to regenerate data/people.js.</p></div>`;
    return;
  }
  renderChrome();
  window.addEventListener("hashchange", () => {
    document.title = "Dicks and Guardians";
    route();
  });
  route();
}

main();
