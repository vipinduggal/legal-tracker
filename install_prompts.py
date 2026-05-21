import os

home = os.path.expanduser("~")
path = os.path.join(home, "legal-tracker", "src", "prompts.js")

# Build the research prompt text as a plain string (no template literals)
research_prompt_lines = [
    'You are a senior legal intelligence analyst supporting a sales team that sells services to corporate legal departments (ALSPs, flex legal talent, legal ops consulting, outside counsel advisory, eDiscovery, contract management).',
    '',
    'Research "ACCOUNT_NAME" (ACCOUNT_INDUSTRY, headquartered in ACCOUNT_LOCATION) and return a structured JSON object. Use only publicly available information. If information is unknown or unverifiable, use null or an empty array. Do NOT fabricate.',
    '',
    'Return ONLY valid JSON, no markdown, no explanation, no preamble.',
    '',
    '{',
    '  "contacts": [',
    '    {',
    '      "name": "string - full name",',
    '      "title": "string - exact current title",',
    '      "tag": "one of: CLO | GC | Head of Litigation | Head of Legal Operations | Litigator | Deputy GC | Associate GC",',
    '      "linkedin": "string - LinkedIn profile URL if known, else null",',
    '      "email": "string - professional email if publicly known, else null",',
    '      "confidence": "one of: High | Medium | Low",',
    '      "confidence_reason": "string - why this confidence level, e.g. Confirmed via company press release March 2025 or AI-sourced only - verify on LinkedIn before outreach",',
    '      "notes": "string - recent hire, prior firm, tenure concerns, or null"',
    '    }',
    '  ],',
    '  "tech": ["string - legal technology product and category, e.g. Ironclad (contract management), Legal Tracker (eBilling)"],',
    '  "counsel": ["string - law firm name and primary practice area, e.g. Latham and Watkins (litigation, M&A)"],',
    '  "alsp": ["string - ALSP name and service type, e.g. Elevate (document review, legal ops)"],',
    '  "flex": ["string - flex talent provider and service type, e.g. Axiom Law (contract attorneys)"],',
    '  "litigation": [',
    '    {',
    '      "type": "string - litigation type, e.g. Securities class action, Employment discrimination, IP infringement",',
    '      "period": "string - date range, e.g. Q2 2024 to present",',
    '      "summary": "string - 1-2 sentence factual summary",',
    '      "counsel": "string - outside counsel firm name",',
    '      "status": "one of: Pending | Settled | Resolved | Dismissed | Ongoing",',
    '      "is_new": "boolean - true if filed or materially updated in last 30 days"',
    '    }',
    '  ],',
    '  "regulatory": [',
    '    {',
    '      "type": "string - regulatory issue type, e.g. FTC inquiry, SEC investigation, OSHA citation",',
    '      "period": "string - date range",',
    '      "summary": "string - 1-2 sentence factual summary",',
    '      "counsel": "string - outside counsel firm name",',
    '      "status": "one of: Ongoing | Resolved | Closed | Under investigation",',
    '      "is_new": "boolean - true if filed or materially updated in last 30 days"',
    '    }',
    '  ],',
    '  "financial_intel": {',
    '    "latest_filing": "string - most recent 10-K or 10-Q period, e.g. FY2024 10-K filed February 2025",',
    '    "legal_risk_factors": "string - key legal and regulatory risk factors disclosed in most recent annual report, 2-3 sentences",',
    '    "cost_initiatives": "string - any disclosed cost reduction or efficiency programs that would pressure legal spend, or null",',
    '    "litigation_disclosure": "string - what the company disclosed about legal proceedings in their most recent SEC filing, 1-2 sentences",',
    '    "earnings_signals": "string - any themes from most recent earnings call relevant to legal department, or null",',
    '    "ma_activity": "string - any recent or pending M&A activity that creates legal workload, or null"',
    '  },',
    '  "personnel_changes": [',
    '    {',
    '      "name": "string - person name",',
    '      "change": "string - what changed, e.g. Appointed GC January 2025, Departed December 2024",',
    '      "significance": "string - why this matters for sales"',
    '    }',
    '  ],',
    '  "sales_triggers": [',
    '    "string - specific time-sensitive reason to reach out now, e.g. Securities class action in discovery phase - document review surge capacity needed, New GC appointed 60 days ago - actively building vendor relationships, Q1 earnings cited $400M cost reduction target - CLO under pressure to cut outside counsel spend"',
    '  ],',
    '  "intel_summary": "string - 3-4 sentence sales intelligence summary: what is the most important thing a salesperson should know about this company right now, what is the specific opportunity, and what is the recommended angle of approach"',
    '}',
    '',
    'RESEARCH PRIORITIES:',
    '- Contacts: prioritize current role holders. Flag anyone whose departure has been reported. Note confidence level for each.',
    '- Litigation: include all matters from last 24 months. Flag any filed or updated in last 30 days with is_new true.',
    '- Regulatory: include all agency actions from last 24 months. Flag recent actions with is_new true.',
    '- Financial intel: pull from the most recent 10-K, 10-Q, earnings call transcript, or press release available.',
    '- Personnel changes: include any GC, CLO, Head of Legal Ops, or Head of Litigation changes in last 18 months.',
    '- Sales triggers: be specific. Reference actual case names, dollar amounts, filing dates where known. Make them actionable this week.',
]

digest_prompt_lines = [
    'You are a strategic sales advisor for a company selling legal services (ALSP, flex talent, legal ops consulting, outside counsel advisory, eDiscovery) to corporate legal departments.',
    '',
    'Generate a weekly outreach plan based on the account intelligence provided.',
    'Return ONLY valid JSON, no markdown.',
    '',
    '{',
    '  "week_summary": "string - 3-4 sentence overview of most important themes this week. Be specific - name companies, reference actual events.",',
    '  "priority_accounts": [',
    '    {',
    '      "account_name": "string",',
    '      "priority_rank": "number",',
    '      "urgency": "one of: Critical | High | Medium",',
    '      "trigger": "string - the specific event making THIS WEEK the right time. Must reference a real event: new filing, financial disclosure, personnel change, earnings statement.",',
    '      "contact": {',
    '        "name": "string - specific person to contact",',
    '        "title": "string",',
    '        "confidence": "string - High/Medium/Low",',
    '        "why_them": "string - why this specific person"',
    '      },',
    '      "talking_point": "string - single best opening line referencing the specific trigger",',
    '      "action": "string - exactly what to do: email, LinkedIn message, phone call, send article",',
    '      "email": {',
    '        "subject": "string - specific, references the actual situation",',
    '        "body": "string - full email 150-200 words. Must reference specific trigger, dollar amounts, case names, or dates. Not a template."',
    '      },',
    '      "linkedin_message": "string - shorter version under 100 words"',
    '    }',
    '  ],',
    '  "new_filings_alert": [',
    '    {',
    '      "account_name": "string",',
    '      "filing_type": "string",',
    '      "summary": "string - what was filed and why it matters",',
    '      "suggested_action": "string - what to do about it this week"',
    '    }',
    '  ],',
    '  "personnel_watch": [',
    '    {',
    '      "account_name": "string",',
    '      "person": "string",',
    '      "change": "string",',
    '      "window": "string - how long the relationship-building window is open and why it closes"',
    '    }',
    '  ],',
    '  "quick_touches": [',
    '    {',
    '      "account_name": "string",',
    '      "action": "string - specific low-effort action"',
    '    }',
    '  ]',
    '}',
    '',
    'Rank priority accounts by: new filings in last 30 days first, then new personnel in last 90 days, then active litigation in discovery phase, then cost reduction initiatives, then regulatory pressure.',
    'Select top 5 for priority_accounts. Add up to 5 for new_filings_alert if they have is_new filings. Add up to 5 for personnel_watch. Add 5 for quick_touches.',
]

content = '''// prompts.js — Research and digest prompt templates
// Updated with deeper research: financial intel, new filings detection, personnel changes, contact verification

export function buildResearchPrompt(account) {
  const lines = ''' + repr(research_prompt_lines) + ''';
  return lines
    .join("\\n")
    .replace(/ACCOUNT_NAME/g, account.name)
    .replace(/ACCOUNT_INDUSTRY/g, account.industry)
    .replace(/ACCOUNT_LOCATION/g, account.location);
}

export function buildWeeklyDigestPrompt(accounts, researchData) {
  const digestLines = ''' + repr(digest_prompt_lines) + ''';
  const basePrompt = digestLines.join("\\n");

  const accountSummaries = accounts
    .filter(a => researchData[a.id])
    .map(a => {
      const d = researchData[a.id];
      const newFilings = [
        ...(d.litigation || []).filter(l => l.is_new),
        ...(d.regulatory || []).filter(r => r.is_new),
      ];
      const triggers = (d.sales_triggers || []);
      return [
        "ACCOUNT: " + a.name + " (" + a.industry + ", " + a.location + ")",
        "Contacts: " + ((d.contacts || []).map(c => c.name + " (" + c.tag + ", " + c.confidence + ")").join(", ") || "None"),
        "Active litigation: " + ((d.litigation || []).filter(l => !["Resolved","Settled","Dismissed"].includes(l.status)).map(l => l.type + (l.is_new ? " [NEW]" : "")).join(", ") || "None"),
        "Active regulatory: " + ((d.regulatory || []).filter(r => !["Resolved","Closed"].includes(r.status)).map(r => r.type + (r.is_new ? " [NEW]" : "")).join(", ") || "None"),
        "New filings (last 30 days): " + (newFilings.map(f => f.type).join(", ") || "None"),
        "Personnel changes: " + ((d.personnel_changes || []).map(p => p.name + ": " + p.change).join(", ") || "None recent"),
        "Cost initiatives: " + (d.financial_intel?.cost_initiatives || "None disclosed"),
        "Earnings signals: " + (d.financial_intel?.earnings_signals || "None"),
        "Sales triggers: " + (triggers.slice(0, 3).join(" | ") || "None identified"),
        "Intel summary: " + (d.intel_summary || "No summary"),
      ].join("\\n");
    }).join("\\n\\n");

  return basePrompt + "\\n\\nACCOUNT INTELLIGENCE:\\n" + accountSummaries;
}
'''

with open(path, 'w') as f:
    f.write(content)

print("Done — prompts.js written to " + path)
print("File size: " + str(os.path.getsize(path)) + " bytes")
