// partnerMonitor.js — Partner-centric trigger engine for Consilio sales.
//
// For each tracked partner:
//   1. Attorney-search by name (RECAP dockets, type=r)          → FIND
//   2. Resolve dockets; pull /attorneys/?docket= + nested party → CNSL
//   3. Follow party URL, read party_types → DEFENSE/PLAINTIFF    → SIDE  (validated)
//   4. Pull /docket-entries/, scan for discovery signal phrases  → ENTRIES
//   5. Classify two triggers:
//        T1 NEW_DEFENSE_MATTER  — partner on defense, case new-to-us
//        T2 ENTERED_DISCOVERY   — scheduling order / Rule 26(f) / motion to compel
//
// Detection-only: writes triggers to partners.json + dashboard. No email/cron.
//
// Findings baked in from validation:
//   - jurisdiction flag: a case remanded/filed in state court is OUT OF COVERAGE,
//     emit "left federal court" rather than silently going stale.
//   - settling down-rank: joint motions / stay / dismissal → suppress T1 outreach.

import "dotenv/config";
import axios from "axios";
import { PARTNERS } from "../../config/partners.js";
import { getPartner, setPartner, logPartnerRun, initPartnersDb, pdb, getAddedPartners } from "./partnersDb.js";
import { logger } from "../logger.js";

const CL_BASE = "https://www.courtlistener.com/api/rest/v4";
const CL_TOKEN = process.env.COURTLISTENER_TOKEN;

function clHeaders() {
  return { "Authorization": `Token ${CL_TOKEN}` };
}

// Discovery signal phrases, strongest first. "scheduling order" is the gold signal.
const DISCOVERY_SIGNALS = [
  "scheduling order", "rule 16", "rule 26(f)", "rule 26 f", "discovery plan",
  "motion to compel", "protective order", "notice of deposition", "deposition",
  "interrogator", "request for production", "discovery",
];

// Case-status phrases that mean the matter is winding down — suppress outreach.
const WINDING_DOWN = [
  "notice of settlement", "notice of resolution", "joint motion to dismiss",
  "stipulation of dismissal", "motion to stay", "order ... stay", "settled",
  "voluntary dismissal", "case closed", "judgment entered",
];

const daysSince = (d) => d ? Math.round((Date.now() - new Date(d).getTime()) / 86400000) : null;
const sleep = (ms) => new Promise(r => setTimeout(r, ms));

// --- Rate limiting -----------------------------------------------------------
// CourtListener enforces a request rate limit (we hit 429s firing ~18 calls in
// 2s). We serialize calls with a minimum gap, and retry on 429 with backoff,
// honoring the Retry-After header when present.
const MIN_GAP_MS = Number(process.env.CL_MIN_GAP_MS || 15000); // 15s = under 5/min hard cap
let lastCallAt = 0;

async function throttle() {
  const wait = MIN_GAP_MS - (Date.now() - lastCallAt);
  if (wait > 0) await sleep(wait);
  lastCallAt = Date.now();
}

async function clGet(path, params, attempt = 0) {
  await throttle();
  try {
    const res = await axios.get(`${CL_BASE}${path}`, { headers: clHeaders(), params, timeout: 30000 });
    return res.data;
  } catch (err) {
    const status = err.response?.status;
    if (status === 429 && attempt < 4) {
      const retryAfter = Number(err.response?.headers?.['retry-after']);
      const backoff = (retryAfter ? retryAfter * 1000 : 0) || (2000 * Math.pow(2, attempt)); // 2s,4s,8s,16s
      logger.info(`  rate limited (429) on ${path} — waiting ${Math.round(backoff/1000)}s then retrying`);
      await sleep(backoff);
      return clGet(path, params, attempt + 1);
    }
    if (status === 401 || status === 403) {
      logger.warn(`CourtListener auth/access error (${status}) on ${path} — check COURTLISTENER_TOKEN / membership tier`);
    } else {
      logger.warn(`CourtListener ${path} failed: ${status} ${err.message}`);
    }
    return { __error: `${status || ""} ${err.message}` };
  }
}

// Guard against silent fallback (the q=foo placeholder failure we hit in validation).
function searchLooksValid(data, expectedTerms) {
  if (!data || data.__error || typeof data.count !== "number") return false;
  if (data.count > 1000) return false; // implausible → likely fell back
  const blob = JSON.stringify(data.results || []).toLowerCase();
  if ((data.results || []).length && !expectedTerms.some(t => blob.includes(t.toLowerCase()))) return false;
  return true;
}

// Step 1: find dockets for a partner by name + firm.
async function findDockets(partner) {
  const q = `${partner.nameVariants?.[0] || partner.name} ${partner.firm}`;
  const data = await clGet(`/search/`, { type: "r", q, order_by: "dateFiled desc", page_size: 20 });
  const expected = [partner.nameVariants?.[0] || partner.name, partner.knownCase?.defendant].filter(Boolean);
  if (!searchLooksValid(data, expected)) {
    return { ok: false, reason: data.__error ? "api_error" : "silent_fail_or_empty", dockets: [] };
  }
  return {
    ok: true,
    dockets: (data.results || []).map(r => ({
      docket_id: r.docket_id,
      caseName: r.caseName,
      court: r.court_id || r.court,
      dateFiled: r.dateFiled,
    })),
  };
}

// Step 2+3: pull attorneys on a docket, match our partner, follow party → side.
async function resolveSide(partner, docketId) {
  const data = await clGet(`/attorneys/`, { docket: docketId, filter_nested_results: true });
  if (data.__error) return { counsel: "ERROR", side: "UNKNOWN" };
  const attys = data.results || [];
  if (!attys.length) return { counsel: "EMPTY", side: "UNKNOWN" };

  const mine = attys.find(a =>
    (partner.nameVariants || [partner.name]).some(v => (a.name || "").toLowerCase().includes(v.toLowerCase())));
  if (!mine) return { counsel: "POPULATED", side: "PARTNER_NOT_LISTED", listed: attys.map(a => a.name).slice(0, 8) };

  const reps = mine.parties_represented || [];
  const sides = [];
  for (const rep of reps) {
    if (!rep.party) continue;
    const party = await clGet(rep.party.replace(CL_BASE, ""));
    if (party.__error) continue;
    const types = (party.party_types || []).map(t => (t.name || "").toLowerCase()).join(",");
    if (types.includes("defendant")) sides.push("DEFENSE");
    else if (types.includes("plaintiff")) sides.push("PLAINTIFF");
  }
  let side = "AMBIGUOUS";
  if (sides.includes("DEFENSE") && !sides.includes("PLAINTIFF")) side = "DEFENSE";
  else if (sides.includes("PLAINTIFF") && !sides.includes("DEFENSE")) side = "PLAINTIFF";
  else if (sides.length) side = sides.join("+");

  return {
    counsel: "POPULATED",
    side,
    contact: { email: mine.email || null, phone: mine.phone || null, raw: mine.contact_raw || null },
  };
}

// Step 4: pull docket entries, detect discovery + winding-down + freshness.
async function readEntries(docketId) {
  const data = await clGet(`/docket-entries/`, { docket: docketId, order_by: "-date_filed" });
  if (data.__error) return { status: "ERROR" };
  const entries = data.results || [];
  if (!entries.length) return { status: "EMPTY", count: 0 };

  const dates = entries.map(e => e.date_filed).filter(Boolean).sort().reverse();
  const newest = dates[0] || null;
  const blob = entries.map(e => (e.description || "")).join(" ").toLowerCase();

  return {
    status: "POPULATED",
    count: data.count ?? entries.length,
    newest,
    newestAgeDays: daysSince(newest),
    discoverySignals: DISCOVERY_SIGNALS.filter(s => blob.includes(s)),
    windingDown: WINDING_DOWN.some(s => blob.includes(s.replace(" ... ", " "))) ||
                 /joint motion to dismiss|notice of (settlement|resolution)|motion to stay/.test(blob),
    topDescriptions: entries.slice(0, 5).map(e => ({ date: e.date_filed, text: (e.description || "").slice(0, 160) })),
  };
}

// State court detection: CourtListener/PACER are federal-only. A remand or a
// state-court entry means the matter is leaving coverage.
function detectStateCourtExit(entries) {
  const blob = (entries.topDescriptions || []).map(e => e.text).join(" ").toLowerCase();
  if (/motion to remand|order granting.*remand|superior court|state court/.test(blob)) {
    return /granting.*remand|superior court/.test(blob) ? "LEFT_FEDERAL" : "REMAND_PENDING";
  }
  return null;
}

// Main detection pass for one partner.
async function detectForPartner(partner) {
  const record = (await getPartner(partner.id)) || { profile: partner, cases: {}, triggers: [] };
  record.profile = { ...partner };
  record.cases = record.cases || {};
  const newTriggers = [];

  const found = await findDockets(partner);
  if (!found.ok) {
    record.lastFindStatus = found.reason;
    await setPartner(partner.id, record);
    logger.info(`  ${partner.name}: find ${found.reason}`);
    return { partner: partner.id, find: found.reason, triggers: 0 };
  }

  for (const d of found.dockets) {
    if (!d.docket_id) continue;
    const side = await resolveSide(partner, d.docket_id);
    // Only care about cases where our partner is on DEFENSE (Consilio sells defense-side).
    if (side.side !== "DEFENSE") continue;

    const entries = await readEntries(d.docket_id);
    const stateExit = detectStateCourtExit(entries);
    const isNew = !record.cases[d.docket_id];

    // Persist/refresh the case record under the partner.
    const caseRec = {
      docket_id: d.docket_id,
      caseName: d.caseName,
      court: d.court,
      jurisdiction: stateExit ? "LEAVING_FEDERAL" : "federal",
      dateFiled: d.dateFiled,
      side: side.side,
      contact: side.contact || null,
      entryCount: entries.count || 0,
      newestEntry: entries.newest || null,
      discoverySignals: entries.discoverySignals || [],
      windingDown: !!entries.windingDown,
      stateExit: stateExit || null,
      lastSeen: new Date().toISOString(),
    };
    record.cases[d.docket_id] = caseRec;

    // --- Trigger 1: NEW defense matter (suppressed if winding down) ---
    if (isNew && !caseRec.windingDown && !stateExit) {
      newTriggers.push({
        type: "NEW_DEFENSE_MATTER",
        docket_id: d.docket_id,
        caseName: d.caseName,
        court: d.court,
        detectedAt: new Date().toISOString(),
        outreachAngle: `${partner.name} newly appears as defense counsel on ${d.caseName} (${d.court}). New defense matter → eDiscovery + document-review need before vendor selection (typically 30-60 days post-filing).`,
        evidence: caseRec.contact,
      });
    } else if (isNew && caseRec.windingDown) {
      logger.info(`  ${partner.name}: ${d.caseName} is new but winding down — T1 suppressed`);
    }

    // --- Trigger 2: entered discovery ---
    const enteredDiscovery = (entries.discoverySignals || []).some(s =>
      ["scheduling order", "rule 16", "rule 26(f)", "rule 26 f"].includes(s));
    const alreadyFlagged = (record.triggers || []).some(t => t.type === "ENTERED_DISCOVERY" && t.docket_id === d.docket_id);
    if (enteredDiscovery && !caseRec.windingDown && !stateExit && !alreadyFlagged) {
      newTriggers.push({
        type: "ENTERED_DISCOVERY",
        docket_id: d.docket_id,
        caseName: d.caseName,
        court: d.court,
        detectedAt: new Date().toISOString(),
        signals: entries.discoverySignals,
        outreachAngle: `${d.caseName} (defended by ${partner.name}) shows discovery activity [${entries.discoverySignals.join(", ")}]. Discovery = active eDiscovery + review demand now.`,
        evidence: { topDescriptions: entries.topDescriptions },
      });
    }

    // Surface state-court exit as an informational event (not an outreach trigger).
    if (stateExit === "LEFT_FEDERAL") {
      logger.info(`  ${partner.name}: ${d.caseName} LEFT FEDERAL COURT — now out of CourtListener/PACER coverage`);
    }
  }

  record.triggers = [...newTriggers, ...(record.triggers || [])].slice(0, 100);
  await setPartner(partner.id, record);
  logger.info(`  ${partner.name}: ${Object.keys(record.cases).length} defense cases, ${newTriggers.length} new triggers`);
  return { partner: partner.id, find: "ok", defenseCases: Object.keys(record.cases).length, triggers: newTriggers.length };
}

export async function runPartnerMonitor(partnerId = null, batchSize = null) {
  if (!CL_TOKEN) {
    logger.warn("COURTLISTENER_TOKEN not set — skipping partner monitor");
    return { checked: 0 };
  }
  const start = Date.now();
  await initPartnersDb();
  const added = await getAddedPartners();
  // The tracked universe = seed partners + manually-added partners (deduped by id).
  const universe = [...PARTNERS];
  for (const a of added) if (!universe.some(p => p.id === a.id)) universe.push(a);

  let targets = partnerId ? universe.filter(p => p.id === partnerId) : universe.filter(p => p.active !== false);

  // Batching: free tier caps at 50 req/hr (~5-6 partners). When batchSize is set,
  // process the LEAST-RECENTLY-CHECKED partners first, so running twice covers all.
  if (!partnerId && batchSize) {
    const checkedAt = (id) => {
      const t = pdb.data.lastChecked?.[id];
      return t ? new Date(t).getTime() : 0; // never-checked sorts first
    };
    targets = [...targets].sort((a, b) => checkedAt(a.id) - checkedAt(b.id)).slice(0, batchSize);
  }

  logger.info(`=== Partner monitor started — ${targets.length} partners${batchSize ? ` (batch of ${batchSize})` : ""} ===`);
  if (batchSize) logger.info(`   batch: ${targets.map(t => t.name).join(", ")}`);

  const summary = [];
  for (const p of targets) {
    try {
      summary.push(await detectForPartner(p));
    } catch (err) {
      logger.error(`Partner monitor failed for ${p.name}`, { error: err.message });
      summary.push({ partner: p.id, find: "error", triggers: 0 });
    }
  }

  const duration = Math.round((Date.now() - start) / 1000);
  const totalTriggers = summary.reduce((n, s) => n + (s.triggers || 0), 0);
  logger.info(`=== Partner monitor complete in ${duration}s — ${totalTriggers} triggers ===`);
  await logPartnerRun({ job: "partner_monitor", duration, partners: targets.length, triggers: totalTriggers, summary });
  return { checked: targets.length, triggers: totalTriggers, summary };
}

// Direct execution:
//   npm run partners:detect                  → all active partners
//   npm run partners:detect -- --batch=5      → 5 least-recently-checked
//   npm run partners:detect -- <partnerId>    → single partner
if (process.argv[1] && process.argv[1].endsWith("partnerMonitor.js")) {
  const args = process.argv.slice(2);
  const batchArg = args.find(a => a.startsWith("--batch="));
  const batchSize = batchArg ? Number(batchArg.split("=")[1]) : null;
  const idArg = args.find(a => !a.startsWith("--")) || null;
  runPartnerMonitor(idArg, batchSize)
    .then(r => { console.log("\nPartner monitor complete:", JSON.stringify(r, null, 2)); process.exit(0); })
    .catch(e => { console.error("Fatal:", e.message); process.exit(1); });
}
