import os

home = os.path.expanduser("~")
base = os.path.join(home, "legal-tracker")

# ── Step 1: Add live intelligence to contactVerifier.js ───
verifier_path = os.path.join(base, "src", "contactVerifier.js")

with open(verifier_path, 'r') as f:
    verifier_content = f.read()

# Add live intel function at the end
live_intel_function = '''
/**
 * Use Perplexity to get LIVE sales triggers and financial intel for an account.
 * Replaces Claude training-data triggers with current web-sourced intelligence.
 */
export async function getLiveIntelligence(account) {
  if (!PERPLEXITY_KEY) {
    logger.warn("No PERPLEXITY_API_KEY — skipping live intelligence");
    return null;
  }

  const today = new Date().toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" });
  const thisYear = new Date().getFullYear();
  const lastYear = thisYear - 1;

  const query = `Today is ${today}. For ${account.name} (${account.industry}), find the most current information available from ${lastYear}-${thisYear} only:

1. What did ${account.name} say about legal costs, litigation, or regulatory issues on their most recent earnings call or in their most recent 10-K or 10-Q filing?
2. Are there any new lawsuits, regulatory investigations, or government actions involving ${account.name} filed or announced in the last 90 days?
3. Has ${account.name} announced any cost reduction programs, restructuring, layoffs, or efficiency initiatives in ${lastYear} or ${thisYear}?
4. Has there been any M&A activity (acquisitions, mergers, divestitures) involving ${account.name} in the last 12 months?
5. Has ${account.name} had any senior legal leadership changes (CLO, GC, Head of Legal Ops) in ${lastYear} or ${thisYear}?

Be specific. Include dates, dollar amounts, and names where known. Only include information from ${lastYear}-${thisYear}. If you cannot find current information for a question, say "No current data found."`;

  try {
    const response = await axios.post(
      "https://api.perplexity.ai/chat/completions",
      {
        model: "sonar",
        messages: [
          {
            role: "system",
            content: `You are a legal intelligence researcher. Today is ${today}. Only report information from ${lastYear} or ${thisYear}. Be specific with dates and amounts. Do not reference anything older than ${lastYear}.`,
          },
          { role: "user", content: query },
        ],
        max_tokens: 1000,
      },
      {
        headers: {
          Authorization: "Bearer " + PERPLEXITY_KEY,
          "Content-Type": "application/json",
        },
        timeout: 20000,
      }
    );

    const answer = response.data?.choices?.[0]?.message?.content || "";
    const citations = response.data?.citations || [];

    if (!answer || answer.length < 50) return null;

    // Parse the answer into structured intelligence
    const intel = parseLiveIntel(answer, account.name, thisYear, lastYear);
    intel.sources = citations.slice(0, 3);
    intel.retrievedAt = new Date().toISOString();
    intel.rawAnswer = answer.slice(0, 800);

    logger.info("Live intel retrieved for " + account.name + " — " + intel.triggers.length + " triggers found");
    return intel;

  } catch (err) {
    logger.warn("Live intel failed for " + account.name, { error: err.message });
    return null;
  }
}

function parseLiveIntel(answer, accountName, thisYear, lastYear) {
  const answerLower = answer.toLowerCase();
  const triggers = [];
  const financialIntel = {};

  // Extract earnings/filing signals
  const earningsSignals = [
    "earnings call", "10-k", "10-q", "annual report", "quarterly report",
    "disclosed", "reported", "cited", "mentioned", "announced"
  ];
  if (earningsSignals.some(s => answerLower.includes(s))) {
    // Extract relevant sentences
    const sentences = answer.split(/[.!?]+/).filter(s => s.trim().length > 20);
    const earningsSentences = sentences.filter(s =>
      earningsSignals.some(sig => s.toLowerCase().includes(sig)) &&
      (s.includes(String(thisYear)) || s.includes(String(lastYear)))
    );
    if (earningsSentences.length > 0) {
      financialIntel.earnings_signals = earningsSentences.slice(0, 2).join(". ").trim();
    }
  }

  // Extract cost/restructuring signals
  const costSignals = ["cost reduction", "restructuring", "layoff", "efficiency", "headcount", "billion", "million"];
  if (costSignals.some(s => answerLower.includes(s))) {
    const sentences = answer.split(/[.!?]+/).filter(s => s.trim().length > 20);
    const costSentences = sentences.filter(s =>
      costSignals.some(sig => s.toLowerCase().includes(sig)) &&
      (s.includes(String(thisYear)) || s.includes(String(lastYear)))
    );
    if (costSentences.length > 0) {
      financialIntel.cost_initiatives = costSentences.slice(0, 2).join(". ").trim();
      triggers.push("CURRENT: " + costSentences[0].trim());
    }
  }

  // Extract M&A signals
  const maSignals = ["acqui", "merger", "divest", "takeover", "deal"];
  if (maSignals.some(s => answerLower.includes(s))) {
    const sentences = answer.split(/[.!?]+/).filter(s => s.trim().length > 20);
    const maSentences = sentences.filter(s =>
      maSignals.some(sig => s.toLowerCase().includes(sig)) &&
      (s.includes(String(thisYear)) || s.includes(String(lastYear)))
    );
    if (maSentences.length > 0) {
      financialIntel.ma_activity = maSentences.slice(0, 2).join(". ").trim();
      triggers.push("M&A ACTIVITY: " + maSentences[0].trim());
    }
  }

  // Extract new legal/regulatory signals
  const legalSignals = ["lawsuit", "litigation", "regulatory", "investigation", "ftc", "doj", "sec", "filed", "complaint"];
  if (legalSignals.some(s => answerLower.includes(s))) {
    const sentences = answer.split(/[.!?]+/).filter(s => s.trim().length > 20);
    const legalSentences = sentences.filter(s =>
      legalSignals.some(sig => s.toLowerCase().includes(sig)) &&
      (s.includes(String(thisYear)) || s.includes(String(lastYear)))
    );
    if (legalSentences.length > 0) {
      triggers.push("NEW LEGAL ISSUE: " + legalSentences[0].trim());
    }
  }

  // Extract personnel signals
  const personnelSignals = ["appointed", "hired", "joined", "promoted", "departed", "left", "replaced", "new general counsel", "new clo"];
  if (personnelSignals.some(s => answerLower.includes(s))) {
    const sentences = answer.split(/[.!?]+/).filter(s => s.trim().length > 20);
    const personnelSentences = sentences.filter(s =>
      personnelSignals.some(sig => s.toLowerCase().includes(sig)) &&
      (s.includes(String(thisYear)) || s.includes(String(lastYear)))
    );
    if (personnelSentences.length > 0) {
      triggers.push("PERSONNEL CHANGE: " + personnelSentences[0].trim());
    }
  }

  // If no specific triggers extracted, use the raw answer as context
  if (triggers.length === 0) {
    const noDataSignals = ["no current data", "no information", "cannot find", "not found"];
    if (!noDataSignals.some(s => answerLower.includes(s))) {
      // Extract first meaningful sentence as a trigger
      const sentences = answer.split(/[.!?]+/).filter(s =>
        s.trim().length > 30 &&
        (s.includes(String(thisYear)) || s.includes(String(lastYear)))
      );
      if (sentences.length > 0) {
        triggers.push(sentences[0].trim());
      }
    }
  }

  return { triggers, financialIntel };
}
'''

if 'getLiveIntelligence' not in verifier_content:
    with open(verifier_path, 'a') as f:
        f.write(live_intel_function)
    print("Done — getLiveIntelligence added to contactVerifier.js")
else:
    print("Skipped — getLiveIntelligence already exists")

# ── Step 2: Update researcher.js to use live intel ────────
researcher_path = os.path.join(base, "src", "researcher.js")

with open(researcher_path, 'r') as f:
    researcher_content = f.read()

# Add getLiveIntelligence import
if 'getLiveIntelligence' not in researcher_content:
    researcher_content = researcher_content.replace(
        "import { verifyAccountContacts } from './contactVerifier.js';",
        "import { verifyAccountContacts, getLiveIntelligence } from './contactVerifier.js';"
    )

    # Add live intel step after contact verification
    old_step = """    // Verify contacts with live web search if Perplexity key is available
    if (process.env.PERPLEXITY_API_KEY) {
      parsed = await verifyAccountContacts(account, parsed);
    }"""

    new_step = """    // Verify contacts with live web search if Perplexity key is available
    if (process.env.PERPLEXITY_API_KEY) {
      parsed = await verifyAccountContacts(account, parsed);

      // Replace Claude training-data triggers with live Perplexity intelligence
      const liveIntel = await getLiveIntelligence(account);
      if (liveIntel) {
        // Override sales triggers with current data
        if (liveIntel.triggers && liveIntel.triggers.length > 0) {
          parsed.sales_triggers = liveIntel.triggers;
          logger.info(`Live triggers applied for ${account.name}: ${liveIntel.triggers.length} triggers`);
        }
        // Override financial intel fields with current data
        if (liveIntel.financialIntel) {
          parsed.financial_intel = parsed.financial_intel || {};
          if (liveIntel.financialIntel.earnings_signals) {
            parsed.financial_intel.earnings_signals = liveIntel.financialIntel.earnings_signals;
          }
          if (liveIntel.financialIntel.cost_initiatives) {
            parsed.financial_intel.cost_initiatives = liveIntel.financialIntel.cost_initiatives;
          }
          if (liveIntel.financialIntel.ma_activity) {
            parsed.financial_intel.ma_activity = liveIntel.financialIntel.ma_activity;
          }
        }
        // Add live intel metadata
        parsed.live_intel_retrieved = liveIntel.retrievedAt;
        parsed.live_intel_sources = liveIntel.sources || [];
      }
    }"""

    if old_step in researcher_content:
        researcher_content = researcher_content.replace(old_step, new_step)
        with open(researcher_path, 'w') as f:
            f.write(researcher_content)
        print("Done — researcher.js updated with live intelligence step")
    else:
        print("WARNING — could not find insertion point in researcher.js")
        print("You may need to add the live intel step manually")
else:
    print("Skipped researcher.js — getLiveIntelligence already imported")

print("")
print("=" * 50)
print("LIVE INTELLIGENCE FIX COMPLETE")
print("=" * 50)
print("")
print("What changed:")
print("  - Sales triggers now come from Perplexity live web search")
print("  - Financial intel (earnings signals, cost initiatives, M&A)")
print("    is now sourced from current web data, not training data")
print("  - Only information from the last 12-24 months is used")
print("")
print("Test it now:")
print('  npm run research:account "AMD"')
print("")
print("AMD sales triggers should now reference 2025/2026 events")
print("not the 2024 restructuring.")
