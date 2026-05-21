import os

home = os.path.expanduser("~")
path = os.path.join(home, "legal-tracker", "src", "contactVerifier.js")

content = '''// contactVerifier.js
// Uses Perplexity Sonar API (live web search) to verify contacts are current

import axios from "axios";
import { logger } from "./logger.js";

const PERPLEXITY_KEY = process.env.PERPLEXITY_API_KEY;

export async function verifyContact(contact, accountName) {
  if (!PERPLEXITY_KEY) {
    logger.warn("PERPLEXITY_API_KEY not set — skipping live verification");
    return { ...contact, verified: false, verifiedAt: null };
  }

  const query = "Who is the current " + contact.tag + " at " + accountName + " in 2025 or 2026? Is " + contact.name + " still in this role?";

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

    const answer = response.data && response.data.choices && response.data.choices[0]
      ? response.data.choices[0].message.content
      : "";
    const citations = response.data && response.data.citations ? response.data.citations : [];

    const nameLower = contact.name.toLowerCase();
    const answerLower = answer.toLowerCase();

    let confidence = "Medium";
    let confidence_reason = "Perplexity web search conducted";
    let isCurrent = true;

    const departureSignals = ["left ", "departed", "no longer", "former", "previously", "resigned", "retired", "stepped down", "replaced by"];
    const currentSignals = ["currently", "is the", "serves as", "appointed", "named as", "joined as", "promoted to"];

    const hasDeparture = departureSignals.some(function(s) {
      const idx = answerLower.indexOf(s);
      const nameIdx = answerLower.indexOf(nameLower);
      return idx !== -1 && nameIdx !== -1 && Math.abs(idx - nameIdx) < 150;
    });
    const hasCurrent = currentSignals.some(function(s) { return answerLower.includes(s); });

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
      name: contact.name,
      title: contact.title,
      tag: contact.tag,
      linkedin: contact.linkedin || null,
      email: contact.email || null,
      notes: contact.notes || null,
      confidence: confidence,
      confidence_reason: confidence_reason,
      isCurrent: isCurrent,
      verificationAnswer: answer.slice(0, 300),
      verificationSources: citations.slice(0, 2),
      verifiedAt: new Date().toISOString(),
      verified: true,
    };

  } catch (err) {
    logger.warn("Contact verification failed for " + contact.name + " at " + accountName, { error: err.message });
    return {
      name: contact.name,
      title: contact.title,
      tag: contact.tag,
      linkedin: contact.linkedin || null,
      email: contact.email || null,
      notes: contact.notes || null,
      confidence: contact.confidence || "Medium",
      confidence_reason: "Verification attempted but failed — verify manually on LinkedIn",
      verified: false,
      verifiedAt: null,
    };
  }
}

export async function verifyAccountContacts(account, researchData, forceAll) {
  if (!researchData || !researchData.contacts || !researchData.contacts.length) {
    return researchData;
  }

  const staleThresholdDays = 7;
  const now = Date.now();

  const contactsToVerify = researchData.contacts.filter(function(c) {
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

  const verified = [];
  for (const c of contactsToVerify) {
    const result = await verifyContact(c, account.name);
    verified.push(result);
    await new Promise(function(r) { setTimeout(r, 500); });
  }

  const verifiedMap = new Map(verified.map(function(c) { return [c.name, c]; }));
  researchData.contacts = researchData.contacts.map(function(c) {
    return verifiedMap.has(c.name) ? verifiedMap.get(c.name) : c;
  });

  return researchData;
}
''';

with open(path, 'w') as f:
    f.write(content)
print("Done — contactVerifier.js fixed")

# Also fix researcher.js JSON parsing to handle unterminated strings
researcher_path = os.path.join(os.path.expanduser("~"), "legal-tracker", "src", "researcher.js")
with open(researcher_path, 'r') as f:
    content = f.read()

# Replace the JSON parsing section with a more robust version
old_parse = '''    const cleaned = raw
      .replace(/^```json\\s*/i, '')
      .replace(/^```\\s*/i, '')
      .replace(/```\\s*$/i, '')
      .trim();

    const parsed = JSON.parse(cleaned);'''

new_parse = '''    let cleaned = raw
      .replace(/^```json\\s*/i, '')
      .replace(/^```\\s*/i, '')
      .replace(/```\\s*$/i, '')
      .trim();

    // Attempt to fix truncated JSON by finding the last complete object
    let parsed;
    try {
      parsed = JSON.parse(cleaned);
    } catch (e) {
      // Try to salvage truncated response by finding last valid closing brace
      const lastBrace = cleaned.lastIndexOf('}');
      if (lastBrace > 0) {
        try {
          parsed = JSON.parse(cleaned.slice(0, lastBrace + 1));
          logger.warn(`Truncated JSON recovered for ${account.name}`);
        } catch (e2) {
          throw new Error('JSON parse failed even after truncation recovery: ' + e.message);
        }
      } else {
        throw e;
      }
    }'''

if old_parse in content:
    content = content.replace(old_parse, new_parse)
    with open(researcher_path, 'w') as f:
        f.write(content)
    print("Done — researcher.js updated with robust JSON parsing")
else:
    print("Skipped researcher.js — parse block not found (may already be updated)")

print("")
print("Now test with: npm run research:account \"Microsoft\"")
