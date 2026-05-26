// partnersDb.js — Isolated lowdb store for the partner intelligence tool.
// Deliberately SEPARATE from Nazar's db.json so partner-tool bugs can never
// corrupt live account data. Same lowdb patterns as src/db.js.

import { Low } from 'lowdb';
import { JSONFile } from 'lowdb/node';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { mkdirSync } from 'fs';

const __dirname = dirname(fileURLToPath(import.meta.url));
const DATA_DIR = process.env.RAILWAY_ENVIRONMENT ? '/tmp' : join(__dirname, '..', 'data');
mkdirSync(DATA_DIR, { recursive: true });

const file = join(DATA_DIR, 'partners.json');
const adapter = new JSONFile(file);

// Partner is the root entity. Cases hang off the partner via appearances.
const defaultData = {
  partners: {},      // keyed by partner id → { profile, cases[], triggers[], ... }
  added: {},         // manually-added partner profiles (keyed by id)
  lastChecked: {},   // keyed by partner id → ISO date
  counters: {},      // daily caps: { "YYYY-MM-DD": { adds: n, immediateSearches: n } }
  runs: [],          // audit log
};

const pdb = new Low(adapter, defaultData);

export async function initPartnersDb() {
  await pdb.read();
  pdb.data = { ...defaultData, ...pdb.data };
  await pdb.write();
  return pdb;
}

export async function getPartner(id) {
  await pdb.read();
  return pdb.data.partners[id] || null;
}

export async function setPartner(id, data) {
  await pdb.read();
  pdb.data.partners[id] = data;
  pdb.data.lastChecked[id] = new Date().toISOString();
  await pdb.write();
}

export async function getAllPartners() {
  await pdb.read();
  return pdb.data.partners;
}

export async function logPartnerRun(entry) {
  await pdb.read();
  pdb.data.runs.unshift({ ...entry, timestamp: new Date().toISOString() });
  pdb.data.runs = pdb.data.runs.slice(0, 200);
  await pdb.write();
}

// --- Manual partner add + daily caps ----------------------------------------
const ADDS_PER_DAY = 10;
const IMMEDIATE_SEARCHES_PER_DAY = 2;

function today() { return new Date().toISOString().slice(0, 10); }

function slugify(name, firm) {
  const s = (x) => (x || "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  return `${s(name)}-${s(firm)}`.slice(0, 80);
}

export async function getCounters() {
  await pdb.read();
  const d = today();
  return pdb.data.counters[d] || { adds: 0, immediateSearches: 0 };
}

// Returns { ok, error?, id?, remainingAdds, immediateAllowed }
export async function addPartner({ name, firm, city, tier }) {
  await pdb.read();
  const d = today();
  pdb.data.counters[d] = pdb.data.counters[d] || { adds: 0, immediateSearches: 0 };
  const c = pdb.data.counters[d];

  // Validation — guard against corrupting the DB with junk.
  if (!name || !name.trim()) return { ok: false, error: "Name is required." };
  if (!firm || !firm.trim()) return { ok: false, error: "Firm is required." };
  if (c.adds >= ADDS_PER_DAY) return { ok: false, error: `Daily add limit reached (${ADDS_PER_DAY}/day). Try again tomorrow.` };

  const id = slugify(name, firm);
  const exists = pdb.data.added[id] || pdb.data.partners[id];
  if (exists) return { ok: false, error: `Already tracking ${name} at ${firm}.`, id };

  const surname = name.trim().split(/\s+/).pop();
  pdb.data.added[id] = {
    id,
    name: name.trim(),
    nameVariants: [surname, name.trim()],
    firm: firm.trim(),
    city: (city || "").trim(),
    tier: tier === "senior_associate" ? "senior_associate" : "partner",
    active: true,
    source: "manual",
    addedAt: new Date().toISOString(),
  };
  c.adds += 1;
  await pdb.write();

  const immediateAllowed = c.immediateSearches < IMMEDIATE_SEARCHES_PER_DAY;
  return { ok: true, id, remainingAdds: ADDS_PER_DAY - c.adds, immediateAllowed, immediateRemaining: IMMEDIATE_SEARCHES_PER_DAY - c.immediateSearches };
}

// Call before running an immediate (on-add) search. Returns false if cap hit.
export async function consumeImmediateSearch() {
  await pdb.read();
  const d = today();
  pdb.data.counters[d] = pdb.data.counters[d] || { adds: 0, immediateSearches: 0 };
  if (pdb.data.counters[d].immediateSearches >= IMMEDIATE_SEARCHES_PER_DAY) return false;
  pdb.data.counters[d].immediateSearches += 1;
  await pdb.write();
  return true;
}

export async function getAddedPartners() {
  await pdb.read();
  return Object.values(pdb.data.added || {});
}

export { ADDS_PER_DAY, IMMEDIATE_SEARCHES_PER_DAY };

export { pdb };
