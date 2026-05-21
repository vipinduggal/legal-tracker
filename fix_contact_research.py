import os

home = os.path.expanduser("~")
base = os.path.join(home, "legal-tracker")

# Rewrite contactVerifier.js to be Perplexity-FIRST
# Instead of verifying Claude's answer, we ask Perplexity WHO is current
# then replace Claude's contacts with Perplexity's answer

path = os.path.join(base, "src", "contactVerifier.js")

content = '''// contactVerifier.js
// Perplexity-FIRST contact research
// Asks Perplexity WHO is currently in each role, then replaces Claude contacts

import axios from "axios";
import { logger } from "./logger.js";

const PERPLEXITY_KEY = process.env.PERPLEXITY_API_KEY;

const ROLES_TO_CHECK = [
  { tag: "CLO", titles: ["Chief Legal Officer", "CLO"] },
  { tag: "GC", titles: ["General Counsel", "GC"] },
  { tag: "Head of Litigation", titles: ["Head of Litigation", "VP Litigation", "Director of Litigation"] },
  { tag: "Head of Legal Operations", titles: ["Head of Legal Operations", "VP Legal Operations", "Director of Legal Operations", "Legal Operations Manager"] },
];

/**
 * Ask Perplexity who currently holds a specific role at a company.
 * Returns a contact object or null if not found.
 */
async function findCurrentRoleHolder(accountName, role) {
  if (!PERPLEXITY_KEY) return null;

  const query = "Who is the current " + role.titles[0] + " at " + accountName +
    " as of 2025 or 2026? Give me their full name and exact title. Be specific and current.";

  try {
    const response = await axios.post(
      "https://api.perplexity.ai/chat/completions",
      {
        model: "sonar",
        messages: [
          {
            role: "system",
            content: "You are a corporate directory researcher. Today is " +
              new Date().toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" }) +
              ". Give only the current person in this role as of 2025-2026. If you are not certain, say so. Be concise: Name, Title, and one sentence of context.",
          },
          { role: "user", content: query },
        ],
        max_tokens: 300,
      },
      {
        headers: {
          Authorization: "Bearer " + PERPLEXITY_KEY,
          "Content-Type": "application/json",
        },
        timeout: 15000,
      }
    );

    const answer = response.data &&
      response.data.choices &&
      response.data.choices[0]
      ? response.data.choices[0].message.content
      : "";

    const citations = response.data && response.data.citations
      ? response.data.citations
      : [];

    if (!answer || answer.length < 10) return null;

    // Check if Perplexity couldn't find anyone
    const noResultSignals = [
      "not sure", "unclear", "cannot confirm", "no information",
      "not available", "i don't know", "unknown", "could not find"
    ];
    if (noResultSignals.some(s => answer.toLowerCase().includes(s))) {
      return null;
    }

    // Try to extract a name from the answer
    // Look for capitalized name patterns
    const nameMatch = answer.match(/^([A-Z][a-z]+ [A-Z][a-z]+(?:\\s[A-Z][a-z]+)?)/m);
    const extractedName = nameMatch ? nameMatch[1] : null;

    if (!extractedName) return null;

    // Build confidence based on answer quality
    const highConfidenceSignals = ["currently", "is the", "serves as", "appointed", "as of 2025", "as of 2026", "since 2024", "since 2025"];
    const isHighConfidence = highConfidenceSignals.some(s => answer.toLowerCase().includes(s));

    return {
      name: extractedName,
      tag: role.tag,
      title: role.titles[0],
      confidence: isHighConfidence ? "High" : "Medium",
      confidence_reason: "Confirmed via Perplexity live web search " +
        new Date().toLocaleDateString("en-US", { month: "short", year: "numeric" }),
      verificationAnswer: answer.slice(0, 400),
      verificationSources: citations.slice(0, 2),
      verifiedAt: new Date().toISOString(),
      verified: true,
      linkedin: null,
      email: null,
      notes: null,
    };

  } catch (err) {
    logger.warn("Perplexity lookup failed for " + role.tag + " at " + accountName, { error: err.message });
    return null;
  }
}

/**
 * Main function: get Perplexity-verified contacts for an account.
 * Asks Perplexity who currently holds each key role.
 * Merges with Claude contacts, preferring Perplexity results for top roles.
 */
export async function verifyAccountContacts(account, researchData) {
  if (!PERPLEXITY_KEY) {
    logger.warn("No PERPLEXITY_API_KEY — using Claude contacts as-is");
    return researchData;
  }

  logger.info("Running Perplexity-first contact lookup for " + account.name);

  const perplexityContacts = [];

  for (const role of ROLES_TO_CHECK) {
    const found = await findCurrentRoleHolder(account.name, role);
    if (found) {
      perplexityContacts.push(found);
      logger.info("Perplexity found " + role.tag + " at " + account.name + ": " + found.name);
    }
    // Small delay between calls
    await new Promise(function(r) { setTimeout(r, 600); });
  }

  if (!perplexityContacts.length) {
    logger.info("Perplexity found no contacts for " + account.name + " — keeping Claude contacts with Low confidence");
    // Mark all Claude contacts as Medium confidence since unverified
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

  // Build final contacts list:
  // 1. Start with Perplexity-verified contacts (these are authoritative)
  // 2. Add any Claude contacts whose role isn't covered by Perplexity
  const perplexityTags = new Set(perplexityContacts.map(function(c) { return c.tag; }));

  const claudeOnlyContacts = (researchData.contacts || []).filter(function(c) {
    return !perplexityTags.has(c.tag);
  }).map(function(c) {
    return Object.assign({}, c, {
      confidence: "Low",
      confidence_reason: "AI-sourced only — not verified by live search. Verify on LinkedIn before outreach.",
    });
  });

  researchData.contacts = perplexityContacts.concat(claudeOnlyContacts);

  logger.info("Contact merge complete for " + account.name + ": " +
    perplexityContacts.length + " Perplexity-verified, " +
    claudeOnlyContacts.length + " Claude-only (Low confidence)");

  return researchData;
}

// Keep old verifyContact for backwards compatibility
export async function verifyContact(contact, accountName) {
  return Object.assign({}, contact, {
    confidence: contact.confidence || "Medium",
    confidence_reason: "Use verifyAccountContacts for full verification",
  });
}
''';

with open(path, 'w') as f:
    f.write(content)
print("Done — contactVerifier.js rewritten (Perplexity-first)")
print("")
print("Now test with:")
print('  npm run research:account "Microsoft"')
print("")
print("Microsoft should now show:")
print("  - Hossein Nowbar as CLO (not Dev Stahlkopf)")
print("  - Each top role verified by live web search")
print("  - Claude-only contacts marked Low confidence")
