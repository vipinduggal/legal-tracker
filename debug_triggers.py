import os

home = os.path.expanduser("~")
base = os.path.join(home, "legal-tracker")

script_path = os.path.join(base, "scripts", "debugTriggers.js")

script = '''// scripts/debugTriggers.js — see exactly what Perplexity returns and what Claude does with it
import "dotenv/config";
import axios from "axios";
import Anthropic from "@anthropic-ai/sdk";

const PERPLEXITY_KEY = process.env.PERPLEXITY_API_KEY;
const account = { name: "AMD", industry: "Semiconductors", location: "Santa Clara, CA", id: "amd" };
const today = new Date().toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" });

console.log("=== STEP 1: PERPLEXITY SEARCHES ===\\n");

const searches = [
  { label: "litigation", query: `What lawsuits, patent cases, class actions, or regulatory investigations involve AMD Advanced Micro Devices in 2025 or 2026? Include case names, dates, courts, dollar amounts.` },
  { label: "financial",  query: `What did AMD report in Q1 2026 or Q4 2025 earnings? Any legal reserves, loss contingencies, restructuring charges, cost cuts? Specific dollar amounts and dates.` },
  { label: "business",   query: `What major business changes has AMD announced in late 2025 or 2026? Acquisitions, export controls, China restrictions, leadership changes in legal or compliance roles?` },
];

let combined = "";
for (const s of searches) {
  try {
    const r = await axios.post("https://api.perplexity.ai/chat/completions", {
      model: "sonar",
      messages: [
        { role: "system", content: "Today is " + today + ". Be specific with dates and facts. Only 2025-2026 information." },
        { role: "user", content: s.query }
      ],
      max_tokens: 600,
    }, {
      headers: { Authorization: "Bearer " + PERPLEXITY_KEY, "Content-Type": "application/json" },
      timeout: 15000,
    });
    const answer = r.data?.choices?.[0]?.message?.content || "";
    console.log("--- " + s.label.toUpperCase() + " (" + answer.length + " chars) ---");
    console.log(answer);
    console.log();
    combined += "\\n\\n=== " + s.label.toUpperCase() + " ===\\n" + answer;
  } catch(e) {
    console.log("--- " + s.label.toUpperCase() + " FAILED: " + e.message);
  }
}

console.log("\\n=== STEP 2: CLAUDE STRUCTURING ===\\n");
console.log("Combined length:", combined.length, "chars\\n");

const client = new Anthropic();
const prompt = `You sell legal services (eDiscovery, document review, ALSP, flex legal talent) to corporate legal departments.

Read this intelligence about AMD and identify sales triggers.

INTELLIGENCE:
${combined}

Return JSON with immediate_triggers (last 90 days, urgent) and strategic_triggers (last 6 months, longer term).
Each trigger needs: what happened, when, why it creates legal services demand.

{
  "immediate_triggers": [{"trigger": "...", "date": "...", "sales_implication": "...", "urgency": "High"}],
  "strategic_triggers": [{"trigger": "...", "timeframe": "...", "sales_implication": "...", "angle": "..."}],
  "intelligence_quality": "High or Medium or Low"
}`;

try {
  const resp = await client.messages.create({
    model: "claude-sonnet-4-5",
    max_tokens: 1000,
    messages: [{ role: "user", content: prompt }],
  });
  const raw = resp.content.filter(b => b.type === "text").map(b => b.text).join("");
  console.log("Claude raw response:");
  console.log(raw);
  console.log();

  const cleaned = raw.replace(/^```json\\s*/i,"").replace(/^```\\s*/i,"").replace(/```\\s*$/i,"").trim();
  try {
    const parsed = JSON.parse(cleaned);
    console.log("\\nPARSED SUCCESSFULLY:");
    console.log("Immediate triggers:", parsed.immediate_triggers?.length || 0);
    console.log("Strategic triggers:", parsed.strategic_triggers?.length || 0);
    console.log("Quality:", parsed.intelligence_quality);
    if (parsed.immediate_triggers?.length) {
      parsed.immediate_triggers.forEach(t => console.log("  IMMED:", t.trigger));
    }
    if (parsed.strategic_triggers?.length) {
      parsed.strategic_triggers.forEach(t => console.log("  STRAT:", t.trigger));
    }
  } catch(pe) {
    console.log("JSON PARSE FAILED:", pe.message);
    console.log("Last 200 chars:", raw.slice(-200));
  }
} catch(e) {
  console.log("Claude call failed:", e.message);
}
''';

with open(script_path, 'w') as f:
    f.write(script)

print("Done — scripts/debugTriggers.js written")
print("")
print("Run: node scripts/debugTriggers.js 2>&1 | head -100")
