import os

home = os.path.expanduser("~")
base = os.path.join(home, "legal-tracker")

# ── File 1: contactVerifier.js ─────────────────────────────
verifier_path = os.path.join(base, "src", "contactVerifier.js")

verifier = '''// contactVerifier.js
// Uses Perplexity Sonar API (live web search) to verify contacts are current
// Cost: ~$0.001 per contact check — very cheap

import axios from "axios";
import { logger } from "./logger.js";

const PERPLEXITY_KEY = process.env.PERPLEXITY_API_KEY;

/**
 * Verify a single contact is currently in their role using live web search.
 * Returns enriched contact object with verified fields.
 */
export async function verifyContact(contact, accountName) {
  if (!PERPLEXITY_KEY) {
    logger.warn("PERPLEXITY_API_KEY not set — skipping live verification");
    return { ...contact, verified: false, verifiedAt: null };
  }

  const query = `Who is the current ${contact.tag} or ${contact.title} at ${accountName} in 2025 or 2026? Is ${contact.name} still in this role?`;

  try {
    const response = await axios.post(
      "https://api.perplexity.ai/chat/completions",
      {
        model: "sonar",
        messages: [
          {
            role: "system",
            content: "You are a corporate legal directory researcher. Answer only with verified, current information from the web. Today is " + new Date().toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" }) + ". Be concise and factual.",
          },
          { role: "user", content: query },
        ],
        max_tokens: 400,
      },
      {
        headers: {
          Authorization: "Bearer " + PERPLEXITY_KEY,
          "Content-Type": "application/json",
        },
        timeout: 15000,
      }
    );

    const answer = response.data?.choices?.[0]?.message?.content || "";
    const citations = response.data?.citations || [];

    // Parse the answer to determine confidence
    const nameLower = contact.name.toLowerCase();
    const answerLower = answer.toLowerCase();

    let confidence = "Medium";
    let confidence_reason = "Perplexity web search conducted — review answer below";
    let currentName = contact.name;
    let isCurrent = true;

    // Check for departure signals
    const departureSignals = ["left ", "departed", "no longer", "former", "previously", "resigned", "retired", "stepped down", "replaced by"];
    const currentSignals = ["currently", "is the", "serves as", "appointed", "named as", "joined as", "promoted to"];

    const hasDeparture = departureSignals.some(s => answerLower.includes(s) && answerLower.indexOf(s) < answerLower.indexOf(nameLower) + 100);
    const hasCurrent = currentSignals.some(s => answerLower.includes(s));

    if (hasDeparture && answerLower.includes(nameLower)) {
      confidence = "Low";
      confidence_reason = "Web search suggests possible departure — verify on LinkedIn before outreach";
      isCurrent = false;
    } else if (hasCurrent && answerLower.includes(nameLower)) {
      confidence = "High";
      confidence_reason = "Confirmed current via Perplexity web search " + new Date().toLocaleDateString("en-US", { month: "short", year: "numeric" });
    } else if (!answerLower.includes(nameLower)) {
      confidence = "Low";
      confidence_reason = "Name not found in current web search results — verify on LinkedIn";
      isCurrent = false;
    }

    return {
      ...contact,
      confidence,
      confidence_reason,
      isCurrent,
      verificationAnswer: answer.slice(0, 300),
      verificationSources: citations.slice(0, 2),
      verifiedAt: new Date().toISOString(),
      verified: true,
    };

  } catch (err) {
    logger.warn("Contact verification failed for " + contact.name + " at " + accountName, { error: err.message });
    return {
      ...contact,
      confidence: contact.confidence || "Medium",
      confidence_reason: "Verification attempted but failed — verify manually on LinkedIn",
      verified: false,
      verifiedAt: null,
    };
  }
}

/**
 * Verify all contacts for an account.
 * Only re-verifies contacts that are Low confidence or not recently verified.
 */
export async function verifyAccountContacts(account, researchData, forceAll = false) {
  if (!researchData?.contacts?.length) return researchData;

  const staleThresholdDays = 7;
  const now = Date.now();

  const contactsToVerify = researchData.contacts.filter(c => {
    if (forceAll) return true;
    if (c.confidence === "Low") return true;
    if (!c.verifiedAt) return true;
    const daysSince = (now - new Date(c.verifiedAt).getTime()) / (1000 * 60 * 60 * 24);
    return daysSince > staleThresholdDays;
  });

  if (!contactsToVerify.length) {
    logger.info("All contacts recently verified for " + account.name);
    return researchData;
  }

  logger.info("Verifying " + contactsToVerify.length + " contacts for " + account.name);

  const verified = await Promise.all(
    contactsToVerify.map(c => verifyContact(c, account.name))
  );

  // Merge verified contacts back
  const verifiedMap = new Map(verified.map(c => [c.name, c]));
  researchData.contacts = researchData.contacts.map(c =>
    verifiedMap.has(c.name) ? verifiedMap.get(c.name) : c
  );

  return researchData;
}
''';

with open(verifier_path, 'w') as f:
    f.write(verifier)
print("Done — contactVerifier.js written")

# ── File 2: Updated prompts.js with recency instructions ───
prompts_path = os.path.join(base, "src", "prompts.js")

with open(prompts_path, 'r') as f:
    prompts_content = f.read()

# Add recency instruction to the research prompt
old_priorities = "RESEARCH PRIORITIES:"
new_priorities = """RECENCY REQUIREMENTS — CRITICAL:
- You MUST prioritize information from 2025 and 2026 over older sources
- For contacts: ONLY include people currently in their roles as of 2025-2026. If you are uncertain whether someone is still in a role, mark confidence as Low and note it explicitly
- For litigation: focus on matters filed or active in 2024-2026. Clearly date all entries
- For financial intel: use the most recent earnings call or filing available — state the exact date
- If you only have information older than 2024 for a field, say so explicitly rather than presenting stale data as current
- Never present 2022 or 2023 data as if it is current without flagging it as potentially outdated

RESEARCH PRIORITIES:"""

prompts_content = prompts_content.replace(old_priorities, new_priorities)

with open(prompts_path, 'w') as f:
    f.write(prompts_content)
print("Done — prompts.js updated with recency requirements")

# ── File 3: Update researcher.js to add verification step ──
researcher_path = os.path.join(base, "src", "researcher.js")

with open(researcher_path, 'r') as f:
    researcher_content = f.read()

if 'verifyAccountContacts' not in researcher_content:
    old_import = 'import { buildResearchPrompt } from'
    new_import = 'import { buildResearchPrompt } from'
    # Add verifier import at top
    researcher_content = researcher_content.replace(
        "import Anthropic from '@anthropic-ai/sdk';",
        "import Anthropic from '@anthropic-ai/sdk';\nimport { verifyAccountContacts } from './contactVerifier.js';"
    )

    # Add verification step after successful parse
    old_return = "    logger.info(`✓ Researched: ${account.name}`"
    new_return = """    // Verify contacts with live web search if Perplexity key is available
    if (process.env.PERPLEXITY_API_KEY) {
      parsed = await verifyAccountContacts(account, parsed);
    }

    logger.info(`✓ Researched: ${account.name}`"""
    researcher_content = researcher_content.replace(old_return, new_return)

    with open(researcher_path, 'w') as f:
        f.write(researcher_content)
    print("Done — researcher.js updated with contact verification step")
else:
    print("Skipped researcher.js — already has verification")

# ── File 4: Manual contact correction script ───────────────
fix_path = os.path.join(base, "scripts", "fixContact.js")

fix_script = '''// fixContact.js — Manually correct a contact in the database
// Usage: node scripts/fixContact.js "AMD" "Vin Riera" "Ava Hahn" "SVP General Counsel and Secretary" "GC"

import "dotenv/config";
import { initDb, getResearch, setResearch } from "../src/db.js";

const [accountQuery, oldName, newName, newTitle, newTag] = process.argv.slice(2);

if (!accountQuery || !oldName || !newName) {
  console.log("Usage: node scripts/fixContact.js \\"Account Name\\" \\"Old Name\\" \\"New Name\\" \\"New Title\\" \\"Tag\\"");
  console.log("Tags: CLO | GC | Head of Litigation | Head of Legal Operations | Litigator | Deputy GC");
  process.exit(1);
}

await initDb();

// Find account
const { ACCOUNTS } = await import("../config/accounts.js");
const account = ACCOUNTS.find(a =>
  a.name.toLowerCase().includes(accountQuery.toLowerCase()) ||
  a.id.includes(accountQuery.toLowerCase().replace(/\\s+/g, "_"))
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
console.log("To verify, run: npm run research:account \\"" + account.name + "\\"");
''';

with open(fix_path, 'w') as f:
    f.write(fix_script)
print("Done — fixContact.js written")

# ── Update package.json with new scripts ───────────────────
import json
pkg_path = os.path.join(base, "package.json")
with open(pkg_path, 'r') as f:
    pkg = json.load(f)

pkg["scripts"]["fix:contact"] = "node scripts/fixContact.js"
pkg["scripts"]["verify:contacts"] = "node -e \"import('./src/db.js').then(async ({initDb,getAllResearch,setResearch})=>{await initDb();const r=await getAllResearch();const low=Object.entries(r).filter(([k,v])=>(v.contacts||[]).some(c=>c.confidence==='Low'||!c.verifiedAt));console.log('Accounts with unverified contacts:',low.map(([k])=>k).join(', '));})\""

with open(pkg_path, 'w') as f:
    json.dump(pkg, f, indent=2)
print("Done — package.json updated with fix:contact and verify:contacts scripts")

print("")
print("=" * 50)
print("ACCURACY UPGRADE COMPLETE")
print("=" * 50)
print("")
print("NEW COMMANDS:")
print("  Fix a wrong contact:")
print('  node scripts/fixContact.js "AMD" "Vin Riera" "Ava Hahn" "SVP General Counsel" "GC"')
print("")
print("  See all accounts with unverified contacts:")
print("  npm run verify:contacts")
print("")
print("NEXT STEP — Add Perplexity API key for live verification:")
print("  1. Go to: https://www.perplexity.ai/settings/api")
print("  2. Create an API key")
print("  3. Add to your .env file:")
print("     nano ~/legal-tracker/.env")
print("     Add line: PERPLEXITY_API_KEY=your-key-here")
print("  4. Run: npm run research:all -- --force")
print("     (contacts will now be verified with live web search)")
print("")
print("WITHOUT Perplexity key the system still works — just uses")
print("Claude training data only (what you have now)")
