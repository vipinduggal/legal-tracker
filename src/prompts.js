// prompts.js — Research and digest prompt templates
// Updated: deeper research, recency requirements, financial intel, contact verification

export function buildResearchPrompt(account) {
  const name = account.name;
  const industry = account.industry;
  const location = account.location;

  return `You are a senior legal intelligence analyst supporting a sales team that sells services to corporate legal departments (ALSPs, flex legal talent, legal ops consulting, outside counsel advisory, eDiscovery, contract management).

Research "${name}" (${industry}, headquartered in ${location}) and return a structured JSON object. Use only publicly available information. If information is unknown or unverifiable, use null or an empty array. Do NOT fabricate.

Return ONLY valid JSON, no markdown, no explanation, no preamble.

RECENCY REQUIREMENTS - CRITICAL:
- Prioritize information from 2025 and 2026 over older sources
- For contacts: ONLY include people currently in their roles as of 2025-2026. If uncertain whether someone is still in a role, mark confidence as Low
- For litigation: focus on matters filed or active in 2024-2026. Clearly date all entries
- For financial intel: use the most recent earnings call or filing available and state the exact date
- If you only have information older than 2024 for a field, flag it as potentially outdated
- Never present 2022 or 2023 data as current without flagging it

{
  "contacts": [
    {
      "name": "string - full name",
      "title": "string - exact current title",
      "tag": "one of: CLO | GC | Deputy GC | Associate GC | Head of Litigation | Head of Legal Operations | Head of Employment | Head of IP | Head of Privacy | Head of Compliance | Head of Regulatory | Head of Corporate | Litigator | CEO | CFO | COO | CISO | Other Legal",
      "linkedin": "string - LinkedIn profile URL if known, else null",
      "email": "string - professional email if publicly known, else null",
      "confidence": "one of: High | Medium | Low",
      "confidence_reason": "string - source and date of confirmation, e.g. Confirmed via LinkedIn March 2026 or Company website 2026 or AI-sourced only",
      "notes": "string - relevant context: recent hire date, prior employer, bar admissions, areas of focus, or null",
      "department": "one of: Legal | Executive | Compliance | Privacy | Other"
    }
  ],
  "tech": [
    "string - legal technology product and category, e.g. Ironclad (contract management), Legal Tracker (eBilling)"
  ],
  "counsel": [
    "string - law firm name and primary practice area, e.g. Latham and Watkins (litigation, M&A)"
  ],
  "alsp": [
    "string - ALSP name and service type, e.g. Elevate (document review, legal ops)"
  ],
  "flex": [
    "string - flex talent provider and service type, e.g. Axiom Law (contract attorneys)"
  ],
  "litigation": [
    {
      "type": "string - litigation type, e.g. Securities class action, Employment discrimination, IP infringement",
      "period": "string - date range, e.g. Q2 2024 to present",
      "summary": "string - 1-2 sentence factual summary",
      "counsel": "string - outside counsel firm name",
      "status": "one of: Pending | Settled | Resolved | Dismissed | Ongoing",
      "is_new": "boolean - true if filed or materially updated in last 30 days"
    }
  ],
  "regulatory": [
    {
      "type": "string - regulatory issue type, e.g. FTC inquiry, SEC investigation, OSHA citation",
      "period": "string - date range",
      "summary": "string - 1-2 sentence factual summary",
      "counsel": "string - outside counsel firm name",
      "status": "one of: Ongoing | Resolved | Closed | Under investigation",
      "is_new": "boolean - true if filed or materially updated in last 30 days"
    }
  ],
  "financial_intel": {
    "latest_filing": "string - most recent 10-K or 10-Q period, e.g. FY2024 10-K filed February 2025",
    "legal_risk_factors": "string - key legal and regulatory risk factors from most recent annual report, 2-3 sentences",
    "cost_initiatives": "string - any disclosed cost reduction or efficiency programs that would pressure legal spend, or null",
    "litigation_disclosure": "string - what the company disclosed about legal proceedings in most recent SEC filing, 1-2 sentences",
    "earnings_signals": "string - themes from most recent earnings call relevant to legal department, or null",
    "ma_activity": "string - any recent or pending M&A activity that creates legal workload, or null"
  },
  "personnel_changes": [
    {
      "name": "string - person name",
      "change": "string - what changed, e.g. Appointed GC January 2025, Departed December 2024",
      "significance": "string - why this matters for sales"
    }
  ],
  "sales_triggers": [
    "string - specific time-sensitive reason to reach out now, e.g. Securities class action in discovery phase - document review surge capacity needed, New GC appointed 60 days ago - actively building vendor relationships, Q1 earnings cited $400M cost reduction target - CLO under pressure to cut outside counsel spend"
  ],
  "intel_summary": "string - 3-4 sentence sales intelligence summary: what is the most important thing a salesperson should know about this company right now, what is the specific opportunity, and what is the recommended angle of approach"
}

RESEARCH PRIORITIES:
- Contacts: Find as many current legal team members as possible. Include:
  * Full C-suite of the company (CEO, CFO, COO, CISO — these are key influencers even if not legal)
  * Complete legal leadership team: CLO, GC, all Deputy/Associate GCs
  * All functional legal heads: Litigation, Legal Ops, Employment, IP, Privacy, Compliance, Regulatory, Corporate/M&A
  * Named litigators or attorneys visible in public filings, court records, or press releases
  * Anyone named as counsel in SEC filings or litigation documents
  * LinkedIn searches for [Company] + "General Counsel" or "Legal" in title
  Prioritize current role holders only. Flag departures. The goal is a COMPREHENSIVE contact list, not just the top 2-3 people.
- Litigation: include all matters from last 24 months. Flag any filed or updated in last 30 days with is_new true.
- Regulatory: include all agency actions from last 24 months. Flag recent actions with is_new true.
- Financial intel: pull from the most recent 10-K, 10-Q, earnings call transcript, or press release available.
- Personnel changes: include any GC, CLO, Head of Legal Ops, or Head of Litigation changes in last 18 months.
- Sales triggers: be specific. Reference actual case names, dollar amounts, filing dates where known. Make them actionable this week.`;
}

export function buildWeeklyDigestPrompt(accounts, researchData) {
  const today = new Date().toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" });
  const threeMonthsAgo = new Date();
  threeMonthsAgo.setMonth(threeMonthsAgo.getMonth() - 3);
  const threeMonthsAgoStr = threeMonthsAgo.toLocaleDateString("en-US", { year: "numeric", month: "long" });

  const accountSummaries = accounts
    .filter(a => researchData[a.id])
    .map(a => {
      const d = researchData[a.id];

      // Use new structured triggers if available, fall back to flat array
      const immediateTrigs = (d.immediate_triggers || []).map(t =>
        `[${t.urgency}] [${t.date}] ${t.trigger} -> ${t.sales_implication}`
      );
      const strategicTrigs = (d.strategic_triggers || []).map(t =>
        `[STRATEGIC] [${t.timeframe}] ${t.trigger} -> ${t.sales_implication}`
      );
      const flatTrigs = d.sales_triggers || [];
      const allTrigs = immediateTrigs.length || strategicTrigs.length
        ? [...immediateTrigs, ...strategicTrigs]
        : flatTrigs;

      // New filings from real sources
      const newFilings = [
        ...(d.litigation || []).filter(l => l.is_new),
        ...(d.regulatory || []).filter(r => r.is_new),
      ];

      // Contacts with confidence
      const verifiedContacts = (d.contacts || []).filter(c => c.confidence === "High");
      const unverifiedContacts = (d.contacts || []).filter(c => c.confidence !== "High");

      // Intelligence quality
      const intelQuality = d.intelligence_quality || "Unknown";
      const intelDate = d.intelligence_date || "Unknown";

      return [
        `ACCOUNT: ${a.name} (${a.industry}, ${a.location})`,
        `Open legal roles: ${(d.open_roles || []).map(r => r.title + (r.posted ? " (posted " + r.posted + ")" : "")).join(", ") || "None currently posted"}`,
        `Intelligence quality: ${intelQuality} | As of: ${intelDate}`,
        `Verified contacts (High confidence): ${verifiedContacts.map(c => c.name + " (" + c.tag + ")").join(", ") || "None verified"}`,
        `Unverified contacts (need LinkedIn check): ${unverifiedContacts.map(c => c.name + " (" + c.tag + ", " + (c.confidence || "?") + ")").join(", ") || "None"}`,
        `IMMEDIATE triggers (act now): ${immediateTrigs.slice(0, 3).join(" | ") || "None identified"}`,
        `STRATEGIC triggers (shape approach): ${strategicTrigs.slice(0, 2).join(" | ") || "None identified"}`,
        `New filings (last 30 days): ${newFilings.map(f => f.type + " [" + f.source + "]").join(", ") || "None"}`,
        `Active litigation (${(d.litigation || []).filter(l => !["Resolved","Settled","Dismissed"].includes(l.status)).length} cases): ${
          (d.litigation || [])
            .filter(l => !["Resolved","Settled","Dismissed"].includes(l.status))
            .slice(0, 5)
            .map(l => {
              const base = (l.case_name || l.type) + (l.case_number ? " (" + l.case_number + ")" : "");
              const counsel = l.outside_counsel_firm ? " — counsel: " + l.outside_counsel_firm : "";
              const partners = (l.lead_partners || []).slice(0,2).join(", ");
              const partnerStr = partners ? " (" + partners + ")" : "";
              const verified = l.courtlistener_verified ? " [COURT VERIFIED]" : "";
              return base + counsel + partnerStr + verified + (l.is_new ? " [NEW]" : "");
            }).join(" | ") || "None"
        }`,
        `Active regulatory: ${(d.regulatory || []).filter(r => !["Resolved","Closed"].includes(r.status)).map(r => r.type + (r.is_new ? " [NEW]" : "")).join(", ") || "None"}`,
        `Cost initiatives: ${d.financial_intel?.cost_initiatives || "None disclosed"}`,
        `Earnings signals: ${d.financial_intel?.earnings_signals || "None"}`,
        `M&A activity: ${d.financial_intel?.ma_activity || "None"}`,
        `Intel summary: ${d.intel_summary || "No summary"}`,
      ].join("\n");
    }).join("\n\n");

  return `You are a strategic legal sales advisor. Today is ${today}. You sell legal services (ALSP, flex talent, legal ops consulting, outside counsel advisory, eDiscovery) to corporate legal departments.

CRITICAL INSTRUCTIONS:
- Only reference triggers, events, and intelligence dated ${threeMonthsAgoStr} or more recent
- If intelligence quality is Low for an account, note that outreach should be verified before sending
- Always use the VERIFIED (High confidence) contacts for outreach recommendations
- Flag any contacts marked Medium or Low confidence with a reminder to verify on LinkedIn first
- Distinguish clearly between IMMEDIATE opportunities (act this week) and STRATEGIC positioning

ACCOUNT INTELLIGENCE (current as of today):

${accountSummaries}

Generate a weekly outreach plan. Return ONLY valid JSON, no markdown.

{
  "week_summary": "string — 3-4 sentences covering the most important IMMEDIATE opportunities this week. Name specific companies, reference specific recent events with dates. Distinguish between what needs action now vs. what shapes strategy.",
  "priority_accounts": [
    {
      "account_name": "string",
      "priority_rank": 1,
      "urgency": "one of: Critical | High | Medium",
      "priority_type": "one of: Immediate | Strategic",
      "trigger": "string — the SPECIFIC recent event making this week the right time. Must include a date. Must be from the last 90 days for Immediate, last 6 months for Strategic.",
      "trigger_date": "string — specific date or period of the trigger event",
      "contact": {
        "name": "string — use High confidence contacts only. If none, use Medium with verification note.",
        "title": "string",
        "confidence": "string — High/Medium/Low",
        "verification_note": "string — null if High confidence, otherwise 'Verify on LinkedIn before sending' "
      },
      "talking_point": "string — opening line referencing the specific trigger with date",
      "action": "string — what to do this week",
      "email": {
        "subject": "string — specific, references the actual recent event",
        "body": "string — 150-200 words. References the specific trigger event with date and dollar amounts where known. Does NOT reference anything from 2023 or 2024 unless it is ongoing and still directly relevant."
      },
      "linkedin_message": "string — under 100 words, references specific trigger"
    }
  ],
  "new_filings_alert": [
    {
      "account_name": "string",
      "filing_type": "string",
      "source": "string — SEC EDGAR, CourtListener, FTC, DOJ, or CFPB",
      "filed_date": "string",
      "summary": "string",
      "suggested_action": "string — specific action this week"
    }
  ],
  "personnel_watch": [
    {
      "account_name": "string",
      "person": "string",
      "change": "string",
      "change_date": "string",
      "window": "string — how long the window is open",
      "confidence": "string — how confident we are in this information"
    }
  ],
  "strategic_opportunities": [
    {
      "account_name": "string",
      "trend": "string — longer-term pattern or trend",
      "timeframe": "string",
      "recommended_angle": "string — how to position over next 3-6 months",
      "first_step": "string — what to do this week to start building toward this"
    }
  ],
  "quick_touches": [
    {
      "account_name": "string",
      "action": "string — specific low-effort action tied to something recent"
    }
  ]
}

PRIORITIZATION ORDER:
1. Accounts with new filings from real court/agency sources (is_new = true) — Critical
2. Accounts with High confidence contacts AND Critical/High immediate triggers — Critical/High
3. New senior legal hires (GC/CLO in last 90 days) — High (vendor panel window)
4. Active litigation entering discovery phase — High
5. Accounts with cost reduction programs AND active litigation — High
6. Strategic M&A or expansion opportunities — Medium

Select top 5 for priority_accounts.
Add up to 5 for new_filings_alert (real source filings only).
Add up to 5 for personnel_watch (recent changes only).
Add up to 3 for strategic_opportunities (longer-term plays).
Add 5 for quick_touches.`;
}

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
