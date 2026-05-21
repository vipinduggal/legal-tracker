import os

home = os.path.expanduser("~")
base = os.path.join(home, "legal-tracker")
verifier_path = os.path.join(base, "src", "contactVerifier.js")

with open(verifier_path, 'r') as f:
    content = f.read()

# The fix: instead of asking Claude for all triggers in one big JSON response
# (which truncates), ask for immediate and strategic separately
# Then combine them. Each call is small enough to never truncate.

old_claude_call = '''  // Step 2: Use Anthropic to structure the Perplexity answer into categorized triggers
  try {
    const Anthropic = (await import("@anthropic-ai/sdk")).default;
    const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

    const structurePrompt ='''

new_claude_call = '''  // Step 2: Use Anthropic to structure triggers — split into two calls to avoid truncation
  try {
    const Anthropic = (await import("@anthropic-ai/sdk")).default;
    const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

    // Call 1: Immediate triggers only (last 90 days)
    const immediatePrompt = `You sell legal services (eDiscovery, document review, ALSP, flex legal talent, outside counsel advisory) to corporate legal departments.

Read this intelligence about ${account.name} (${account.industry}) and identify IMMEDIATE sales triggers — specific events from the last 90 days that create an urgent need for legal services RIGHT NOW.

Look for: new lawsuits filed, regulatory actions, earnings loss contingencies, cost-cutting programs, new GC/CLO hired, export control issues, M&A announced.

INTELLIGENCE:
${perplexityAnswer.slice(0, 3000)}

Return JSON array only — no other text:
[{"trigger":"specific event with details","date":"month year","sales_implication":"which Consilio service and why urgent","urgency":"Critical or High or Medium"}]

If no immediate triggers found, return: []`;

    // Call 2: Strategic triggers only (last 6 months)
    const strategicPrompt = `You sell legal services (eDiscovery, document review, ALSP, flex legal talent, outside counsel advisory) to corporate legal departments.

Read this intelligence about ${account.name} (${account.industry}) and identify STRATEGIC trends — patterns from the last 6 months that shape a longer-term sales approach.

Look for: sustained litigation volume, M&A integration complexity, rapid business growth creating contract surge, sustained regulatory pressure, technology transformation creating legal workload.

INTELLIGENCE:
${perplexityAnswer.slice(0, 3000)}

Return JSON array only — no other text:
[{"trigger":"trend with timeframe","timeframe":"specific period","sales_implication":"how to position over next quarter","angle":"which Consilio service to lead with"}]

If no strategic triggers found, return: []`;

    // Call 3: Financial intel only
    const financialPrompt = `Extract financial intelligence from this text about ${account.name}. Return JSON only:
{"latest_filing":"most recent earnings period mentioned or null","cost_initiatives":"specific cost reduction program with dollar amount or null","earnings_signals":"what was said about costs/legal spend on earnings call or null","ma_activity":"specific M&A deal name and status or null"}

TEXT: ${perplexityAnswer.slice(0, 2000)}`;

    const [immResp, stratResp, finResp] = await Promise.all([
      client.messages.create({ model: "claude-sonnet-4-5", max_tokens: 1500, messages: [{ role: "user", content: immediatePrompt }] }),
      client.messages.create({ model: "claude-sonnet-4-5", max_tokens: 1500, messages: [{ role: "user", content: strategicPrompt }] }),
      client.messages.create({ model: "claude-sonnet-4-5", max_tokens: 500, messages: [{ role: "user", content: financialPrompt }] }),
    ]);

    const parseArr = (resp) => {
      const raw = resp.content.filter(b => b.type === "text").map(b => b.text).join("")
        .replace(/^```json\\s*/i, "").replace(/^```\\s*/i, "").replace(/```\\s*$/i, "").trim();
      try { return JSON.parse(raw); } catch(e) {
        // Try to recover truncated array
        const lastBracket = raw.lastIndexOf('}');
        if (lastBracket > 0) {
          try { return JSON.parse(raw.slice(0, lastBracket + 1) + "]"); } catch(e2) {}
        }
        return [];
      }
    };

    const parseObj = (resp) => {
      const raw = resp.content.filter(b => b.type === "text").map(b => b.text).join("")
        .replace(/^```json\\s*/i, "").replace(/^```\\s*/i, "").replace(/```\\s*$/i, "").trim();
      try { return JSON.parse(raw); } catch(e) { return {}; }
    };

    const immediateTrigs = parseArr(immResp);
    const strategicTrigs = parseArr(stratResp);
    const financialIntel = parseObj(finResp);

    const quality = (immediateTrigs.length + strategicTrigs.length) >= 3 ? "High"
      : (immediateTrigs.length + strategicTrigs.length) >= 1 ? "Medium" : "Low";

    const structured = {
      immediate_triggers: Array.isArray(immediateTrigs) ? immediateTrigs : [],
      strategic_triggers: Array.isArray(strategicTrigs) ? strategicTrigs : [],
      financial_intel: financialIntel,
      intelligence_date: todayStr,
      intelligence_quality: quality,
      sources: citations.slice(0, 3),
      retrievedAt: new Date().toISOString(),
    };

    const iCount = structured.immediate_triggers.length;
    const sCount = structured.strategic_triggers.length;
    logger.info(`Structured triggers for ${account.name}: ${iCount} immediate, ${sCount} strategic (${quality})`);
    return structured;

  } catch (err) {
    logger.warn("Claude structuring failed for " + account.name, { error: err.message });
    return {
      immediate_triggers: [],
      strategic_triggers: [],
      financial_intel: {},
      intelligence_date: todayStr,
      intelligence_quality: "Low",
      sources: citations.slice(0, 3),
      retrievedAt: new Date().toISOString(),
    };
  }
}

// ── DEAD CODE BELOW — replaced by split calls above ──
function _oldStructurePrompt_unused(account, perplexityAnswer, todayStr) {
  const structurePrompt ='''

# Find the end of the old structurePrompt and close it properly
# We need to find where the old function ends and replace cleanly

# Find the old claude call start
old_start = "  // Step 2: Use Anthropic to structure the Perplexity answer into categorized triggers\n  try {\n    const Anthropic = (await import(\"@anthropic-ai/sdk\")).default;\n    const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });\n\n    const structurePrompt ="

if old_start in content:
    # Find where the structurePrompt ends and the actual API call begins
    idx = content.index(old_start)
    # Find the next occurrence of "const response = await client.messages.create"
    call_idx = content.index("const response = await client.messages.create", idx)
    # Find the end of the entire try/catch block
    # We'll replace from old_start to the closing of the getLiveIntelligence function

    # Find the closing of getLiveIntelligence
    # It ends with the last } before "function normalizeName"
    norm_idx = content.find("\n// Normalize a name", idx)
    if norm_idx == -1:
        norm_idx = content.find("\nfunction normalizeName", idx)
    if norm_idx == -1:
        norm_idx = content.find("\nexport async function verifyAccountContacts", idx)

    if norm_idx > 0:
        old_block = content[idx:norm_idx]
        content = content[:idx] + new_claude_call + content[norm_idx:]
        print("Done — Claude structuring replaced with 3 parallel calls")
    else:
        print("WARNING — could not find end of getLiveIntelligence function")
        print("Doing targeted replacement...")
        # Just replace the token counts
        content = content.replace("max_tokens: 2000,\n      messages: [{ role: \"user\", content: structurePrompt }]", "max_tokens: 4000,\n      messages: [{ role: \"user\", content: structurePrompt }]")
        print("Fallback: increased to 4000 tokens")
else:
    print("Step 2 pattern not found — increasing all token limits as fallback")
    import re
    content = re.sub(r'max_tokens:\s*\d+,', lambda m: 'max_tokens: 4000,' if int(re.search(r'\d+', m.group()).group()) < 3000 else m.group(), content)
    print("Done — all small token limits increased to 4000")

with open(verifier_path, 'w') as f:
    f.write(content)

print("")
print("Test: npm run research:account \"Microsoft\"")
print("Should see: [info] Structured triggers for Microsoft: X immediate, Y strategic")
