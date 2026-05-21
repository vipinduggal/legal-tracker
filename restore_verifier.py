import os

home = os.path.expanduser("~")
path = os.path.join(home, "legal-tracker", "src", "contactVerifier.js")

content = r'''// contactVerifier.js
// Perplexity-first contact verification + live intelligence
// Uses 4 focused searches: litigation, financial, business, open roles

import axios from "axios";
import { logger } from "./logger.js";

const PERPLEXITY_KEY = process.env.PERPLEXITY_API_KEY;

const ROLES_TO_CHECK = [
  { tag: "CLO", titles: ["Chief Legal Officer", "CLO"] },
  { tag: "GC", titles: ["General Counsel", "GC"] },
  { tag: "Deputy GC", titles: ["Deputy General Counsel", "Associate General Counsel"] },
  { tag: "Head of Litigation", titles: ["Head of Litigation", "VP Litigation", "Chief Litigation Counsel"] },
  { tag: "Head of Legal Operations", titles: ["Head of Legal Operations", "VP Legal Operations", "Director of Legal Operations"] },
  { tag: "Head of Employment", titles: ["Head of Employment Law", "Chief Employment Counsel"] },
  { tag: "Head of IP", titles: ["Head of Intellectual Property", "Chief IP Counsel", "VP Intellectual Property"] },
  { tag: "Head of Privacy", titles: ["Chief Privacy Officer", "Head of Privacy", "Data Protection Officer"] },
  { tag: "Head of Compliance", titles: ["Chief Compliance Officer", "Head of Compliance", "Chief Ethics and Compliance Officer"] },
  { tag: "Head of Regulatory", titles: ["Head of Regulatory Affairs", "VP Regulatory", "Chief Regulatory Counsel"] },
  { tag: "Head of Corporate", titles: ["Head of Corporate Law", "VP Corporate", "Chief Corporate Counsel"] },
  { tag: "CEO", titles: ["Chief Executive Officer", "CEO"] },
  { tag: "CFO", titles: ["Chief Financial Officer", "CFO"] },
  { tag: "COO", titles: ["Chief Operating Officer", "COO"] },
];

const ROLE_RANK = {
  "CLO": 14, "GC": 13, "Deputy GC": 12, "Associate GC": 11,
  "Head of Litigation": 10, "Head of Legal Operations": 9,
  "Head of Employment": 8, "Head of IP": 7, "Head of Privacy": 6,
  "Head of Compliance": 5, "Head of Regulatory": 4, "Head of Corporate": 3,
  "CEO": 13, "CFO": 12, "COO": 11, "CISO": 10,
  "Litigator": 2, "Other Legal": 1,
};

function normalizeName(name) {
  return (name || "").toLowerCase().replace(/[^a-z\s]/g, "").replace(/\s+/g, " ").trim();
}

function deduplicateContacts(contacts) {
  const seen = new Map();
  for (const c of contacts) {
    const key = normalizeName(c.name);
    if (!key || key.length < 3) continue;
    if (!seen.has(key)) {
      seen.set(key, c);
    } else {
      const existing = seen.get(key);
      const existRank = ROLE_RANK[existing.tag] || 0;
      const newRank = ROLE_RANK[c.tag] || 0;
      if (newRank > existRank) {
        seen.set(key, { ...c, linkedin: c.linkedin || existing.linkedin, email: c.email || existing.email });
      } else {
        seen.set(key, { ...existing, linkedin: existing.linkedin || c.linkedin, email: existing.email || c.email });
      }
    }
  }
  return Array.from(seen.values());
}

async function perplexityCall(systemPrompt, userQuery, maxTokens = 600) {
  const response = await axios.post(
    "https://api.perplexity.ai/chat/completions",
    {
      model: "sonar",
      messages: [
        { role: "system", content: systemPrompt },
        { role: "user", content: userQuery },
      ],
      max_tokens: maxTokens,
    },
    {
      headers: { Authorization: "Bearer " + PERPLEXITY_KEY, "Content-Type": "application/json" },
      timeout: 20000,
    }
  );
  return {
    answer: response.data?.choices?.[0]?.message?.content || "",
    citations: response.data?.citations || [],
  };
}

async function findCurrentRoleHolder(accountName, role) {
  if (!PERPLEXITY_KEY) return null;
  try {
    const { answer } = await perplexityCall(
      `You are a corporate directory researcher. Today is ${new Date().toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" })}. Give only the current person in this role as of 2025-2026. Be concise: Name, Title, one sentence of context.`,
      `Who is the current ${role.titles[0]} at ${accountName} as of 2025 or 2026? Give their full name and exact title.`,
      300
    );
    if (!answer || answer.length < 10) return null;
    const noResultSignals = ["not sure", "unclear", "cannot confirm", "no information", "not available", "i don't know", "unknown", "could not find"];
    if (noResultSignals.some(s => answer.toLowerCase().includes(s))) return null;
    const nameMatch = answer.match(/^([A-Z][a-z]+ [A-Z][a-z]+(?:\s[A-Z][a-z]+)?)/m);
    if (!nameMatch) return null;
    const highConfidenceSignals = ["currently", "is the", "serves as", "appointed", "as of 2025", "as of 2026", "since 2024", "since 2025"];
    const isHigh = highConfidenceSignals.some(s => answer.toLowerCase().includes(s));
    return {
      name: nameMatch[1],
      tag: role.tag,
      title: role.titles[0],
      confidence: isHigh ? "High" : "Medium",
      confidence_reason: `Confirmed via Perplexity live search ${new Date().toLocaleDateString("en-US", { month: "short", year: "numeric" })}`,
      verifiedAt: new Date().toISOString(),
      verified: true,
      linkedin: null,
      email: null,
      notes: null,
    };
  } catch (err) {
    return null;
  }
}

export async function verifyAccountContacts(account, researchData) {
  if (!researchData) return researchData;

  // Always deduplicate first
  if (researchData.contacts && researchData.contacts.length) {
    const before = researchData.contacts.length;
    researchData.contacts = deduplicateContacts(researchData.contacts);
    const after = researchData.contacts.length;
    if (before !== after) logger.info(`Dedup removed ${before - after} duplicate contacts for ${account.name}`);
  }

  if (!PERPLEXITY_KEY) return researchData;

  logger.info(`Running Perplexity-first contact lookup for ${account.name}`);
  const perplexityContacts = [];

  for (const role of ROLES_TO_CHECK) {
    const found = await findCurrentRoleHolder(account.name, role);
    if (found) {
      perplexityContacts.push(found);
      logger.info(`Perplexity found ${role.tag} at ${account.name}: ${found.name}`);
    }
    await new Promise(r => setTimeout(r, 400));
  }

  if (!perplexityContacts.length) {
    if (researchData.contacts) {
      researchData.contacts = researchData.contacts.map(c => ({
        ...c,
        confidence: c.confidence || "Medium",
        confidence_reason: c.confidence_reason || "AI-sourced — verify on LinkedIn before outreach",
      }));
    }
    return researchData;
  }

  // Deduplicate Perplexity contacts by name — keep most senior role per person
  const perplexityByName = new Map();
  for (const c of perplexityContacts) {
    const key = normalizeName(c.name);
    if (!key || key.length < 3) continue;
    if (!perplexityByName.has(key)) {
      perplexityByName.set(key, c);
    } else {
      const existing = perplexityByName.get(key);
      if ((ROLE_RANK[c.tag] || 0) > (ROLE_RANK[existing.tag] || 0)) {
        perplexityByName.set(key, c);
      }
    }
  }
  const uniquePerplexity = Array.from(perplexityByName.values());
  logger.info(`Perplexity contacts after dedup: ${uniquePerplexity.length} unique (was ${perplexityContacts.length})`);

  const perplexityTags = new Set(uniquePerplexity.map(c => c.tag));
  const perplexityNames = new Set(uniquePerplexity.map(c => normalizeName(c.name)));

  const claudeOnly = (researchData.contacts || []).filter(c => {
    if (perplexityNames.has(normalizeName(c.name))) return false;
    return !perplexityTags.has(c.tag);
  }).map(c => ({
    ...c,
    confidence: "Low",
    confidence_reason: "AI-sourced only — verify on LinkedIn before outreach",
  }));

  researchData.contacts = deduplicateContacts([...uniquePerplexity, ...claudeOnly]);
  logger.info(`Contact merge for ${account.name}: ${uniquePerplexity.length} Perplexity + ${claudeOnly.length} Claude-only = ${researchData.contacts.length} total`);
  return researchData;
}

export async function getLiveIntelligence(account) {
  if (!PERPLEXITY_KEY) return null;

  const today = new Date();
  const todayStr = today.toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" });
  const sixMonthsAgo = new Date(today);
  sixMonthsAgo.setMonth(sixMonthsAgo.getMonth() - 6);
  const sixMonthsAgoStr = sixMonthsAgo.toLocaleDateString("en-US", { year: "numeric", month: "long" });
  const sysPrompt = `You are a legal intelligence researcher. Today is ${todayStr}. Only report information from ${sixMonthsAgoStr} to today. Be specific with dates and facts.`;

  // Run 4 focused searches in parallel
  const [litResult, finResult, bizResult, rolesResult] = await Promise.allSettled([
    perplexityCall(sysPrompt,
      `What lawsuits, patent cases, class actions, or regulatory investigations involve ${account.name} in ${sixMonthsAgoStr} to ${todayStr}? Include case names, filing dates, courts, dollar amounts.`,
      700),
    perplexityCall(sysPrompt,
      `What did ${account.name} report in Q1 2026 or Q4 2025 earnings? Any legal reserves, loss contingencies, restructuring charges, cost cuts? Specific dollar amounts and dates.`,
      700),
    perplexityCall(sysPrompt,
      `What major business changes has ${account.name} announced in ${sixMonthsAgoStr} to ${todayStr}? Acquisitions, export controls, China restrictions, leadership changes in legal or compliance roles?`,
      700),
    perplexityCall(sysPrompt,
      `What legal department job openings does ${account.name} currently have posted as of ${todayStr}? Search LinkedIn Jobs, company careers page, Indeed. Look for: attorney, counsel, paralegal, compliance, eDiscovery, legal operations, privacy, regulatory, contract manager. List each role title, when posted, and location.`,
      700),
  ]);

  // Combine all answers
  const sections = [];
  let allCitations = [];

  if (litResult.status === "fulfilled" && litResult.value.answer.length > 30) {
    sections.push("=== LITIGATION ===\n" + litResult.value.answer);
    allCitations = [...allCitations, ...litResult.value.citations];
    logger.info(`Perplexity litigation search complete for ${account.name} (${litResult.value.answer.length} chars)`);
  }
  if (finResult.status === "fulfilled" && finResult.value.answer.length > 30) {
    sections.push("=== FINANCIAL ===\n" + finResult.value.answer);
    allCitations = [...allCitations, ...finResult.value.citations];
    logger.info(`Perplexity financial search complete for ${account.name} (${finResult.value.answer.length} chars)`);
  }
  if (bizResult.status === "fulfilled" && bizResult.value.answer.length > 30) {
    sections.push("=== BUSINESS ===\n" + bizResult.value.answer);
    allCitations = [...allCitations, ...bizResult.value.citations];
    logger.info(`Perplexity business search complete for ${account.name} (${bizResult.value.answer.length} chars)`);
  }
  if (rolesResult.status === "fulfilled" && rolesResult.value.answer.length > 30) {
    sections.push("=== OPEN_ROLES ===\n" + rolesResult.value.answer);
    logger.info(`Perplexity open roles search complete for ${account.name} (${rolesResult.value.answer.length} chars)`);
  }

  if (!sections.length) {
    logger.warn(`Perplexity found no intelligence for ${account.name}`);
    return null;
  }

  const combinedAnswer = sections.join("\n\n");
  logger.info(`Combined Perplexity intelligence for ${account.name}: ${combinedAnswer.length} chars`);

  // Use Anthropic to structure triggers and open roles
  try {
    const Anthropic = (await import("@anthropic-ai/sdk")).default;
    const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

    // Run 3 parallel Claude structuring calls — each small enough to never truncate
    const [immResp, stratResp, rolesResp] = await Promise.allSettled([
      client.messages.create({
        model: "claude-sonnet-4-5",
        max_tokens: 1500,
        messages: [{ role: "user", content: `You sell legal services (eDiscovery, document review, ALSP, flex legal talent) to corporate legal departments.

Read this intelligence about ${account.name} and identify IMMEDIATE sales triggers — specific events from the last 90 days creating urgent need for legal services RIGHT NOW. Look for: new lawsuits, regulatory actions, loss contingencies, cost cuts, new GC/CLO hired, export controls, M&A.

INTELLIGENCE:
${combinedAnswer.slice(0, 2500)}

Return JSON array only:
[{"trigger":"specific event with details","date":"month year","sales_implication":"which service and why urgent","urgency":"Critical or High or Medium"}]
If none found return: []` }],
      }),
      client.messages.create({
        model: "claude-sonnet-4-5",
        max_tokens: 1500,
        messages: [{ role: "user", content: `You sell legal services (eDiscovery, document review, ALSP, flex legal talent) to corporate legal departments.

Read this intelligence about ${account.name} and identify STRATEGIC trends — patterns from the last 6 months shaping longer-term sales approach. Look for: sustained litigation, M&A integration, rapid growth, sustained regulatory pressure.

INTELLIGENCE:
${combinedAnswer.slice(0, 2500)}

Return JSON array only:
[{"trigger":"trend with timeframe","timeframe":"specific period","sales_implication":"how to position over next quarter","angle":"which service to lead with"}]
If none found return: []` }],
      }),
      client.messages.create({
        model: "claude-sonnet-4-5",
        max_tokens: 1000,
        messages: [{ role: "user", content: `Extract open legal job roles from this text about ${account.name}.

TEXT:
${rolesResult.status === "fulfilled" ? rolesResult.value.answer : "No roles data available"}

Return JSON array only:
[{"title":"exact job title","posted":"when posted or null","location":"city or Remote or null","signal":"one sentence on what this hiring need means for legal services sales"}]
If no roles found return: []

Also extract financial intel as a second JSON object on a new line:
{"latest_filing":"most recent earnings period or null","cost_initiatives":"cost reduction program with dollar amount or null","earnings_signals":"earnings call comment about costs/legal or null","ma_activity":"M&A deal or null"}` }],
      }),
    ]);

    const parseArr = (result) => {
      if (result.status !== "fulfilled") return [];
      const raw = result.value.content.filter(b => b.type === "text").map(b => b.text).join("")
        .replace(/^```json\s*/i, "").replace(/^```\s*/i, "").replace(/```\s*$/i, "").trim();
      try { const p = JSON.parse(raw); return Array.isArray(p) ? p : []; }
      catch(e) {
        const lb = raw.lastIndexOf("}"); 
        if (lb > 0) { try { const p = JSON.parse(raw.slice(0, lb+1)+"]"); return Array.isArray(p) ? p : []; } catch(e2) {} }
        return [];
      }
    };

    const immediateTrigs = parseArr(immResp);
    const strategicTrigs = parseArr(stratResp);

    // Parse roles and financial from combined response
    let openRoles = [];
    let financialIntel = {};
    if (rolesResp.status === "fulfilled") {
      const raw = rolesResp.value.content.filter(b => b.type === "text").map(b => b.text).join("")
        .replace(/^```json\s*/i, "").replace(/^```\s*/i, "").replace(/```\s*$/i, "").trim();
      // Try to parse two JSON objects separated by newline
      const parts = raw.split(/\n(?=\{)/);
      for (const part of parts) {
        const trimmed = part.trim();
        try {
          const parsed = JSON.parse(trimmed);
          if (Array.isArray(parsed)) {
            openRoles = parsed;
            if (openRoles.length) logger.info(`Open roles found for ${account.name}: ${openRoles.length}`);
          } else if (parsed && typeof parsed === "object") {
            financialIntel = parsed;
          }
        } catch(e) {}
      }
    }

    const quality = (immediateTrigs.length + strategicTrigs.length) >= 3 ? "High"
      : (immediateTrigs.length + strategicTrigs.length) >= 1 ? "Medium" : "Low";

    logger.info(`Structured triggers for ${account.name}: ${immediateTrigs.length} immediate, ${strategicTrigs.length} strategic, ${openRoles.length} open roles (${quality})`);

    return {
      immediate_triggers: immediateTrigs,
      strategic_triggers: strategicTrigs,
      open_roles: openRoles,
      financial_intel: financialIntel,
      intelligence_date: todayStr,
      intelligence_quality: quality,
      sources: allCitations.slice(0, 3),
      retrievedAt: new Date().toISOString(),
    };

  } catch (err) {
    logger.warn(`Claude structuring failed for ${account.name}: ${err.message}`);
    return {
      immediate_triggers: [],
      strategic_triggers: [],
      open_roles: [],
      financial_intel: {},
      intelligence_date: todayStr,
      intelligence_quality: "Low",
      sources: allCitations.slice(0, 3),
      retrievedAt: new Date().toISOString(),
    };
  }
}

export async function verifyContact(contact, accountName) {
  return { ...contact, confidence: contact.confidence || "Medium" };
}
'''

with open(path, 'w') as f:
    f.write(content)

print("Done — contactVerifier.js fully restored")
print("File size:", os.path.getsize(path), "bytes")
print("")
print("Test: npm run research:account \"Microsoft\"")
print("Watch for:")
print("  [info] Perplexity open roles search complete for Microsoft")
print("  [info] Open roles found for Microsoft: X")
print("  [info] Live triggers applied: X immediate, Y strategic, Z open roles")
