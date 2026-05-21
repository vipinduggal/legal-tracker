import Anthropic from "@anthropic-ai/sdk";
import { buildResearchPromptA, buildResearchPromptB } from "./prompts.js";
import { verifyAccountContacts, getLiveIntelligence } from "./contactVerifier.js";
import { logger } from "./logger.js";

const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
const MAX_RETRIES = 3;
const MAX_TOKENS = 4096;

function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}

function cleanJSON(resp) {
  return resp.content
    .filter(b => b.type === "text")
    .map(b => b.text)
    .join("")
    .replace(/^```json\s*/i, "")
    .replace(/^```\s*/i, "")
    .replace(/```\s*$/i, "")
    .trim();
}

function parseHalf(raw, label, accountName) {
  try {
    return JSON.parse(raw);
  } catch (e) {
    // Recovery: find last complete closing brace
    const lastBrace = raw.lastIndexOf("}");
    if (lastBrace > 0) {
      try {
        return JSON.parse(raw.slice(0, lastBrace + 1));
      } catch (e2) {}
    }
    logger.warn(`${label} parse failed for ${accountName}: ${e.message}`);
    return {};
  }
}

/**
 * Research a single account using two parallel Claude calls.
 * Call A: contacts, tech, counsel, alsp, flex
 * Call B: litigation, regulatory, financial, personnel, triggers
 * Results are merged into one complete object.
 */
export async function researchAccount(account, retries = 0) {
  try {
    logger.info(`Researching: ${account.name}`, { id: account.id });

    const promptA = buildResearchPromptA(account);
    const promptB = buildResearchPromptB(account);

    // Run both prompts in parallel — each is small enough to never truncate
    const [responseA, responseB] = await Promise.all([
      client.messages.create({
        model: "claude-sonnet-4-5",
        max_tokens: MAX_TOKENS,
        messages: [{ role: "user", content: promptA }],
      }),
      client.messages.create({
        model: "claude-sonnet-4-5",
        max_tokens: MAX_TOKENS,
        messages: [{ role: "user", content: promptB }],
      }),
    ]);

    const parsedA = parseHalf(cleanJSON(responseA), "Part A (contacts/tech)", account.name);
    const parsedB = parseHalf(cleanJSON(responseB), "Part B (litigation/financial)", account.name);

    // Merge both halves
    let parsed = { ...parsedA, ...parsedB };

    // Ensure required arrays exist
    parsed.contacts = parsed.contacts || [];
    parsed.tech = parsed.tech || [];
    parsed.counsel = parsed.counsel || [];
    parsed.alsp = parsed.alsp || [];
    parsed.flex = parsed.flex || [];
    parsed.litigation = parsed.litigation || [];
    parsed.regulatory = parsed.regulatory || [];
    parsed.financial_intel = parsed.financial_intel || {};
    parsed.personnel_changes = parsed.personnel_changes || [];
    parsed.sales_triggers = parsed.sales_triggers || [];

    // Step 2: Verify contacts and get live intelligence via Perplexity
    if (process.env.PERPLEXITY_API_KEY) {
      parsed = await verifyAccountContacts(account, parsed);

      const liveIntel = await getLiveIntelligence(account);
      if (liveIntel) {
        // Apply structured immediate triggers
        const immediateTrigs = (liveIntel.immediate_triggers || []).map(t =>
          `IMMEDIATE [${t.urgency}] [${t.date}] ${t.trigger} — ${t.sales_implication}`
        );
        const strategicTrigs = (liveIntel.strategic_triggers || []).map(t =>
          `STRATEGIC [${t.timeframe}] ${t.trigger} — ${t.sales_implication}`
        );

        parsed.sales_triggers = [...immediateTrigs, ...strategicTrigs];
        parsed.immediate_triggers = liveIntel.immediate_triggers || [];
        parsed.strategic_triggers = liveIntel.strategic_triggers || [];
        parsed.intelligence_quality = liveIntel.intelligence_quality;
        parsed.intelligence_date = liveIntel.intelligence_date;
        parsed.live_intel_retrieved = liveIntel.retrievedAt;
        parsed.live_intel_sources = liveIntel.sources || [];

        // Apply open roles
        if (liveIntel.open_roles && liveIntel.open_roles.length) {
          parsed.open_roles = liveIntel.open_roles;
        }

        // Override financial intel with live data
        if (liveIntel.financial_intel) {
          const fi = liveIntel.financial_intel;
          if (fi.earnings_signals) parsed.financial_intel.earnings_signals = fi.earnings_signals;
          if (fi.cost_initiatives) parsed.financial_intel.cost_initiatives = fi.cost_initiatives;
          if (fi.ma_activity) parsed.financial_intel.ma_activity = fi.ma_activity;
          if (fi.latest_filing) parsed.financial_intel.latest_filing = fi.latest_filing;
        }

        // Filter out stale personnel changes (older than 2025)
        if (parsed.personnel_changes) {
          parsed.personnel_changes = parsed.personnel_changes.filter(p => {
            const text = (p.change || "") + (p.name || "");
            const has2025 = text.includes("2025") || text.includes("2026");
            const hasOld = text.includes("2023") || text.includes("2024") || text.includes("2022");
            return has2025 || !hasOld;
          });
        }

        const iCount = (liveIntel.immediate_triggers || []).length;
        const sCount = (liveIntel.strategic_triggers || []).length;
        const rCount = (liveIntel.open_roles || []).length;
        logger.info(`Live triggers applied for ${account.name}: ${iCount} immediate, ${sCount} strategic, ${rCount} open roles (${liveIntel.intelligence_quality} quality)`);
      }
    }

    logger.info(`\u2713 Researched: ${account.name}`, {
      contacts: parsed.contacts.length,
      litigation: (parsed.litigation || []).length,
      regulatory: (parsed.regulatory || []).length,
    });

    return parsed;

  } catch (err) {
    if (retries < MAX_RETRIES - 1) {
      const delay = Math.pow(2, retries) * 2000;
      logger.warn(`Retry ${retries + 1}/${MAX_RETRIES} for ${account.name} in ${delay}ms`, { error: err.message });
      await sleep(delay);
      return researchAccount(account, retries + 1);
    }
    logger.error(`Failed to research ${account.name} after ${MAX_RETRIES} attempts`, { error: err.message });
    return null;
  }
}

/**
 * Detect changes between old and new research data.
 */
export function detectChanges(oldData, newData) {
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
}
