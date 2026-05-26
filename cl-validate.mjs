#!/usr/bin/env node
/**
 * cl-validate.mjs — CourtListener coverage / freshness / side-detection probe
 * -----------------------------------------------------------------------------
 * Purpose: answer the load-bearing question for the Partner Intelligence tool
 * BEFORE building anything: can CourtListener (free RECAP) reliably surface a
 * named partner's defense cases, with counsel populated, fast enough to matter?
 *
 * This script does NOT touch your Nazar code. It is a throwaway diagnostic.
 * It prints a scorecard. The scorecard decides which build path you're on.
 *
 * RUN:
 *   1. Sign in to CourtListener and get your API token from your PROFILE page.
 *      NOTE: API access is now a membership benefit (changed May 2026) — you may
 *      need a paid FLP membership for a working token, and access may be tiered.
 *      Confirm your token works before reading too much into a failure here:
 *      a 401/403 means "auth/access problem," NOT "data missing."
 *   2. export CL_TOKEN=your_token_here
 *   3. node cl-validate.mjs
 *
 * Requires Node 18+ (uses built-in fetch). No npm install needed.
 *
 * The four checks, per partner:
 *   [FIND]  findability-by-name   — does attorney search return their known case
 *                                   WITHOUT us already knowing the docket id?
 *   [CNSL]  counsel-population    — on the docket, is defense counsel actually
 *                                   filled in (not an empty block)?
 *   [SIDE]  side-correctness      — does parsing place the partner on DEFENSE?
 *   [FRESH] freshness             — lag between filing date and RECAP having it
 *                                   (only meaningful for a recently-filed case)
 * -----------------------------------------------------------------------------
 */

const TOKEN = process.env.CL_TOKEN;
const BASE = "https://www.courtlistener.com/api/rest/v4";
const FRESHNESS_BAR_DAYS = 30; // a "new defense matter" older than this is a weak sales trigger

if (!TOKEN) {
  console.error("\n  ERROR: set CL_TOKEN first.\n  Get a free token at https://www.courtlistener.com/profile/api/token/\n  Then: export CL_TOKEN=...\n");
  process.exit(1);
}

const headers = { Authorization: `Token ${TOKEN}`, "Content-Type": "application/json" };

/* ---------------------------------------------------------------------------
 * GROUND TRUTH — fill this in. Each partner needs:
 *   name      : exactly as you'd expect it on a docket (we also try variants)
 *   firm      : current firm (used to disambiguate common names)
 *   knownCase : a case you KNOW they are on, defense side, with party names.
 *               docketId is OPTIONAL — if you leave it null, the findability
 *               check is REAL (we make the tool find it by name). If you supply
 *               it, we can still run counsel/side checks but FIND is "assisted".
 *   recent    : true if this case was filed within ~60 days (anchors FRESH).
 * ------------------------------------------------------------------------- */
const PARTNERS = [
  {
    name: "Chris M. Katsantonis",
    nameVariants: ["Katsantonis", "Christopher Katsantonis", "Chris Katsantonis"],
    firm: "DLA Piper",
    knownCase: {
      caption: "Redstone Logics LLC v. Advanced Micro Devices, Inc.",
      defendant: "Advanced Micro Devices",
      docketId: null,            // leave null to test REAL findability
      court: "txwd",
    },
    recent: false,
  },
  {
    name: "Matthew Caplan",
    nameVariants: ["Caplan", "Matthew D. Caplan", "Matt Caplan"],
    firm: "Foley & Lardner", // NOTE: verify firm — Caplan is widely associated with Cooley; confirm before trusting SIDE result
    knownCase: {
      caption: "Doe et al v. Roblox Corporation et al",
      defendant: "Roblox",
      docketId: null,
      court: null,
    },
    recent: false,
  },
  {
    name: "Ragesh Tangri",
    nameVariants: ["Tangri", "Ragesh K. Tangri"],
    firm: "Morrison & Foerster",
    knownCase: {
      caption: "Reddit, Inc. v. Anthropic, PBC",
      defendant: "Anthropic",
      docketId: null,
      court: null,
    },
    recent: false,
  },
  // ADD A RECENT CASE HERE to make FRESH meaningful — filed in last ~60 days.
  // {
  //   name: "...", nameVariants: ["..."], firm: "...",
  //   knownCase: { caption: "...", defendant: "...", docketId: null, court: null },
  //   recent: true,
  // },
];

/* ---------------------------------------------------------------------------
 * Silent-failure guard. CourtListener's loose search will happily return
 * 2000+ unrelated results for a malformed query without erroring (we saw the
 * "q=foo" placeholder leak). Every response must be sanity-checked.
 * ------------------------------------------------------------------------- */
function guardSearchResponse(json, expectedTerms) {
  if (!json || typeof json.count !== "number") return { ok: false, why: "no count field" };
  if (json.count > 1000) return { ok: false, why: `implausible count ${json.count} — query likely fell back` };
  // Confirm at least one expected term appears somewhere in the first results.
  const blob = JSON.stringify(json.results || []).toLowerCase();
  const hit = expectedTerms.some(t => blob.includes(t.toLowerCase()));
  if (!hit && (json.results || []).length > 0)
    return { ok: false, why: "results don't contain any expected term — likely wrong query" };
  return { ok: true };
}

async function api(path) {
  const res = await fetch(`${BASE}${path}`, { headers });
  if (!res.ok) {
    const authIssue = res.status === 401 || res.status === 403;
    return {
      __error: `HTTP ${res.status} ${res.statusText}${authIssue ? " — AUTH/ACCESS problem, not a data problem. Check token & membership access level." : ""}`,
      __auth: authIssue,
      __path: path,
    };
  }
  return res.json();
}

const daysBetween = (a, b) => Math.round((new Date(b) - new Date(a)) / 86400000);

/* ---------------------------------------------------------------------------
 * Check 1: FINDABILITY — search the attorney/RECAP index by partner name,
 * see whether the known case surfaces without us supplying the docket id.
 * ------------------------------------------------------------------------- */
async function checkFindability(p) {
  const out = { status: "UNKNOWN", detail: "", dockets: [] };
  // Search RECAP dockets (type=r) for the partner's name; we then look for the
  // known defendant in any returned caption. q is the partner surname + firm.
  const q = encodeURIComponent(`${p.nameVariants[0]} ${p.firm}`);
  const json = await api(`/search/?type=r&q=${q}`);
  if (json.__error) { out.status = "ERROR"; out.detail = json.__error; return out; }

  const guard = guardSearchResponse(json, [p.nameVariants[0], p.knownCase.defendant]);
  if (!guard.ok) { out.status = "SILENT_FAIL"; out.detail = guard.why; return out; }

  const results = json.results || [];
  out.dockets = results.slice(0, 5).map(r => ({
    caseName: r.caseName, docket_id: r.docket_id, court: r.court_id,
    dateFiled: r.dateFiled, attorneyBlob: (r.attorney || "").slice(0, 200),
  }));
  const match = results.find(r =>
    (r.caseName || "").toLowerCase().includes(p.knownCase.defendant.toLowerCase()));
  if (match) {
    out.status = "PASS";
    out.detail = `found known case by name: "${match.caseName}" (docket ${match.docket_id})`;
    out.resolvedDocketId = match.docket_id;
    out.resolvedDateFiled = match.dateFiled;
  } else {
    out.status = "FAIL";
    out.detail = `name search returned ${json.count} dockets but none matched defendant "${p.knownCase.defendant}". Top hits: ${out.dockets.map(d => d.caseName).join(" | ") || "(none)"}`;
  }
  return out;
}

/* ---------------------------------------------------------------------------
 * Check 2+3: COUNSEL POPULATION + SIDE. Use the dedicated /attorneys/ endpoint
 * filtered to the docket, with nested party roles, which is structured (unlike
 * the free-text blob in the search index).
 * ------------------------------------------------------------------------- */
async function checkCounselAndSide(p, docketId) {
  const out = { counsel: "UNKNOWN", side: "UNKNOWN", detail: "" };
  if (!docketId) { out.detail = "no docket id resolved — cannot check counsel"; return out; }

  const json = await api(`/attorneys/?docket=${docketId}&filter_nested_results=true`);
  if (json.__error) { out.counsel = "ERROR"; out.detail = json.__error; return out; }

  const attys = json.results || [];
  if (attys.length === 0) {
    out.counsel = "EMPTY";
    out.detail = "docket present but /attorneys/ returned 0 — counsel not populated in RECAP";
    return out;
  }
  out.counsel = "POPULATED";

  // Find our partner among the attorneys.
  const mine = attys.find(a =>
    p.nameVariants.some(v => (a.name || "").toLowerCase().includes(v.toLowerCase())));
  if (!mine) {
    out.side = "PARTNER_NOT_LISTED";
    out.detail = `counsel populated (${attys.length} attorneys) but none matched ${p.name}. Listed: ${attys.map(a => a.name).slice(0, 8).join(", ")}`;
    return out;
  }

  // The party each attorney represents is in nested party_types / roles.
  // Side is NOT in the attorney object. parties_represented gives a party URL
  // and a role integer. We must fetch the party and read its `party_types`,
  // which contains the human-readable role name ("Defendant"/"Plaintiff").
  const reps = mine.parties_represented || [];
  if (reps.length === 0) {
    out.side = "NO_PARTY_LINK";
    out.detail = `matched ${mine.name} but no parties_represented`;
    return out;
  }

  const sides = [];
  for (const rep of reps) {
    if (!rep.party) continue;
    const partyPath = rep.party.replace(BASE, ""); // party is a full URL
    const party = await api(partyPath);
    if (party.__error) { sides.push(`ERR(${party.__error})`); continue; }
    if (process.env.CL_DUMP) {
      console.log(`\n   ----- RAW PARTY OBJECT -----`);
      console.log(JSON.stringify(party, null, 2).split("\n").slice(0, 40).map(l => "   " + l).join("\n"));
      console.log(`   ----- END PARTY -----\n`);
    }
    // party_types is an array; each has a `name` like "Defendant" / "Plaintiff".
    const types = (party.party_types || []).map(t => (t.name || "").toLowerCase());
    const blob = types.join(",") + " " + (party.name || "");
    if (blob.includes("defendant")) sides.push("DEFENSE");
    else if (blob.includes("plaintiff")) sides.push("PLAINTIFF");
    else sides.push(`OTHER(${types.join("|") || "unknown"})`);
  }

  if (sides.includes("DEFENSE") && !sides.includes("PLAINTIFF")) out.side = "DEFENSE";
  else if (sides.includes("PLAINTIFF") && !sides.includes("DEFENSE")) out.side = "PLAINTIFF";
  else if (sides.length) out.side = sides.join("+"); // shows mixed/other explicitly
  else out.side = "AMBIGUOUS";
  out.detail = `matched ${mine.name}; represents ${sides.join(", ")} => ${out.side}`;
  out._raw = mine;

  // DIAGNOSTIC: dump the matched attorney's raw structure so we can see the
  // real field names for party representation and fix the parser.
  if (process.env.CL_DUMP) {
    console.log(`\n   ----- RAW ATTORNEY OBJECT (${mine.name}) -----`);
    console.log(JSON.stringify(mine, null, 2).split("\n").map(l => "   " + l).join("\n"));
    console.log(`   ----- END RAW -----\n`);
  }
  return out;
}

/* ---------------------------------------------------------------------------
 * Check 4: FRESHNESS. Compare the docket's filing date to when RECAP first had
 * it (date_created on the docket). Only meaningful for recently filed cases.
 * ------------------------------------------------------------------------- */
async function checkFreshness(p, docketId, dateFiledFromSearch) {
  const out = { status: "UNTESTED", detail: "" };
  if (!p.recent) { out.detail = "case not flagged recent — freshness UNTESTED (an untested check is not a pass)"; return out; }
  if (!docketId) { out.status = "BLOCKED"; out.detail = "no docket id"; return out; }

  const d = await api(`/dockets/${docketId}/`);
  if (d.__error) { out.status = "ERROR"; out.detail = d.__error; return out; }
  const filed = d.date_filed || dateFiledFromSearch;
  const seen = d.date_created;
  if (!filed || !seen) { out.status = "NO_DATES"; out.detail = `filed=${filed} seen=${seen}`; return out; }
  const lag = daysBetween(filed, seen);
  out.lagDays = lag;
  out.status = lag <= FRESHNESS_BAR_DAYS ? "PASS" : "FAIL";
  out.detail = `filed ${filed}, in RECAP ${seen} → lag ${lag}d (bar ${FRESHNESS_BAR_DAYS}d)`;
  return out;
}

/* ---------------------------------------------------------------------------
 * Check 5: DOCKET ENTRIES — the real open question. Both triggers depend on
 * reading the actual filings. We pull /docket-entries/, count them, find the
 * newest entry date (entry freshness), and scan descriptions for the discovery
 * signal phrases the design identified (Rule 16 scheduling order, Rule 26(f),
 * motion to compel, deposition, protective order). This tells us whether RECAP
 * carries the entries needed for new-matter + discovery detection, fresh enough.
 * ------------------------------------------------------------------------- */
const DISCOVERY_SIGNALS = [
  "scheduling order", "rule 16", "rule 26(f)", "rule 26 f", "discovery plan",
  "motion to compel", "protective order", "notice of deposition", "deposition",
  "interrogator", "request for production", "discovery",
];

async function checkDocketEntries(docketId) {
  const out = { status: "UNKNOWN", detail: "", count: 0, newest: null, signals: [] };
  if (!docketId) { out.status = "BLOCKED"; out.detail = "no docket id"; return out; }

  // Order newest-first so the first page gives us the latest activity.
  const json = await api(`/docket-entries/?docket=${docketId}&order_by=-date_filed`);
  if (json.__error) { out.status = "ERROR"; out.detail = json.__error; return out; }

  const entries = json.results || [];
  out.count = json.count ?? entries.length;
  if (out.count === 0) {
    out.status = "EMPTY";
    out.detail = "docket present but ZERO entries in RECAP — cannot detect new-matter or discovery events";
    return out;
  }

  // Newest entry date = entry-level freshness (more honest than docket date_modified).
  const dates = entries.map(e => e.date_filed).filter(Boolean).sort().reverse();
  out.newest = dates[0] || null;
  const entryLag = out.newest ? daysBetween(out.newest, new Date().toISOString()) : null;

  // Scan descriptions for discovery signal phrases.
  const blob = entries
    .map(e => (e.description || "") + " " +
      ((e.recap_documents || []).map(d => d.description || "").join(" ")))
    .join(" ")
    .toLowerCase();
  out.signals = DISCOVERY_SIGNALS.filter(s => blob.includes(s));

  out.status = "POPULATED";
  out.detail = `${out.count} entries; newest ${out.newest} (${entryLag}d ago); ` +
    `discovery signals: ${out.signals.length ? out.signals.join(", ") : "NONE on first page"}`;

  if (process.env.CL_DUMP) {
    console.log(`\n   ----- FIRST 5 DOCKET ENTRY DESCRIPTIONS -----`);
    entries.slice(0, 5).forEach(e =>
      console.log(`   [${e.date_filed}] ${(e.description || "(no description)").slice(0, 140)}`));
    console.log(`   ----- END ENTRIES -----\n`);
  }
  return out;
}

/* ------------------------------------------------------------------------- */
async function run() {
  console.log(`\n${"=".repeat(78)}\nCourtListener validation — ${new Date().toISOString().slice(0, 10)}\nFreshness bar: ${FRESHNESS_BAR_DAYS} days\n${"=".repeat(78)}`);

  const scorecard = [];
  for (const p of PARTNERS) {
    console.log(`\n── ${p.name}  (${p.firm})`);
    console.log(`   known case: ${p.knownCase.caption}`);

    const find = await checkFindability(p);
    console.log(`   [FIND]  ${find.status.padEnd(11)} ${find.detail}`);

    // Resolve docket id: prefer one found by name; fall back to supplied id.
    const docketId = find.resolvedDocketId || p.knownCase.docketId;
    const assisted = !find.resolvedDocketId && p.knownCase.docketId ? " (ASSISTED — id supplied)" : "";

    const cs = await checkCounselAndSide(p, docketId);
    console.log(`   [CNSL]  ${cs.counsel.padEnd(11)} ${cs.counsel === "POPULATED" ? "" : cs.detail}`);
    console.log(`   [SIDE]  ${cs.side.padEnd(11)} ${cs.detail}${assisted}`);

    const fr = await checkFreshness(p, docketId, find.resolvedDateFiled);
    console.log(`   [FRESH] ${fr.status.padEnd(11)} ${fr.detail}`);

    const de = await checkDocketEntries(docketId);
    console.log(`   [ENTRY] ${de.status.padEnd(11)} ${de.detail}`);

    scorecard.push({
      partner: p.name,
      FIND: find.status, CNSL: cs.counsel, SIDE: cs.side, FRESH: fr.status,
      ENTRIES: de.count, DISCOVERY: de.signals.length ? "YES" : (de.status === "POPULATED" ? "none" : "-"),
      cleanPass: find.status === "PASS" && cs.counsel === "POPULATED" && cs.side === "DEFENSE",
    });
  }

  console.log(`\n${"=".repeat(78)}\nSCORECARD\n${"=".repeat(78)}`);
  console.table(scorecard);

  const clean = scorecard.filter(s => s.cleanPass).length;
  const n = scorecard.length;
  console.log(`\nClean passes (FIND + CNSL + SIDE=DEFENSE): ${clean}/${n}`);
  console.log(`Freshness: ${scorecard.filter(s => s.FRESH === "PASS").length}/${n} passed, ${scorecard.filter(s => s.FRESH === "UNTESTED").length} UNTESTED`);
  console.log(`Docket entries populated: ${scorecard.filter(s => s.ENTRIES > 0).length}/${n}; discovery signals found: ${scorecard.filter(s => s.DISCOVERY === "YES").length}/${n}`);
  console.log(`\nVERDICT GUIDE:`);
  console.log(`  • entries populated + discovery signals present → CourtListener CAN do both triggers; PACER pivot may be unnecessary`);
  console.log(`  • entries EMPTY or stale on known cases          → real gap; PACER (Fetch or direct) justified`);
  console.log(`  • findability or counsel mostly failing          → STOP. free RECAP can't carry this.`);
  console.log(`  • any SILENT_FAIL                                → fix query/guard before trusting ANY result\n`);
}

run().catch(e => { console.error("FATAL", e); process.exit(1); });
