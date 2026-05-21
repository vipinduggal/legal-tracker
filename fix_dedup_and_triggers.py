import os

home = os.path.expanduser("~")
base = os.path.join(home, "legal-tracker")
verifier_path = os.path.join(base, "src", "contactVerifier.js")

with open(verifier_path, 'r') as f:
    content = f.read()

# ── Fix 1: Deduplicate Perplexity contacts by name ────────
# Ava Hahn is appearing as CLO, GC, Deputy GC, Head of Litigation, Head of Corporate
# because Perplexity returns her for any role it finds her associated with
# Fix: after collecting all Perplexity contacts, deduplicate by name
# keeping the most senior/specific role

old_merge = '''  if (!perplexityContacts.length) {
    logger.info("Perplexity found no contacts for " + account.name + " — keeping Claude contacts with Low confidence");
    if (researchData.contacts) {
      researchData.contacts = researchData.contacts.map(function(c) {
        return Object.assign({}, c, {
          confidence: c.confidence || "Medium",
          confidence_reason: c.confidence_reason || "AI-sourced — verify on LinkedIn before outreach",
        });
      });
    }
    return researchData;
  }

  // Merge Perplexity contacts with existing Claude contacts'''

new_merge = '''  if (!perplexityContacts.length) {
    logger.info("Perplexity found no contacts for " + account.name + " — keeping Claude contacts with Low confidence");
    if (researchData.contacts) {
      researchData.contacts = researchData.contacts.map(function(c) {
        return Object.assign({}, c, {
          confidence: c.confidence || "Medium",
          confidence_reason: c.confidence_reason || "AI-sourced — verify on LinkedIn before outreach",
        });
      });
    }
    return researchData;
  }

  // Deduplicate Perplexity contacts by name — keep most senior role per person
  // This prevents one person appearing under multiple role tags
  const roleRank = {
    "CLO": 14, "GC": 13, "Deputy GC": 12, "Associate GC": 11,
    "Head of Litigation": 10, "Head of Legal Operations": 9,
    "Head of Employment": 8, "Head of IP": 7, "Head of Privacy": 6,
    "Head of Compliance": 5, "Head of Regulatory": 4, "Head of Corporate": 3,
    "CEO": 13, "CFO": 12, "COO": 11, "CISO": 10,
    "Litigator": 2, "Other Legal": 1,
  };

  const dedupedPerplexity = [];
  const perplexityByName = new Map();

  for (const c of perplexityContacts) {
    const nameKey = normalizeName(c.name);
    if (!nameKey || nameKey.length < 3) continue;

    if (!perplexityByName.has(nameKey)) {
      perplexityByName.set(nameKey, c);
    } else {
      // Keep the more senior role for this person
      const existing = perplexityByName.get(nameKey);
      const existingRank = roleRank[existing.tag] || 0;
      const newRank = roleRank[c.tag] || 0;
      if (newRank > existingRank) {
        perplexityByName.set(nameKey, c);
      }
    }
  }

  const uniquePerplexityContacts = Array.from(perplexityByName.values());
  logger.info("Perplexity contacts after name dedup: " + uniquePerplexityContacts.length + " unique people (was " + perplexityContacts.length + ")");

  // Merge Perplexity contacts with existing Claude contacts'''

# Also update the merge section to use uniquePerplexityContacts
old_merge_use = '''  // Build final contacts list:
  // 1. Start with Perplexity-verified contacts (these are authoritative)
  // 2. Add any Claude contacts whose role isn't covered by Perplexity
  const perplexityTags = new Set(perplexityContacts.map(function(c) { return c.tag; }));
  const perplexityNames = new Set(perplexityContacts.map(function(c) { return normalizeName(c.name); }));

  // Keep Claude contacts not covered by Perplexity AND not already found by Perplexity
  const claudeOnlyContacts = (researchData.contacts || []).filter(function(c) {
    const nameNorm = normalizeName(c.name);
    // Skip if Perplexity already found this person by name
    if (perplexityNames.has(nameNorm)) return false;
    // Keep if it's a role Perplexity didn't cover
    return !perplexityTags.has(c.tag);
  }).map(function(c) {
    return Object.assign({}, c, {
      confidence: "Low",
      confidence_reason: "AI-sourced only — not verified by live search. Verify on LinkedIn before outreach.",
    });
  });

  // Combine and deduplicate one final time
  const combined = [...perplexityContacts, ...claudeOnlyContacts];
  researchData.contacts = deduplicateContacts(combined);

  logger.info("Contact merge complete for " + account.name + ": " +
    perplexityContacts.length + " Perplexity-verified, " +
    claudeOnlyContacts.length + " Claude-only (Low confidence), " +
    researchData.contacts.length + " total after dedup");'''

new_merge_use = '''  // Build final contacts list using deduplicated Perplexity contacts
  const perplexityTags = new Set(uniquePerplexityContacts.map(function(c) { return c.tag; }));
  const perplexityNames = new Set(uniquePerplexityContacts.map(function(c) { return normalizeName(c.name); }));

  // Keep Claude contacts not covered by Perplexity AND not already found by Perplexity
  const claudeOnlyContacts = (researchData.contacts || []).filter(function(c) {
    const nameNorm = normalizeName(c.name);
    if (perplexityNames.has(nameNorm)) return false;
    return !perplexityTags.has(c.tag);
  }).map(function(c) {
    return Object.assign({}, c, {
      confidence: "Low",
      confidence_reason: "AI-sourced only — not verified by live search. Verify on LinkedIn before outreach.",
    });
  });

  // Combine and deduplicate one final time
  const combined = [...uniquePerplexityContacts, ...claudeOnlyContacts];
  researchData.contacts = deduplicateContacts(combined);

  logger.info("Contact merge complete for " + account.name + ": " +
    uniquePerplexityContacts.length + " Perplexity-verified (unique), " +
    claudeOnlyContacts.length + " Claude-only (Low confidence), " +
    researchData.contacts.length + " total after dedup");'''

if old_merge in content:
    content = content.replace(old_merge, new_merge)
    print("Done — Perplexity contact dedup added")
else:
    print("WARNING — merge pattern not found")

if old_merge_use in content:
    content = content.replace(old_merge_use, new_merge_use)
    print("Done — merge updated to use deduplicated contacts")
else:
    print("WARNING — merge use pattern not found")

# ── Fix 2: Improve force extraction prompt to get both categories ──
old_force = '''      const forcePrompt = `Based on this intelligence about ${account.name}, write 2-3 specific sales triggers for a legal services company (Consilio) selling eDiscovery, document review, flex legal talent, and outside counsel advisory.

INTELLIGENCE:
${perplexityAnswer.slice(0, 2000)}

For each trigger, write ONE sentence describing: what happened, when it happened, and why it creates a need for legal services.
Use this exact JSON format:
{
  "immediate_triggers": [{"trigger": "...", "date": "...", "sales_implication": "...", "urgency": "High"}],
  "strategic_triggers": [{"trigger": "...", "timeframe": "...", "sales_implication": "...", "angle": "..."}],
  "financial_intel": {"latest_filing": null, "cost_initiatives": null, "earnings_signals": null, "ma_activity": null},
  "intelligence_quality": "Medium"
}`;'''

new_force = '''      const forcePrompt = `You sell legal services (eDiscovery, document review, ALSP, flex legal talent, outside counsel advisory) to corporate legal departments.

Read this intelligence about ${account.name} and identify:
1. IMMEDIATE triggers — specific events in the last 90 days that create an URGENT need for legal services RIGHT NOW (litigation filed, regulatory action, cost-cutting pressure, new GC hired)
2. STRATEGIC triggers — trends in the last 6 months that shape a longer-term sales approach

INTELLIGENCE GATHERED TODAY:
${perplexityAnswer.slice(0, 3000)}

Be specific. Reference actual events, dates, and dollar amounts from the intelligence above.
If you see any lawsuit, patent dispute, regulatory action, export control issue, earnings loss contingency, M&A deal, or rapid growth — those are immediate triggers.
If you see sustained litigation, business expansion, cost pressure trends, or leadership changes — those are strategic triggers.

Return JSON only:
{
  "immediate_triggers": [
    {"trigger": "specific event with date", "date": "month year", "sales_implication": "what Consilio service this needs and why now", "urgency": "Critical or High or Medium"}
  ],
  "strategic_triggers": [
    {"trigger": "trend with timeframe", "timeframe": "e.g. Q4 2025 to present", "sales_implication": "how to position over next quarter", "angle": "which Consilio service to lead with"}
  ],
  "financial_intel": {
    "latest_filing": "most recent earnings period if mentioned, else null",
    "cost_initiatives": "any cost reduction program with specifics, else null",
    "earnings_signals": "what was said about costs or legal on earnings call, else null",
    "ma_activity": "any M&A deal mentioned, else null"
  },
  "intelligence_quality": "High or Medium or Low"
}`;'''

if old_force in content:
    content = content.replace(old_force, new_force)
    print("Done — force extraction prompt improved")
else:
    print("WARNING — force prompt pattern not found")

with open(verifier_path, 'w') as f:
    f.write(content)

print("")
print("Run: npm run research:account \"AMD\"")
print("Expect: no duplicate contacts, 2-3 immediate triggers including")
print("  - Adeia patent lawsuit Nov 2025")
print("  - Q1 2026 loss contingency")
print("  - China export controls")
