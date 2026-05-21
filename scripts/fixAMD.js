// scripts/fixAMD.js
// Standalone fix: dedup contacts and apply live triggers for AMD
import "dotenv/config";
import { initDb, getResearch, setResearch } from "../src/db.js";
import { verifyAccountContacts, getLiveIntelligence } from "../src/contactVerifier.js";
import { ACCOUNTS } from "../config/accounts.js";
import { logger } from "../src/logger.js";

await initDb();

const account = ACCOUNTS.find(a => a.id === "amd");
if (!account) { console.error("AMD not found"); process.exit(1); }

console.log("Loading AMD research data...");
let data = await getResearch("amd");
if (!data) { console.error("No AMD data found"); process.exit(1); }

console.log("Contacts before dedup:", data.contacts?.length || 0);

// Step 1: Dedup contacts
function normalizeName(name) {
  return (name || "").toLowerCase().replace(/[^a-z\s]/g, "").replace(/\s+/g, " ").trim();
}

const roleRank = {
  "CLO": 14, "GC": 13, "Deputy GC": 12, "Associate GC": 11,
  "Head of Litigation": 10, "Head of Legal Operations": 9,
  "Head of Employment": 8, "Head of IP": 7, "Head of Privacy": 6,
  "Head of Compliance": 5, "Head of Regulatory": 4, "Head of Corporate": 3,
  "CEO": 13, "CFO": 12, "COO": 11, "CISO": 10,
  "Litigator": 2, "Other Legal": 1,
};

const byName = new Map();
for (const c of (data.contacts || [])) {
  const key = normalizeName(c.name);
  if (!key || key.length < 3) continue;
  if (!byName.has(key)) {
    byName.set(key, c);
  } else {
    const existing = byName.get(key);
    const existRank = roleRank[existing.tag] || 0;
    const newRank = roleRank[c.tag] || 0;
    if (newRank > existRank) {
      byName.set(key, { ...c, linkedin: c.linkedin || existing.linkedin, email: c.email || existing.email });
    } else {
      byName.set(key, { ...existing, linkedin: existing.linkedin || c.linkedin, email: existing.email || c.email });
    }
  }
}

data.contacts = Array.from(byName.values());
console.log("Contacts after dedup:", data.contacts.length);
data.contacts.forEach(c => console.log(" ", c.name, "|", c.tag, "|", c.confidence));

// Step 2: Get live intelligence
console.log("\nRunning live intelligence...");
const liveIntel = await getLiveIntelligence(account);

if (liveIntel) {
  console.log("\nLive intel result:");
  console.log("  Quality:", liveIntel.intelligence_quality);
  console.log("  Immediate triggers:", (liveIntel.immediate_triggers || []).length);
  console.log("  Strategic triggers:", (liveIntel.strategic_triggers || []).length);

  // Apply triggers
  const immediateTrigs = (liveIntel.immediate_triggers || []).map(t =>
    `IMMEDIATE [${t.urgency}] [${t.date}] ${t.trigger} — ${t.sales_implication}`
  );
  const strategicTrigs = (liveIntel.strategic_triggers || []).map(t =>
    `STRATEGIC [${t.timeframe}] ${t.trigger} — ${t.sales_implication}`
  );

  data.sales_triggers = [...immediateTrigs, ...strategicTrigs];
  data.immediate_triggers = liveIntel.immediate_triggers || [];
  data.strategic_triggers = liveIntel.strategic_triggers || [];
  data.intelligence_quality = liveIntel.intelligence_quality;
  data.intelligence_date = liveIntel.intelligence_date;
  data.live_intel_retrieved = liveIntel.retrievedAt;
  data.live_intel_sources = liveIntel.sources || [];

  if (liveIntel.financial_intel) {
    data.financial_intel = data.financial_intel || {};
    const fi = liveIntel.financial_intel;
    if (fi.earnings_signals) data.financial_intel.earnings_signals = fi.earnings_signals;
    if (fi.cost_initiatives) data.financial_intel.cost_initiatives = fi.cost_initiatives;
    if (fi.ma_activity) data.financial_intel.ma_activity = fi.ma_activity;
    if (fi.latest_filing) data.financial_intel.latest_filing = fi.latest_filing;
  }

  if (immediateTrigs.length || strategicTrigs.length) {
    console.log("\nTriggers applied:");
    data.sales_triggers.forEach(t => console.log(" ", t.slice(0, 100)));
  } else {
    console.log("WARNING: Still no triggers after live intel run");
    console.log("Raw Perplexity answer available but not structured");
  }
} else {
  console.log("WARNING: getLiveIntelligence returned null");
}

// Step 3: Save
await setResearch("amd", data);
console.log("\nSaved successfully");
console.log("Final state:");
console.log("  Contacts:", data.contacts.length);
console.log("  Immediate triggers:", (data.immediate_triggers || []).length);
console.log("  Strategic triggers:", (data.strategic_triggers || []).length);
console.log("\nRefresh http://localhost:3000 and check AMD Sales Triggers tab");
