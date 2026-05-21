import os

home = os.path.expanduser("~")
base = os.path.join(home, "legal-tracker")
verifier_path = os.path.join(base, "src", "contactVerifier.js")

with open(verifier_path, 'r') as f:
    content = f.read()

# Fix 1: Improve the structuring prompt to ALWAYS generate triggers
# even when Perplexity returns limited data, using what it finds
# and supplementing with known industry context

old_quality_check = '''    const structured = JSON.parse(raw);
    structured.sources = citations.slice(0, 3);
    structured.retrievedAt = new Date().toISOString();

    const immCount = (structured.immediate_triggers || []).length;
    const stratCount = (structured.strategic_triggers || []).length;
    logger.info(`Structured triggers for ${account.name}: ${immCount} immediate, ${stratCount} strategic (quality: ${structured.intelligence_quality})`);

    return structured;

  } catch (err) {
    logger.warn("Claude structuring failed for " + account.name + " — returning raw Perplexity data", { error: err.message });
    // Fallback: return basic structure with raw answer
    return {
      immediate_triggers: [],
      strategic_triggers: [{ trigger: perplexityAnswer.slice(0, 300), timeframe: "Recent", sales_implication: "Review raw intelligence above", angle: "TBD" }],
      financial_intel: {},
      intelligence_date: todayStr,
      intelligence_quality: "Low",
      sources: citations.slice(0, 3),
      retrievedAt: new Date().toISOString(),
    };
  }'''

new_quality_check = '''    let structured;
    try {
      structured = JSON.parse(raw);
    } catch(parseErr) {
      // Try to recover truncated JSON
      const lastBrace = raw.lastIndexOf('}');
      if (lastBrace > 0) {
        try { structured = JSON.parse(raw.slice(0, lastBrace + 1)); } catch(e2) { structured = null; }
      }
    }

    if (!structured) {
      logger.warn("Claude structuring parse failed for " + account.name);
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

    structured.sources = citations.slice(0, 3);
    structured.retrievedAt = new Date().toISOString();

    // If Claude returned empty triggers despite having data, force extract from raw answer
    const immCount = (structured.immediate_triggers || []).length;
    const stratCount = (structured.strategic_triggers || []).length;

    if (immCount === 0 && stratCount === 0 && perplexityAnswer.length > 200) {
      logger.warn(`Claude returned empty triggers for ${account.name} despite ${perplexityAnswer.length} chars of Perplexity data — forcing extraction`);

      // Force Claude to try again with a simpler, more direct prompt
      try {
        const forcePrompt = `Based on this intelligence about ${account.name}, write 2-3 specific sales triggers for a legal services company (Consilio) selling eDiscovery, document review, flex legal talent, and outside counsel advisory.

INTELLIGENCE:
${perplexityAnswer.slice(0, 2000)}

For each trigger, write ONE sentence describing: what happened, when it happened, and why it creates a need for legal services.
Use this exact JSON format:
{
  "immediate_triggers": [{"trigger": "...", "date": "...", "sales_implication": "...", "urgency": "High"}],
  "strategic_triggers": [{"trigger": "...", "timeframe": "...", "sales_implication": "...", "angle": "..."}],
  "financial_intel": {"latest_filing": null, "cost_initiatives": null, "earnings_signals": null, "ma_activity": null},
  "intelligence_quality": "Medium"
}`;

        const Anthropic2 = (await import("@anthropic-ai/sdk")).default;
        const client2 = new Anthropic2({ apiKey: process.env.ANTHROPIC_API_KEY });
        const resp2 = await client2.messages.create({
          model: "claude-sonnet-4-5",
          max_tokens: 1000,
          messages: [{ role: "user", content: forcePrompt }],
        });

        const raw2 = resp2.content
          .filter(b => b.type === "text").map(b => b.text).join("")
          .replace(/^```json\s*/i, "").replace(/^```\s*/i, "").replace(/```\s*$/i, "").trim();

        const structured2 = JSON.parse(raw2);
        structured2.sources = citations.slice(0, 3);
        structured2.retrievedAt = new Date().toISOString();
        logger.info(`Force extraction succeeded for ${account.name}: ${(structured2.immediate_triggers||[]).length} immediate, ${(structured2.strategic_triggers||[]).length} strategic`);
        return structured2;

      } catch(forceErr) {
        logger.warn(`Force extraction also failed for ${account.name}: ${forceErr.message}`);
      }
    }

    logger.info(`Structured triggers for ${account.name}: ${immCount} immediate, ${stratCount} strategic (quality: ${structured.intelligence_quality})`);
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
  }'''

if old_quality_check in content:
    content = content.replace(old_quality_check, new_quality_check)
    print("Done — added force extraction fallback")
else:
    print("WARNING — quality check pattern not found")

# Fix 2: Remove stale personnel changes from sales triggers
# The researcher.js applies live intel but personnel_changes come from Claude training data
# We need to filter out anything with years before 2025

researcher_path = os.path.join(base, "src", "researcher.js")
with open(researcher_path, 'r') as f:
    researcher = f.read()

old_apply = '''        parsed.live_intel_retrieved = liveIntel.retrievedAt;
        parsed.live_intel_sources = liveIntel.sources || [];

        const iCount = (liveIntel.immediate_triggers || []).length;
        const sCount = (liveIntel.strategic_triggers || []).length;
        logger.info(`Live triggers applied for ${account.name}: ${iCount} immediate, ${sCount} strategic (${liveIntel.intelligence_quality} quality)`);'''

new_apply = '''        parsed.live_intel_retrieved = liveIntel.retrievedAt;
        parsed.live_intel_sources = liveIntel.sources || [];

        // Filter out stale personnel changes (older than 2025)
        if (parsed.personnel_changes) {
          parsed.personnel_changes = parsed.personnel_changes.filter(p => {
            const text = (p.change || "") + (p.name || "");
            // Keep if it mentions 2025 or 2026, remove if only 2024 or older
            const has2025 = text.includes("2025") || text.includes("2026");
            const hasOld = text.includes("2023") || text.includes("2024") || text.includes("2022");
            return has2025 || !hasOld; // keep if recent or if no date mentioned
          });
        }

        const iCount = (liveIntel.immediate_triggers || []).length;
        const sCount = (liveIntel.strategic_triggers || []).length;
        logger.info(`Live triggers applied for ${account.name}: ${iCount} immediate, ${sCount} strategic (${liveIntel.intelligence_quality} quality)`);'''

if old_apply in researcher:
    researcher = researcher.replace(old_apply, new_apply)
    with open(researcher_path, 'w') as f:
        f.write(researcher)
    print("Done — stale personnel changes now filtered out")
else:
    print("WARNING — personnel filter pattern not found in researcher.js")

with open(verifier_path, 'w') as f:
    f.write(content)

print("")
print("="*50)
print("Run: npm run research:account \"AMD\"")
print("")
print("Watch for this in output:")
print("  [info] Perplexity litigation/financial/business search complete")
print("  [info] Structured triggers for AMD: X immediate, Y strategic")
print("  OR")
print("  [warn] Force extraction succeeded for AMD")
print("")
print("If triggers still empty after this, the issue is Perplexity")
print("not finding AMD data — we'll inject known triggers manually")
