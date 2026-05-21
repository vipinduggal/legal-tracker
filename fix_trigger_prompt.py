import os

home = os.path.expanduser("~")
base = os.path.join(home, "legal-tracker")
verifier_path = os.path.join(base, "src", "contactVerifier.js")

with open(verifier_path, 'r') as f:
    content = f.read()

old_structure_prompt = '''    const structurePrompt = `You are a legal sales intelligence analyst. I have gathered the following recent intelligence about ${account.name} (${account.industry}, ${account.location}) from live web search conducted today, ${todayStr}.

LIVE INTELLIGENCE FROM WEB SEARCH:
${perplexityAnswer}

Based ONLY on the information above, create structured sales triggers in two categories:

1. IMMEDIATE TRIGGERS (last 90 days — events driving urgent, near-term sales opportunity):
   - New litigation or regulatory actions just filed
   - Recent leadership changes (new GC/CLO in last 90 days = vendor panel window open)
   - Earnings calls from last quarter mentioning legal cost pressure
   - Recent announcements of cost cuts that pressure legal spend

2. STRATEGIC TRIGGERS (last 6 months — trends affecting longer-term sales strategy):
   - Sustained litigation volume requiring ongoing support
   - M&A activity creating legal workload increase
   - Business expansion into new markets requiring legal infrastructure
   - Technology adoption signals (if they are buying legal tech, what gaps remain)
   - Regulatory environment shifts affecting their industry

RULES:
- Only include triggers supported by the intelligence above — do not add anything from your own training data
- Every trigger must include a specific date or time reference (e.g. "Q1 2026", "March 2026", "announced last month")
- If the intelligence does not support a trigger in a category, leave that category empty
- Be specific: include dollar amounts, case names, names of people where mentioned
- Each trigger should end with a clear sales implication

Return ONLY valid JSON:
{
  "immediate_triggers": [
    {
      "trigger": "string — specific event with date",
      "date": "string — specific date or period, e.g. March 2026",
      "sales_implication": "string — what this means for your outreach this week",
      "urgency": "one of: Critical | High | Medium"
    }
  ],
  "strategic_triggers": [
    {
      "trigger": "string — trend or pattern with timeframe",
      "timeframe": "string — e.g. Last 6 months, Q4 2025 - present",
      "sales_implication": "string — how this shapes your longer-term sales strategy",
      "angle": "string — what service or capability to position"
    }
  ],
  "financial_intel": {
    "latest_filing": "string — most recent earnings or filing period mentioned, or null",
    "cost_initiatives": "string — any cost reduction programs mentioned with specifics, or null",
    "earnings_signals": "string — what leadership said about costs/legal on recent earnings call, or null",
    "ma_activity": "string — any M&A mentioned with details, or null"
  },
  "intelligence_date": "${todayStr}",
  "intelligence_quality": "one of: High | Medium | Low — based on how much current data was found"
}`;'''

new_structure_prompt = '''    const structurePrompt = `You are a senior legal sales intelligence analyst for Consilio, a company selling legal services (ALSP document review, flex legal talent, legal ops consulting, eDiscovery, outside counsel advisory) to corporate legal departments.

Today is ${todayStr}. I have gathered live web search intelligence about ${account.name} (${account.industry}, based in ${account.location}).

LIVE INTELLIGENCE FROM WEB SEARCH:
${perplexityAnswer}

Your job: Extract specific, actionable sales triggers for Consilio's legal services. Think about what creates LEGAL WORK and LEGAL COST PRESSURE at this company right now.

LEGAL WORK SIGNALS TO LOOK FOR:
- Any lawsuit, investigation, or regulatory action = document review, outside counsel, eDiscovery need
- M&A activity = due diligence, integration counsel, contract volume surge
- Rapid business growth = contract backlog, need for flex legal talent
- Cost reduction programs = pressure on legal budget = opportunity for ALSP/flex alternatives
- Export control issues = regulatory compliance counsel need
- IP litigation = IP litigation support, document review
- Leadership change (new GC/CLO) = vendor panel evaluation window open
- Earnings disclosures mentioning legal reserves or loss contingencies = active litigation
- China/international regulatory issues = compliance counsel need

CATEGORY 1 — IMMEDIATE TRIGGERS (events from last 90 days requiring action THIS WEEK):
Must have a specific date. Must create an urgent legal workload or cost pressure. Must connect clearly to a Consilio service.

CATEGORY 2 — STRATEGIC TRIGGERS (trends from last 6 months shaping the account strategy):
Longer-term patterns. How to position Consilio over the next 3-6 months. What angle to take.

RULES:
- Be specific: cite dollar amounts, case names, filing dates, earnings quarter — anything concrete from the intelligence above
- Every trigger must include a date or time period from the last 6 months
- Connect every trigger to a specific Consilio service: eDiscovery, document review, ALSP, flex talent, legal ops, outside counsel advisory
- If something is from 2023 or 2024 and there is no recent update, DO NOT include it
- Intelligence quality: High = multiple specific recent facts found; Medium = some recent facts; Low = mostly general or no recent data

Return ONLY valid JSON, no markdown:
{
  "immediate_triggers": [
    {
      "trigger": "string — specific recent event with exact date and dollar amounts where known",
      "date": "string — specific month and year, e.g. May 2026, Q1 2026",
      "sales_implication": "string — specific Consilio service this creates demand for and why NOW",
      "urgency": "one of: Critical | High | Medium"
    }
  ],
  "strategic_triggers": [
    {
      "trigger": "string — trend or sustained pattern with timeframe",
      "timeframe": "string — specific period, e.g. Q4 2025 to present, Last 6 months",
      "sales_implication": "string — how this shapes Consilio positioning over next quarter",
      "angle": "string — specific Consilio service or capability to lead with"
    }
  ],
  "financial_intel": {
    "latest_filing": "string — most recent earnings period and key financial metric, or null",
    "cost_initiatives": "string — specific cost reduction program with dollar amount if mentioned, or null",
    "earnings_signals": "string — exact quote or specific detail from most recent earnings call relevant to legal spend, or null",
    "ma_activity": "string — specific deal name, size, and status if mentioned, or null"
  },
  "intelligence_date": "${todayStr}",
  "intelligence_quality": "one of: High | Medium | Low"
}`;'''

if old_structure_prompt in content:
    content = content.replace(old_structure_prompt, new_structure_prompt)
    print("Done — structurePrompt rewritten with legal-specific framing")
else:
    print("WARNING — structurePrompt pattern not found exactly")
    # Find it approximately
    idx = content.find("You are a legal sales intelligence analyst")
    if idx > 0:
        print("Found at index " + str(idx) + " — manual review needed")
    else:
        print("Not found at all — may need manual update")

with open(verifier_path, 'w') as f:
    f.write(content)

print("")
print("Test:")
print('  npm run research:account "AMD"')
print("")
print("Expected AMD triggers:")
print("  IMMEDIATE: Adeia IP lawsuit filed Nov 2025 — 10 patent claims, document review need")
print("  IMMEDIATE: Q1 2026 8-K loss contingency reserve — active litigation signal")
print("  IMMEDIATE: China export control compliance — MI308 GPU regulatory scrutiny")
print("  STRATEGIC: 38% revenue growth Q1 2026 — contract volume surge, flex talent need")
print("  STRATEGIC: Server CPU market expansion forecast — sustained legal infrastructure need")
