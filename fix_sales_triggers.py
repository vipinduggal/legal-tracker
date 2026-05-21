import os

home = os.path.expanduser("~")
base = os.path.join(home, "legal-tracker")

# ── Step 1: Rewrite getLiveIntelligence in contactVerifier.js ──
verifier_path = os.path.join(base, "src", "contactVerifier.js")

with open(verifier_path, 'r') as f:
    content = f.read()

# Replace from getLiveIntelligence to end of file
start_marker = "\n/**\n * Use Perplexity to get LIVE sales triggers"
if start_marker in content:
    content = content[:content.index(start_marker)]

new_intel = '''

/**
 * Get LIVE, categorized sales triggers using Perplexity + Claude.
 * Perplexity searches for current intelligence (last 6 months).
 * Claude then structures it into two categories:
 *   - immediate: recent events driving urgent need (last 90 days)
 *   - strategic: longer-term trends affecting sales strategy (last 6 months)
 */
export async function getLiveIntelligence(account) {
  if (!PERPLEXITY_KEY) {
    logger.warn("No PERPLEXITY_API_KEY — skipping live intelligence");
    return null;
  }

  const today = new Date();
  const todayStr = today.toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" });
  const sixMonthsAgo = new Date(today);
  sixMonthsAgo.setMonth(sixMonthsAgo.getMonth() - 6);
  const sixMonthsAgoStr = sixMonthsAgo.toLocaleDateString("en-US", { year: "numeric", month: "long" });
  const threeMonthsAgo = new Date(today);
  threeMonthsAgo.setMonth(threeMonthsAgo.getMonth() - 3);
  const threeMonthsAgoStr = threeMonthsAgo.toLocaleDateString("en-US", { year: "numeric", month: "long" });

  // Step 1: Perplexity live search for current intelligence
  const perplexityQuery = `Today is ${todayStr}. Search for the most recent news and events about ${account.name} (${account.industry}) from ${sixMonthsAgoStr} to today only.

Find:
1. Any new lawsuits, regulatory investigations, or government actions filed or announced since ${threeMonthsAgoStr}
2. Recent earnings calls or financial results from the last 2 quarters — what did leadership say about costs, legal spend, or headcount?
3. Any restructuring, layoffs, cost reduction programs, or efficiency initiatives announced since ${sixMonthsAgoStr}
4. Any M&A activity (acquisitions, mergers, divestitures) announced since ${sixMonthsAgoStr}
5. Any senior legal leadership changes (CLO, GC, Head of Legal Ops) since ${sixMonthsAgoStr}
6. Any major contract wins, new markets, or business expansions since ${sixMonthsAgoStr} that would increase legal workload

Be specific: include dates, dollar amounts, and names. Only report events from ${sixMonthsAgoStr} to today. If you find nothing current for a category, say so explicitly.`;

  let perplexityAnswer = "";
  let citations = [];

  try {
    const response = await axios.post(
      "https://api.perplexity.ai/chat/completions",
      {
        model: "sonar",
        messages: [
          {
            role: "system",
            content: `You are a legal intelligence researcher. Today is ${todayStr}. Only report verified information from ${sixMonthsAgoStr} to today. Be specific with dates. Do not reference anything older than ${sixMonthsAgoStr}.`,
          },
          { role: "user", content: perplexityQuery },
        ],
        max_tokens: 1500,
      },
      {
        headers: {
          Authorization: "Bearer " + PERPLEXITY_KEY,
          "Content-Type": "application/json",
        },
        timeout: 25000,
      }
    );

    perplexityAnswer = response.data?.choices?.[0]?.message?.content || "";
    citations = response.data?.citations || [];

    if (!perplexityAnswer || perplexityAnswer.length < 50) {
      logger.warn("Perplexity returned empty response for " + account.name);
      return null;
    }

    logger.info("Perplexity live search complete for " + account.name + " (" + perplexityAnswer.length + " chars)");

  } catch (err) {
    logger.warn("Perplexity live search failed for " + account.name, { error: err.message });
    return null;
  }

  // Step 2: Use Anthropic to structure the Perplexity answer into categorized triggers
  try {
    const Anthropic = (await import("@anthropic-ai/sdk")).default;
    const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

    const structurePrompt = `You are a legal sales intelligence analyst. I have gathered the following recent intelligence about ${account.name} (${account.industry}, ${account.location}) from live web search conducted today, ${todayStr}.

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
}`;

    const response = await client.messages.create({
      model: "claude-sonnet-4-5",
      max_tokens: 2000,
      messages: [{ role: "user", content: structurePrompt }],
    });

    const raw = response.content
      .filter(b => b.type === "text")
      .map(b => b.text)
      .join("")
      .replace(/^```json\s*/i, "")
      .replace(/^```\s*/i, "")
      .replace(/```\s*$/i, "")
      .trim();

    const structured = JSON.parse(raw);
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
  }
}
''';

content += new_intel

with open(verifier_path, 'w') as f:
    f.write(content)
print("Done — getLiveIntelligence rewritten with Perplexity + Claude structuring")

# ── Step 2: Update researcher.js to use new structured triggers ──
researcher_path = os.path.join(base, "src", "researcher.js")

with open(researcher_path, 'r') as f:
    researcher = f.read()

old_apply = '''    // Replace Claude training-data triggers with live Perplexity intelligence
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
      }'''

new_apply = '''    // Replace Claude training-data triggers with structured live intelligence
      const liveIntel = await getLiveIntelligence(account);
      if (liveIntel) {
        // Apply structured immediate triggers
        const immediateTrigs = (liveIntel.immediate_triggers || []).map(t =>
          `IMMEDIATE [${t.urgency}] [${t.date}] ${t.trigger} — ${t.sales_implication}`
        );

        // Apply structured strategic triggers
        const strategicTrigs = (liveIntel.strategic_triggers || []).map(t =>
          `STRATEGIC [${t.timeframe}] ${t.trigger} — ${t.sales_implication}`
        );

        // Store both as flat array for backwards compat + structured for new UI
        parsed.sales_triggers = [...immediateTrigs, ...strategicTrigs];
        parsed.immediate_triggers = liveIntel.immediate_triggers || [];
        parsed.strategic_triggers = liveIntel.strategic_triggers || [];
        parsed.intelligence_quality = liveIntel.intelligence_quality;
        parsed.intelligence_date = liveIntel.intelligence_date;

        // Override financial intel with live data
        if (liveIntel.financial_intel) {
          parsed.financial_intel = parsed.financial_intel || {};
          const fi = liveIntel.financial_intel;
          if (fi.earnings_signals) parsed.financial_intel.earnings_signals = fi.earnings_signals;
          if (fi.cost_initiatives) parsed.financial_intel.cost_initiatives = fi.cost_initiatives;
          if (fi.ma_activity) parsed.financial_intel.ma_activity = fi.ma_activity;
          if (fi.latest_filing) parsed.financial_intel.latest_filing = fi.latest_filing;
        }

        parsed.live_intel_retrieved = liveIntel.retrievedAt;
        parsed.live_intel_sources = liveIntel.sources || [];

        const iCount = (liveIntel.immediate_triggers || []).length;
        const sCount = (liveIntel.strategic_triggers || []).length;
        logger.info(`Live triggers applied for ${account.name}: ${iCount} immediate, ${sCount} strategic (${liveIntel.intelligence_quality} quality)`);
      }'''

if old_apply in researcher:
    researcher = researcher.replace(old_apply, new_apply)
    with open(researcher_path, 'w') as f:
        f.write(researcher)
    print("Done — researcher.js updated with structured trigger application")
else:
    print("WARNING — could not find old trigger application in researcher.js")
    print("You may need to manually update the trigger section")

# ── Step 3: Update dashboard.html to show categorized triggers ──
dashboard_path = os.path.join(base, "src", "dashboard.html")

with open(dashboard_path, 'r') as f:
    dash = f.read()

old_triggers_tab = """  }else if(tab==='triggers'){
    var tr=r.sales_triggers||[];var pc=r.personnel_changes||[];
    if(!tr.length&&!pc.length){c.innerHTML=emp('No sales triggers yet');return;}
    var h='';
    if(tr.length){h+='<div class="sl">Sales triggers ('+tr.length+')</div>';tr.forEach(function(t){h+='<div class="trg">'+t+'</div>';});}
    if(pc.length){h+='<div class="sl" style="margin-top:12px">Personnel changes</div>';pc.forEach(function(p){h+='<div class="card"><div style="font-size:13px;font-weight:600;margin-bottom:3px">'+p.name+'</div><div style="font-size:12px;color:#6B7280;margin-bottom:5px">'+p.change+'</div><div style="font-size:12px;color:#0A7C6E">'+p.significance+'</div></div>';});}
    c.innerHTML=h;
  }"""

new_triggers_tab = """  }else if(tab==='triggers'){
    var imm=r.immediate_triggers||[];
    var str=r.strategic_triggers||[];
    var tr=r.sales_triggers||[];
    var pc=r.personnel_changes||[];
    var iq=r.intelligence_quality||'';
    var id=r.intelligence_date||'';
    var hasNew=imm.length||str.length;
    var hasFallback=!hasNew&&tr.length;
    if(!hasNew&&!hasFallback&&!pc.length){c.innerHTML=emp('No sales triggers yet');return;}
    var h='';
    // Quality badge
    if(id){
      var qcls=iq==='High'?'ch':iq==='Medium'?'cm':'cl';
      h+='<div style="display:flex;align-items:center;gap:8px;margin-bottom:14px">';
      h+='<span style="font-size:11px;color:var(--g5)">Intelligence as of: <strong>'+id+'</strong></span>';
      if(iq)h+='<span class="'+qcls+'" style="font-size:11px">'+iq+' quality</span>';
      h+='</div>';
    }
    // Immediate triggers
    if(imm.length){
      h+='<div class="sl">Immediate triggers — act this week ('+imm.length+')</div>';
      imm.forEach(function(t){
        var ucls=t.urgency==='Critical'?'br':t.urgency==='High'?'ba':'bb';
        h+='<div style="background:#fff;border:1px solid var(--g2);border-left:3px solid '+(t.urgency==='Critical'?'#991B1B':t.urgency==='High'?'#B45309':'#1E56A0')+';border-radius:var(--rl);padding:12px;margin-bottom:8px">';
        h+='<div style="display:flex;align-items:center;gap:8px;margin-bottom:5px">';
        h+='<span class="bdg '+ucls+'">'+t.urgency+'</span>';
        h+='<span style="font-size:11px;color:var(--g4)">'+t.date+'</span>';
        h+='</div>';
        h+='<div style="font-size:13px;font-weight:500;color:var(--g9);margin-bottom:5px">'+t.trigger+'</div>';
        h+='<div style="font-size:12px;color:var(--teal)">&#8594; '+t.sales_implication+'</div>';
        h+='</div>';
      });
    }
    // Strategic triggers
    if(str.length){
      h+='<div class="sl" style="margin-top:'+(imm.length?'16':'0')+'px">Strategic trends — shape your approach ('+str.length+')</div>';
      str.forEach(function(t){
        h+='<div style="background:#fff;border:1px solid var(--g2);border-left:3px solid #5B45C7;border-radius:var(--rl);padding:12px;margin-bottom:8px">';
        h+='<div style="display:flex;align-items:center;gap:8px;margin-bottom:5px">';
        h+='<span class="bdg" style="background:#F0EEFE;color:#5B45C7">Strategic</span>';
        h+='<span style="font-size:11px;color:var(--g4)">'+t.timeframe+'</span>';
        if(t.angle)h+='<span style="font-size:11px;color:var(--g5);background:var(--g1);padding:1px 7px;border-radius:10px">'+t.angle+'</span>';
        h+='</div>';
        h+='<div style="font-size:13px;font-weight:500;color:var(--g9);margin-bottom:5px">'+t.trigger+'</div>';
        h+='<div style="font-size:12px;color:var(--teal)">&#8594; '+t.sales_implication+'</div>';
        h+='</div>';
      });
    }
    // Fallback: old flat triggers
    if(hasFallback&&!hasNew){
      h+='<div class="sl">Sales triggers</div>';
      tr.forEach(function(t){h+='<div class="trg">'+t+'</div>';});
    }
    // Personnel changes
    if(pc.length){
      h+='<div class="sl" style="margin-top:16px">Personnel changes</div>';
      pc.forEach(function(p){h+='<div class="card"><div style="font-size:13px;font-weight:600;margin-bottom:3px">'+p.name+'</div><div style="font-size:12px;color:#6B7280;margin-bottom:5px">'+p.change+'</div><div style="font-size:12px;color:#0A7C6E">'+p.significance+'</div></div>';});
    }
    c.innerHTML=h;
  }"""

if old_triggers_tab in dash:
    dash = dash.replace(old_triggers_tab, new_triggers_tab)
    with open(dashboard_path, 'w') as f:
        f.write(dash)
    print("Done — dashboard.html updated with categorized trigger display")
else:
    print("WARNING — could not find triggers tab in dashboard.html")

print("")
print("="*50)
print("SALES TRIGGERS UPGRADE COMPLETE")
print("="*50)
print("")
print("What changed:")
print("  1. Perplexity now searches specifically for last 6 months only")
print("  2. Claude structures raw search results into two categories:")
print("     - IMMEDIATE: last 90 days, specific dates, urgency rating")
print("     - STRATEGIC: last 6 months, trends, positioning angle")
print("  3. Dashboard shows color-coded cards by urgency and category")
print("  4. Each trigger has a date, sales implication, and urgency")
print("  5. Intelligence quality badge shows High/Medium/Low")
print("")
print("Test on one account:")
print('  npm run research:account "AMD" -- --force')
print("")
print("Then run all accounts:")
print("  npm run research:all -- --force")
