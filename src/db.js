// db.js — Simple JSON file database using lowdb
// Stores all research data locally in data/db.json

import { Low } from 'lowdb';
import { JSONFile } from 'lowdb/node';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { mkdirSync } from 'fs';

const __dirname = dirname(fileURLToPath(import.meta.url));
const DATA_DIR = process.env.DB_PATH ? require('path').dirname(process.env.DB_PATH) : (process.env.RAILWAY_ENVIRONMENT ? '/tmp' : join(__dirname, '..', 'data'));

mkdirSync(DATA_DIR, { recursive: true });

const file = join(DATA_DIR, 'db.json');
const adapter = new JSONFile(file);

const defaultData = {
  research: {},      // keyed by account id
  lastUpdated: {},   // keyed by account id → ISO date string
  digests: [],       // weekly digests array
  runs: [],          // audit log of research runs
};

const db = new Low(adapter, defaultData);

export async function initDb() {
  await db.read();
  // Ensure all default keys exist
  db.data = { ...defaultData, ...db.data };
  await db.write();
  return db;
}

export async function getResearch(accountId) {
  await db.read();
  return db.data.research[accountId] || null;
}

export async function setResearch(accountId, data) {
  await db.read();
  db.data.research[accountId] = data;
  db.data.lastUpdated[accountId] = new Date().toISOString();
  await db.write();
}

export async function getAllResearch() {
  await db.read();
  return db.data.research;
}

export async function getLastUpdated(accountId) {
  await db.read();
  return db.data.lastUpdated[accountId] || null;
}

export async function isStale(accountId, staleDays = 1) {
  const last = await getLastUpdated(accountId);
  if (!last) return true;
  const diffMs = Date.now() - new Date(last).getTime();
  const diffDays = diffMs / (1000 * 60 * 60 * 24);
  return diffDays >= staleDays;
}

export async function saveDigest(digest) {
  await db.read();
  db.data.digests.unshift({
    ...digest,
    savedAt: new Date().toISOString(),
  });
  // Keep only last 52 digests (1 year)
  db.data.digests = db.data.digests.slice(0, 52);
  await db.write();
}

export async function getLatestDigest() {
  await db.read();
  return db.data.digests[0] || null;
}

export async function logRun(entry) {
  await db.read();
  db.data.runs.unshift({ ...entry, timestamp: new Date().toISOString() });
  db.data.runs = db.data.runs.slice(0, 200); // keep last 200 runs
  await db.write();
}

export { db };

// Notification deduplication — tracks what alerts have been sent
// Prevents re-alerting about the same litigation/regulatory item

export function hasBeenNotified(accountId, itemKey) {
  const key = accountId + ':' + itemKey;
  const notified = db.data.notified || {};
  if (!notified[key]) return false;
  const daysSince = (Date.now() - new Date(notified[key]).getTime()) / (1000 * 60 * 60 * 24);
  return daysSince < 30;
}

export async function markNotified(accountId, itemKey) {
  await db.read();
  db.data.notified = db.data.notified || {};
  const key = accountId + ':' + itemKey;
  db.data.notified[key] = new Date().toISOString();
  // Clean up entries older than 60 days
  const now = Date.now();
  for (const k of Object.keys(db.data.notified)) {
    const age = (now - new Date(db.data.notified[k]).getTime()) / (1000 * 60 * 60 * 24);
    if (age > 60) delete db.data.notified[k];
  }
  await db.write();
}
