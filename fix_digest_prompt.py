import os

home = os.path.expanduser("~")
base = os.path.join(home, "legal-tracker")
prompts_path = os.path.join(base, "src", "prompts.js")

with open(prompts_path, 'r') as f:
    content = f.read()

# Find and replace the buildWeeklyDigestPrompt function
old_digest_fn_start = "export function buildWeeklyDigestPrompt(accounts, researchData) {"

if old_digest_fn_start not in content:
    print("ERROR: Could not find buildWeeklyDigestPrompt in prompts.js")
    exit(1)

# Find where the function starts and ends
start_idx = content.index(old_digest_fn_start)
# Find the last closing brace of the file (end of function)
end_idx = len(content)

# Keep everything before this function
before = content[:start_idx]

new_digest_fn = '''export function buildWeeklyDigestPrompt(accounts, researchData) {
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
        `Intelligence quality: ${intelQuality} | As of: ${intelDate}`,
        `Verified contacts (High confidence): ${verifiedContacts.map(c => c.name + " (" + c.tag + ")").join(", ") || "None verified"}`,
        `Unverified contacts (need LinkedIn check): ${unverifiedContacts.map(c => c.name + " (" + c.tag + ", " + (c.confidence || "?") + ")").join(", ") || "None"}`,
        `IMMEDIATE triggers (act now): ${immediateTrigs.slice(0, 3).join(" | ") || "None identified"}`,
        `STRATEGIC triggers (shape approach): ${strategicTrigs.slice(0, 2).join(" | ") || "None identified"}`,
        `New filings (last 30 days): ${newFilings.map(f => f.type + " [" + f.source + "]").join(", ") || "None"}`,
        `Active litigation: ${(d.litigation || []).filter(l => !["Resolved","Settled","Dismissed"].includes(l.status)).map(l => l.type + (l.is_new ? " [NEW]" : "")).join(", ") || "None"}`,
        `Active regulatory: ${(d.regulatory || []).filter(r => !["Resolved","Closed"].includes(r.status)).map(r => r.type + (r.is_new ? " [NEW]" : "")).join(", ") || "None"}`,
        `Cost initiatives: ${d.financial_intel?.cost_initiatives || "None disclosed"}`,
        `Earnings signals: ${d.financial_intel?.earnings_signals || "None"}`,
        `M&A activity: ${d.financial_intel?.ma_activity || "None"}`,
        `Intel summary: ${d.intel_summary || "No summary"}`,
      ].join("\\n");
    }).join("\\n\\n");

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
'''

content = before + new_digest_fn

with open(prompts_path, 'w') as f:
    f.write(content)

print("Done — buildWeeklyDigestPrompt fully rewritten")
print("")
print("Key improvements:")
print("  1. Uses immediate_triggers and strategic_triggers separately")
print("  2. Only references triggers dated last 90 days (immediate) or 6 months (strategic)")
print("  3. Contacts: uses High confidence only, flags Medium/Low for LinkedIn verification")
print("  4. New section: strategic_opportunities for longer-term plays")
print("  5. New filings include source (EDGAR, CourtListener, FTC etc)")
print("  6. Explicit instruction: do NOT reference 2023/2024 data")
print("")
print("Also updating digest.html to show strategic_opportunities...")

# Update digest.html to show the new strategic_opportunities section
digest_path = os.path.join(base, "src", "digest.html")
with open(digest_path, 'r') as f:
    digest = f.read()

# Add strategic opportunities section after quick_touches
old_qt = """  var qt=d.quick_touches||[];
  if(qt.length){h+='<div class="sec">Quick touches</div><div class="ql">';qt.forEach(function(q){h+='<div class="qi"><span class="qn">'+esc(q.account_name)+'</span><span class="qac">'+esc(q.action)+'</span></div>';});h+='</div>';}"""

new_qt = """  var so=d.strategic_opportunities||[];
  if(so.length){
    h+='<div class="sec">Strategic opportunities &mdash; 3-6 month plays</div>';
    so.forEach(function(s){
      h+='<div style="background:#fff;border:1px solid var(--g2);border-left:4px solid #5B45C7;border-radius:14px;padding:14px 16px;margin-bottom:10px">';
      h+='<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px"><strong style="font-size:13px">'+esc(s.account_name)+'</strong><span style="font-size:11px;background:#F0EEFE;color:#5B45C7;padding:2px 8px;border-radius:20px">Strategic</span><span style="font-size:11px;color:var(--g4)">'+esc(s.timeframe)+'</span></div>';
      h+='<div style="font-size:13px;color:var(--g7);margin-bottom:6px">'+esc(s.trend)+'</div>';
      if(s.recommended_angle)h+='<div style="font-size:12px;color:var(--teal);margin-bottom:4px">Position as: '+esc(s.recommended_angle)+'</div>';
      if(s.first_step)h+='<div style="font-size:12px;color:var(--amber);font-weight:500">This week: '+esc(s.first_step)+'</div>';
      h+='</div>';
    });
  }
  var qt=d.quick_touches||[];
  if(qt.length){h+='<div class="sec">Quick touches</div><div class="ql">';qt.forEach(function(q){h+='<div class="qi"><span class="qn">'+esc(q.account_name)+'</span><span class="qac">'+esc(q.action)+'</span></div>';});h+='</div>';}"""

if old_qt in digest:
    digest = digest.replace(old_qt, new_qt)
    with open(digest_path, 'w') as f:
        f.write(digest)
    print("Done — digest.html updated with strategic_opportunities section")
else:
    print("WARNING — could not update digest.html (pattern not found)")

print("")
print("Next steps:")
print("  1. Run research to get fresh structured triggers:")
print('     npm run research:account "AMD"')
print("  2. Generate a new digest to test:")
print("     npm run digest:weekly")
print("  3. Open http://localhost:3000/digest to see the new format")
print("  4. Then run all accounts:")
print("     npm run research:all -- --force")
