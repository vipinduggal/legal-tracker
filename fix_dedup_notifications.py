import os

home = os.path.expanduser("~")
base = os.path.join(home, "legal-tracker")

# ── Add notification history to db.js ──────────────────────
db_path = os.path.join(base, "src", "db.js")

with open(db_path, 'r') as f:
    db_content = f.read()

# Add notification tracking functions
old_init = """export async function initDb() {
  await db.read();
  db.data ||= { research: {}, lastUpdated: {}, runs: [], digest: null };
  await db.write();
}"""

new_init = """export async function initDb() {
  await db.read();
  db.data ||= { research: {}, lastUpdated: {}, runs: [], digest: null, notified: {} };
  db.data.notified ||= {};
  await db.write();
}

// Check if we already notified about a specific item
export function hasBeenNotified(accountId, itemKey) {
  const key = accountId + ':' + itemKey;
  const notified = db.data.notified || {};
  if (!notified[key]) return false;
  // Consider notified if within last 30 days
  const daysSince = (Date.now() - new Date(notified[key]).getTime()) / (1000 * 60 * 60 * 24);
  return daysSince < 30;
}

// Mark an item as notified
export async function markNotified(accountId, itemKey) {
  db.data.notified ||= {};
  const key = accountId + ':' + itemKey;
  db.data.notified[key] = new Date().toISOString();
  // Clean up old entries (older than 60 days)
  const now = Date.now();
  for (const k of Object.keys(db.data.notified)) {
    const age = (now - new Date(db.data.notified[k]).getTime()) / (1000 * 60 * 60 * 24);
    if (age > 60) delete db.data.notified[k];
  }
  await db.write();
}"""

if old_init in db_content:
    db_content = db_content.replace(old_init, new_init)
    with open(db_path, 'w') as f:
        f.write(db_content)
    print("Done — notification tracking added to db.js")
else:
    print("WARNING — initDb pattern not found in db.js")
    idx = db_content.find('initDb')
    if idx > 0:
        print(db_content[idx:idx+300])

# ── Update researcher.js to use notification tracking ──────
researcher_path = os.path.join(base, "src", "researcher.js")

with open(researcher_path, 'r') as f:
    researcher = f.read()

# Update the import to include notification functions
old_import = 'import { verifyAccountContacts, getLiveIntelligence } from "./contactVerifier.js";'
new_import = '''import { verifyAccountContacts, getLiveIntelligence } from "./contactVerifier.js";
import { hasBeenNotified, markNotified } from "./db.js";'''

if old_import in researcher and 'hasBeenNotified' not in researcher:
    researcher = researcher.replace(old_import, new_import)
    print("Done — notification imports added to researcher.js")

with open(researcher_path, 'w') as f:
    f.write(researcher)

# ── Update detectChanges to filter already-notified items ──
old_detect = """export function detectChanges(oldData, newData) {
  if (!oldData) return ["New account researched"];
  const changes = [];

  const oldContacts = (oldData.contacts || []).map(c => c.name).sort().join(",");
  const newContacts = (newData.contacts || []).map(c => c.name).sort().join(",");
  if (oldContacts !== newContacts) {
    const added = (newData.contacts || []).filter(c => !(oldData.contacts || []).find(o => o.name === c.name));
    if (added.length) changes.push(`${added.length} new contact(s): ${added.map(c => c.name).join(", ")}`);
  }

  const oldLit = (oldData.litigation || []).length;
  const newLit = (newData.litigation || []).length;
  if (newLit > oldLit) changes.push(`${newLit - oldLit} new litigation item(s): ${(newData.litigation || []).slice(0, 2).map(l => l.type).join(", ")}`);

  const oldReg = (oldData.regulatory || []).length;
  const newReg = (newData.regulatory || []).length;
  if (newReg > oldReg) changes.push(`${newReg - oldReg} new regulatory item(s): ${(newData.regulatory || []).slice(0, 2).map(r => r.type).join(", ")}`);

  const oldTech = (oldData.tech || []).sort().join(",");
  const newTech = (newData.tech || []).sort().join(",");
  if (oldTech !== newTech) changes.push(`New technology detected: ${(newData.tech || []).slice(0, 3).join(", ")}`);

  const oldRoles = (oldData.open_roles || []).length;
  const newRoles = (newData.open_roles || []).length;
  if (newRoles > oldRoles) changes.push(`${newRoles} open legal role(s) found: ${(newData.open_roles || []).slice(0, 2).map(r => r.title).join(", ")}`);

  return changes.length ? changes : ["No significant changes detected"];
}"""

new_detect = """export function detectChanges(oldData, newData, accountId) {
  if (!oldData) return ["New account researched"];
  const changes = [];

  // New contacts
  const oldContactNames = new Set((oldData.contacts || []).map(c => c.name));
  const newContacts = (newData.contacts || []).filter(c => !oldContactNames.has(c.name));
  if (newContacts.length) {
    changes.push(`${newContacts.length} new contact(s): ${newContacts.map(c => c.name).join(", ")}`);
  }

  // New litigation — only items not previously seen
  const oldLitKeys = new Set((oldData.litigation || []).map(l => l.type + '|' + l.period));
  const newLitItems = (newData.litigation || []).filter(l => {
    const key = l.type + '|' + l.period;
    return !oldLitKeys.has(key);
  });
  if (newLitItems.length) {
    changes.push(`${newLitItems.length} new litigation item(s): ${newLitItems.slice(0, 2).map(l => l.type).join(", ")}`);
  }

  // New regulatory — only items not previously seen
  const oldRegKeys = new Set((oldData.regulatory || []).map(r => r.type + '|' + r.period));
  const newRegItems = (newData.regulatory || []).filter(r => {
    const key = r.type + '|' + r.period;
    return !oldRegKeys.has(key);
  });
  if (newRegItems.length) {
    changes.push(`${newRegItems.length} new regulatory item(s): ${newRegItems.slice(0, 2).map(r => r.type).join(", ")}`);
  }

  // New technology
  const oldTechSet = new Set((oldData.tech || []).map(t => t.toLowerCase()));
  const newTechItems = (newData.tech || []).filter(t => !oldTechSet.has(t.toLowerCase()));
  if (newTechItems.length) {
    changes.push(`New technology detected: ${newTechItems.slice(0, 3).join(", ")}`);
  }

  // New open roles — compare by title
  const oldRoleTitles = new Set((oldData.open_roles || []).map(r => (r.title || '').toLowerCase()));
  const newRoleItems = (newData.open_roles || []).filter(r => !oldRoleTitles.has((r.title || '').toLowerCase()));
  if (newRoleItems.length) {
    changes.push(`${newRoleItems.length} new open legal role(s): ${newRoleItems.slice(0, 2).map(r => r.title).join(", ")}`);
  }

  // New triggers — check if immediate triggers changed
  const oldTrigCount = (oldData.immediate_triggers || []).length;
  const newTrigCount = (newData.immediate_triggers || []).length;
  if (newTrigCount > oldTrigCount) {
    changes.push(`${newTrigCount - oldTrigCount} new immediate trigger(s) detected`);
  }

  return changes.length ? changes : ["No significant changes detected"];
}"""

if old_detect in researcher:
    researcher = researcher.replace(old_detect, new_detect)
    with open(researcher_path, 'w') as f:
        f.write(researcher)
    print("Done — detectChanges updated to track specific new items")
else:
    print("WARNING — detectChanges pattern not found")
    # Try to find it
    idx = researcher.find('export function detectChanges')
    if idx > 0:
        print("Found at:", idx)

print("")
print("="*50)
print("NOTIFICATION DEDUP COMPLETE")
print("="*50)
print("")
print("What changed:")
print("  1. db.js now tracks which items have been notified")
print("  2. detectChanges now compares specific items not just counts")
print("  3. Won't re-notify about same litigation/regulatory item")
print("  4. New contacts, new roles, new tech still trigger emails")
print("  5. Notification history cleaned up after 60 days")
print("")
print("Restart: pm2 restart legal-tracker")
