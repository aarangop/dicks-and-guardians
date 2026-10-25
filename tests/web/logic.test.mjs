// Run with: node --test tests/web/
import assert from "node:assert/strict";
import { test } from "node:test";

import {
  DEFAULT_STATE,
  applyFilters,
  enrich,
  groupPeople,
  matchesQuery,
  normalize,
  paramsToState,
  rankDicks,
  rankAmbivalent,
  rankGuardians,
  sortPeople,
  stateToParams,
} from "../../web/js/logic.js";

function person(over = {}) {
  return enrich({
    id: "p",
    name: "Test Person",
    descriptor: "tester",
    requested_name: "Test",
    rated_at: "2026-10-21T10:00:00Z",
    tier: "minor",
    score: 0.2,
    power: 0.5,
    confidence: 0.9,
    benefit: 0,
    benefit_tier: "none_documented",
    rubrics: [
      { id: "R1", severity: 2, evidence_ids: ["R1-E01"] },
      { id: "R2", severity: 1, evidence_ids: [] },
    ],
    benefit_rubrics: [{ id: "R1", severity: 3, evidence_ids: ["R1-E02"] }],
    evidence: [{ id: "R1-E01", claim: "Lobbied against the Climate Act" }],
    ...over,
  });
}

test("normalize strips accents and case", () => {
  assert.equal(normalize("Álvaro Uribe Vélez"), "alvaro uribe velez");
});

test("enrich derives driver from harm rubrics only, keeping benefit apart", () => {
  const p = person({ benefit_rubrics: [{ id: "R2", severity: 4, evidence_ids: ["R2-E01"] }] });
  assert.equal(p.driver, "R1");
  assert.equal(p.points, 200000);
  assert.equal(p.severities.R2, 1);
  assert.equal(p.benefitSeverities.R2, 4);
  assert.ok(p.countedIds.has("R2-E01"));
});

test("enrich: no severity above zero means no driver", () => {
  const p = person({ rubrics: [{ id: "R1", severity: 0, evidence_ids: [] }] });
  assert.equal(p.driver, "none");
});

test("enrich: unrated has no points", () => {
  assert.equal(person({ score: null, tier: "unrated" }).points, null);
});

test("search matches accents, descriptor and requested name, all tokens required", () => {
  const p = person({ name: "Álvaro Uribe", descriptor: "Colombian ex president" });
  assert.ok(matchesQuery(p, "alvaro"));
  assert.ok(matchesQuery(p, "colombian president"));
  assert.ok(!matchesQuery(p, "alvaro brazilian"));
});

test("evidence text is searched only when asked", () => {
  const p = person();
  assert.ok(!matchesQuery(p, "climate act"));
  assert.ok(matchesQuery(p, "climate act", true));
});

test("applyFilters combines tier, driver and confidence", () => {
  const a = person({ id: "a", tier: "major" });
  const b = person({ id: "b", tier: "minor", confidence: 0.3 });
  const c = person({ id: "c", tier: "minor", rubrics: [{ id: "R3", severity: 2 }] });
  const all = [a, b, c];
  assert.deepEqual(applyFilters(all, { tiers: new Set(["minor"]) }).map((p) => p.id), ["b", "c"]);
  assert.deepEqual(applyFilters(all, { driver: "R3" }).map((p) => p.id), ["c"]);
  assert.deepEqual(applyFilters(all, { minConfidence: 0.5 }).map((p) => p.id), ["a", "c"]);
});

test("sort by score puts unrated last in both directions", () => {
  const hi = person({ id: "hi", score: 0.9 });
  const lo = person({ id: "lo", score: 0.1 });
  const none = person({ id: "none", score: null, tier: "unrated" });
  assert.deepEqual(sortPeople([none, lo, hi], "score").map((p) => p.id), ["hi", "lo", "none"]);
  assert.deepEqual(sortPeople([none, hi, lo], "score_asc").map((p) => p.id), ["lo", "hi", "none"]);
});

test("grouping orders groups by severity, not alphabetically", () => {
  const people = [
    person({ id: "m", tier: "minor" }),
    person({ id: "u", tier: "ultimate" }),
    person({ id: "n", tier: "not_a_dick" }),
  ];
  const groups = groupPeople(people, "tier");
  assert.deepEqual(groups.map((g) => g.label), ["Ultimate Dick", "Minor Dick", "Not a Dick"]);
  assert.equal(groupPeople(people, "none").length, 1);
});

test("rankDicks: worst first, excludes Not a Dick and unrated", () => {
  const ranked = rankDicks([
    person({ id: "minor", score: 0.2 }),
    person({ id: "worst", tier: "ultimate", score: 0.9 }),
    person({ id: "clean", tier: "not_a_dick", score: 0 }),
    person({ id: "nr", tier: "unrated", score: null }),
  ]);
  assert.deepEqual(ranked.map((p) => p.id), ["worst", "minor"]);
});

test("rankGuardians ranks by benefit alone and ignores harm", () => {
  const g = (id, benefit, over = {}) =>
    person({ benefit, benefit_tier: "minor_guardian", ...over, id, name: id });
  const ranked = rankGuardians([
    g("low", 0.2, { tier: "not_a_dick", score: 0 }),
    g("high", 0.6, { tier: "ultimate", score: 0.9 }),
    person({ id: "none", benefit: 0, benefit_tier: "none_documented" }),
    person({ id: "nr", benefit: null, benefit_tier: "unrated" }),
  ]);
  assert.deepEqual(ranked.map((p) => p.id), ["high", "low"]);
});

test("rankAmbivalent needs both profiles and ranks by the weaker one", () => {
  const a = (id, score, benefit, over = {}) =>
    person({ id, name: id, score, benefit, benefit_tier: "major_guardian", ...over });
  const ranked = rankAmbivalent([
    a("both-high", 0.6, 0.5),
    a("lopsided", 0.95, 0.15),
    a("clean", 0, 0.9, { tier: "not_a_dick" }),
    a("no-benefit", 0.8, 0, { benefit_tier: "none_documented" }),
  ]);
  assert.deepEqual(ranked.map((p) => p.id), ["both-high", "lopsided"]);
});

test("URL state round-trips and rejects junk", () => {
  const state = {
    ...DEFAULT_STATE,
    q: "lula",
    tiers: new Set(["major", "minor"]),
    sort: "name",
    by: "tier",
    minConfidence: 0.5,
  };
  assert.deepEqual(paramsToState(stateToParams(state)), state);
  const junk = paramsToState(new URLSearchParams("tier=bogus&sort=bogus&by=bogus&conf=abc"));
  assert.deepEqual(junk, DEFAULT_STATE);
});
