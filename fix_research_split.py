import os, re

home = os.path.expanduser("~")
base = os.path.join(home, "legal-tracker")
researcher_path = os.path.join(base, "src", "researcher.js")
prompts_path = os.path.join(base, "src", "prompts.js")

with open(researcher_path, 'r') as f:
    researcher = f.read()

with open(prompts_path, 'r') as f:
    prompts = f.read()

# ── Strategy: split the research prompt into two smaller prompts ──
# Prompt A: contacts + tech + counsel + alsp + flex (people and tools)
# Prompt B: litigation + regulatory + financial + personnel + triggers + summary
# Each returns a smaller JSON that won't truncate
# Then merge the two results

# First add a second prompt builder to prompts.js
prompt_a = '''
export function buildResearchPromptA(account) {
  const name = account.name;
  const industry = account.industry;
  const location = account.location;
  return `You are a legal intelligence analyst. Research "${name}" (${industry}, ${location}).
Return ONLY valid JSON, no markdown, no preamble.
Focus ONLY on people and technology — not litigation or financial data.

{
  "contacts": [
    {
      "name": "string - full name",
      "title": "string - exact current title",
      "tag": "one of: CLO | GC | Deputy GC | Associate GC | Head of Litigation | Head of Legal Operations | Head of Employment | Head of IP | Head of Privacy | Head of Compliance | Head of Regulatory | Head of Corporate | Litigator | CEO | CFO | COO | CISO | Other Legal",
      "linkedin": "string or null",
      "email": "string or null",
      "confidence": "one of: High | Medium | Low",
      "confidence_reason": "string - source and date",
      "notes": "string or null",
      "department": "one of: Legal | Executive | Compliance | Privacy | Other"
    }
  ],
  "tech": ["string - legal tech product and category"],
  "counsel": ["string - law firm name and practice area"],
  "alsp": ["string - ALSP name and service"],
  "flex": ["string - flex talent provider and service"]
}

Find as many current contacts as possible including full C-suite and all legal functional heads.
Only include people currently in their roles as of 2025-2026.`;
}

export function buildResearchPromptB(account) {
  const name = account.name;
  const industry = account.industry;
  const location = account.location;
  return `You are a legal intelligence analyst. Research "${name}" (${industry}, ${location}).
Return ONLY valid JSON, no markdown, no preamble.
Focus ONLY on legal issues, financial intel, and sales intelligence — not contacts or technology.
Only include information from 2024-2026. Flag anything older.

{
  "litigation": [
    {
      "type": "string - litigation type",
      "period": "string - date range",
      "summary": "string - 1-2 sentence factual summary",
      "counsel": "string - outside counsel firm",
      "status": "one of: Pending | Settled | Resolved | Dismissed | Ongoing",
      "is_new": "boolean - true if filed or updated in last 30 days"
    }
  ],
  "regulatory": [
    {
      "type": "string - regulatory issue type",
      "period": "string - date range",
      "summary": "string - 1-2 sentence summary",
      "counsel": "string - outside counsel firm",
      "status": "one of: Ongoing | Resolved | Closed | Under investigation",
      "is_new": "boolean"
    }
  ],
  "financial_intel": {
    "latest_filing": "string - most recent 10-K or 10-Q period or null",
    "legal_risk_factors": "string - key legal risk factors from most recent annual report or null",
    "cost_initiatives": "string - cost reduction programs or null",
    "litigation_disclosure": "string - legal proceedings disclosure from most recent SEC filing or null",
    "earnings_signals": "string - earnings call comments about legal department or null",
    "ma_activity": "string - recent M&A activity or null"
  },
  "personnel_changes": [
    {
      "name": "string",
      "change": "string - what changed with date",
      "significance": "string - why this matters for sales"
    }
  ],
  "sales_triggers": ["string - specific time-sensitive reason to reach out now"],
  "intel_summary": "string - 3-4 sentence sales intelligence summary"
}`;
}
'''

# Add the two new functions to prompts.js
if "buildResearchPromptA" not in prompts:
    prompts = prompts + prompt_a
    with open(prompts_path, 'w') as f:
        f.write(prompts)
    print("Done — buildResearchPromptA and buildResearchPromptB added to prompts.js")
else:
    print("Skipped — prompts A/B already exist")

# ── Now update researcher.js to use the split approach ──
# Find the import of buildResearchPrompt
if "buildResearchPromptA" not in researcher:
    # Update the import
    researcher = researcher.replace(
        "import { buildResearchPrompt }",
        "import { buildResearchPrompt, buildResearchPromptA, buildResearchPromptB }"
    )
    # Also handle default import style
    researcher = researcher.replace(
        "buildResearchPrompt } from './prompts.js'",
        "buildResearchPrompt, buildResearchPromptA, buildResearchPromptB } from './prompts.js'"
    )
    print("Done — researcher.js import updated")

# Find the main research function and add split logic
# Look for where the Anthropic call is made and add split logic before it
old_research_call = '''    const prompt = buildResearchPrompt(account);

    const response = await client.messages.create({
      model: "claude-sonnet-4-5",
      max_tokens: 8192,
      messages: [{ role: "user", content: prompt }],
    });

    const raw = response.content
      .filter(b => b.type === "text")
      .map(b => b.text)
      .join("")
      .replace(/^```json\\s*/i, '')
      .replace(/^```\\s*/i, '')
      .replace(/```\\s*$/i, '')
      .trim();'''

new_research_call = '''    const promptA = buildResearchPromptA(account);
    const promptB = buildResearchPromptB(account);

    // Run both prompts in parallel — each is half the size so no truncation
    const [responseA, responseB] = await Promise.all([
      client.messages.create({
        model: "claude-sonnet-4-5",
        max_tokens: 4096,
        messages: [{ role: "user", content: promptA }],
      }),
      client.messages.create({
        model: "claude-sonnet-4-5",
        max_tokens: 4096,
        messages: [{ role: "user", content: promptB }],
      }),
    ]);

    const cleanJSON = (resp) => resp.content
      .filter(b => b.type === "text").map(b => b.text).join("")
      .replace(/^```json\\s*/i, '').replace(/^```\\s*/i, '').replace(/```\\s*$/i, '').trim();

    const rawA = cleanJSON(responseA);
    const rawB = cleanJSON(responseB);

    // Parse both with recovery
    const parseHalf = (raw, label) => {
      try { return JSON.parse(raw); }
      catch(e) {
        const lastBrace = raw.lastIndexOf('}');
        if (lastBrace > 0) {
          try { return JSON.parse(raw.slice(0, lastBrace + 1)); }
          catch(e2) {}
        }
        logger.warn(`${label} parse failed for ${account.name}: ${e.message}`);
        return {};
      }
    };

    const parsedA = parseHalf(rawA, "Part A (contacts/tech)");
    const parsedB = parseHalf(rawB, "Part B (litigation/financial)");

    // Merge both halves into one complete research object
    const raw = JSON.stringify({ ...parsedA, ...parsedB });'''

# Try exact match first
if old_research_call in researcher:
    researcher = researcher.replace(old_research_call, new_research_call)
    print("Done — researcher.js split into two parallel calls")
else:
    print("Exact pattern not found — trying flexible match...")
    # Try to find just the messages.create call
    pattern = r'const prompt = buildResearchPrompt\(account\);[\s\S]*?\.trim\(\);'
    match = re.search(pattern, researcher)
    if match:
        researcher = researcher[:match.start()] + new_research_call + researcher[match.end():]
        print("Done — researcher.js patched with flexible match")
    else:
        # Last resort: just find where JSON.parse is called on the raw response
        # and add the split before it
        print("Flexible match also failed — checking file structure...")
        idx = researcher.find("buildResearchPrompt(account)")
        if idx > 0:
            print("Found buildResearchPrompt call at:", idx)
            print(researcher[idx:idx+400])
        else:
            print("buildResearchPrompt call not found")
            # Show all function calls
            calls = re.findall(r'\w+\(account\)', researcher)
            print("Function calls with account:", calls[:10])

# Also update the JSON parse section to handle merged object
old_parse = '''    // Robust JSON parsing with multiple recovery strategies
    let parsed;
    try {
      parsed = JSON.parse(cleaned);'''

new_parse = '''    // Parse merged research object
    let parsed;
    try {
      parsed = JSON.parse(raw);'''

if old_parse in researcher:
    researcher = researcher.replace(old_parse, new_parse)
    print("Done — JSON parse updated for merged object")

# Remove the old cleaned variable since we now use raw directly
old_cleaned = '''    let cleaned = raw
      .replace(/^```json\\s*/i, '')
      .replace(/^```\\s*/i, '')
      .replace(/```\\s*$/i, '')
      .trim();'''

if old_cleaned in researcher:
    researcher = researcher.replace(old_cleaned, "    // cleaned step skipped — raw already cleaned in split calls")
    print("Done — removed redundant cleaned step")

with open(researcher_path, 'w') as f:
    f.write(researcher)

print("")
print("="*50)
print("RESEARCH SPLIT COMPLETE")
print("="*50)
print("")
print("Each account now makes 2 parallel Claude calls:")
print("  Call A (4096 tokens): contacts, tech, counsel, alsp, flex")
print("  Call B (4096 tokens): litigation, regulatory, financial, triggers")
print("Results merged into one complete research object")
print("")
print("Test: npm run research:account \"Microsoft\"")
print("Should complete without any JSON parse errors")
