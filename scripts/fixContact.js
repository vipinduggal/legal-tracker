// fixContact.js — Manually correct a contact in the database
// Usage: node scripts/fixContact.js "AMD" "Vin Riera" "Ava Hahn" "SVP General Counsel and Secretary" "GC"

import "dotenv/config";
import { initDb, getResearch, setResearch } from "../src/db.js";

const [accountQuery, oldName, newName, newTitle, newTag] = process.argv.slice(2);

if (!accountQuery || !oldName || !newName) {
  console.log("Usage: node scripts/fixContact.js \"Account Name\" \"Old Name\" \"New Name\" \"New Title\" \"Tag\"");
  console.log("Tags: CLO | GC | Head of Litigation | Head of Legal Operations | Litigator | Deputy GC");
  process.exit(1);
}

await initDb();

// Find account
const { ACCOUNTS } = await import("../config/accounts.js");
const account = ACCOUNTS.find(a =>
  a.name.toLowerCase().includes(accountQuery.toLowerCase()) ||
  a.id.includes(accountQuery.toLowerCase().replace(/\s+/g, "_"))
);

if (!account) {
  console.error("Account not found: " + accountQuery);
  process.exit(1);
}

const data = await getResearch(account.id);
if (!data) {
  console.error("No research data found for " + account.name);
  process.exit(1);
}

const existing = data.contacts.find(c => c.name.toLowerCase().includes(oldName.toLowerCase()));

if (existing) {
  // Update existing contact
  Object.assign(existing, {
    name: newName,
    title: newTitle || existing.title,
    tag: newTag || existing.tag,
    confidence: "High",
    confidence_reason: "Manually verified and corrected " + new Date().toLocaleDateString("en-US", { month: "short", year: "numeric" }),
    verifiedAt: new Date().toISOString(),
    notes: "Corrected from: " + oldName,
  });
  console.log("Updated: " + oldName + " -> " + newName + " at " + account.name);
} else {
  // Add as new contact
  data.contacts.unshift({
    name: newName,
    title: newTitle || "Unknown",
    tag: newTag || "GC",
    confidence: "High",
    confidence_reason: "Manually added " + new Date().toLocaleDateString("en-US", { month: "short", year: "numeric" }),
    verifiedAt: new Date().toISOString(),
    notes: "Manually added — replaced: " + oldName,
    linkedin: null,
    email: null,
  });
  console.log("Added new contact: " + newName + " at " + account.name);
  console.log("Note: " + oldName + " was not found — added as new contact");
}

await setResearch(account.id, data);
console.log("Saved to database successfully");
console.log("");
console.log("To verify, run: npm run research:account \"" + account.name + "\"");
