import os

home = os.path.expanduser("~")
base = os.path.join(home, "legal-tracker")
verifier_path = os.path.join(base, "src", "contactVerifier.js")

with open(verifier_path, 'r') as f:
    content = f.read()

# ── Step 1: Add open roles search to getLiveIntelligence ──
old_searches = '''  const searches = [
    {
      label: "litigation",
      query: `What lawsuits, legal disputes, patent infringement cases, class actions, or regulatory investigations involve ${account.name} in ${sixMonthsAgoStr} to ${todayStr}? Include case names, filing dates, courts, and dollar amounts where known. Focus on NEW cases filed in the last 6 months.`,
    },
    {
      label: "financial",
      query: `What did ${account.name} report in their most recent earnings call or quarterly results in 2026? Focus on: legal costs, litigation reserves, loss contingencies, restructuring charges, cost reduction programs, M&A deals, and any comments about legal department spending or headcount. Include specific dollar amounts and dates.`,
    },
    {
      label: "business",
      query: `What major business changes has ${account.name} announced in the last 6 months (${sixMonthsAgoStr} to ${todayStr})? Focus on: acquisitions, mergers, divestitures, major new contracts, expansion into new markets, regulatory approvals or rejections, export controls, government investigations, or leadership changes in legal/compliance roles.`,
    },
  ];'''

new_searches = '''  const searches = [
    {
      label: "litigation",
      query: `What lawsuits, legal disputes, patent infringement cases, class actions, or regulatory investigations involve ${account.name} in ${sixMonthsAgoStr} to ${todayStr}? Include case names, filing dates, courts, and dollar amounts where known. Focus on NEW cases filed in the last 6 months.`,
    },
    {
      label: "financial",
      query: `What did ${account.name} report in their most recent earnings call or quarterly results in 2026? Focus on: legal costs, litigation reserves, loss contingencies, restructuring charges, cost reduction programs, M&A deals, and any comments about legal department spending or headcount. Include specific dollar amounts and dates.`,
    },
    {
      label: "business",
      query: `What major business changes has ${account.name} announced in the last 6 months (${sixMonthsAgoStr} to ${todayStr})? Focus on: acquisitions, mergers, divestitures, major new contracts, expansion into new markets, regulatory approvals or rejections, export controls, government investigations, or leadership changes in legal/compliance roles.`,
    },
    {
      label: "open_roles",
      query: `What legal department job openings does ${account.name} currently have posted as of ${todayStr}? Search LinkedIn Jobs, their company careers page, Indeed, and other job boards. Look for any roles with these keywords in the title: legal, counsel, attorney, paralegal, compliance, eDiscovery, legal operations, privacy, regulatory, contract manager, litigation. For each open role list: exact job title, when posted if known, location, and whether it is remote or in-office. If no legal roles are currently posted, say so explicitly.`,
    },
  ];'''

if old_searches in content:
    content = content.replace(old_searches, new_searches)
    print("Done — open roles search added to Perplexity pipeline")
else:
    print("WARNING — searches pattern not found")

# ── Step 2: Parse open roles from Perplexity answer ──
old_intel_return = '''    const structured = {
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
    return structured;'''

new_intel_return = '''    // Parse open roles from Perplexity answer
    const openRolesSection = perplexityAnswer.includes("=== OPEN_ROLES ===")
      ? perplexityAnswer.split("=== OPEN_ROLES ===")[1]?.split("===")[0] || ""
      : "";

    let openRoles = [];
    if (openRolesSection && openRolesSection.length > 30) {
      try {
        const rolesPrompt = `Extract job openings from this text about ${account.name} legal department hiring.

TEXT: ${openRolesSection.slice(0, 1500)}

Return a JSON array only. Each item: {"title":"exact job title","posted":"when posted or null","location":"city or Remote or null","signal":"one sentence on what this hiring need means for legal services sales"}

If no roles found return: []`;

        const rolesResp = await client.messages.create({
          model: "claude-sonnet-4-5",
          max_tokens: 800,
          messages: [{ role: "user", content: rolesPrompt }],
        });
        const rolesRaw = rolesResp.content.filter(b => b.type === "text").map(b => b.text).join("")
          .replace(/^```json\\s*/i, "").replace(/^```\\s*/i, "").replace(/```\\s*$/i, "").trim();
        const parsed = JSON.parse(rolesRaw);
        openRoles = Array.isArray(parsed) ? parsed : [];
        if (openRoles.length) {
          logger.info(`Open roles found for ${account.name}: ${openRoles.length} positions`);
        }
      } catch(rolesErr) {
        logger.warn(`Open roles parsing failed for ${account.name}: ${rolesErr.message}`);
      }
    }

    // Add open roles as immediate triggers if any found
    const roleTrigs = openRoles.map(r => ({
      trigger: `Open role: ${r.title}${r.posted ? " (posted " + r.posted + ")" : ""}${r.location ? " — " + r.location : ""}`,
      date: r.posted || todayStr,
      sales_implication: r.signal || "Active hiring signals legal team capacity gap — opportunity for flex talent or ALSP support",
      urgency: "Medium",
    }));

    const allImmediate = [...(Array.isArray(immediateTrigs) ? immediateTrigs : []), ...roleTrigs];

    const structured = {
      immediate_triggers: allImmediate,
      strategic_triggers: Array.isArray(strategicTrigs) ? strategicTrigs : [],
      financial_intel: financialIntel,
      open_roles: openRoles,
      intelligence_date: todayStr,
      intelligence_quality: quality,
      sources: citations.slice(0, 3),
      retrievedAt: new Date().toISOString(),
    };

    const iCount = structured.immediate_triggers.length;
    const sCount = structured.strategic_triggers.length;
    const rCount = openRoles.length;
    logger.info(`Structured triggers for ${account.name}: ${iCount} immediate, ${sCount} strategic, ${rCount} open roles (${quality})`);
    return structured;'''

if old_intel_return in content:
    content = content.replace(old_intel_return, new_intel_return)
    print("Done — open roles parsing added")
else:
    print("WARNING — intel return pattern not found")

with open(verifier_path, 'w') as f:
    f.write(content)

# ── Step 3: Apply open_roles in researcher.js ──
researcher_path = os.path.join(base, "src", "researcher.js")
with open(researcher_path, 'r') as f:
    researcher = f.read()

old_apply_end = '''        const iCount = (liveIntel.immediate_triggers || []).length;
        const sCount = (liveIntel.strategic_triggers || []).length;
        logger.info(`Live triggers applied for ${account.name}: ${iCount} immediate, ${sCount} strategic (${liveIntel.intelligence_quality} quality)`);'''

new_apply_end = '''        // Apply open roles
        if (liveIntel.open_roles && liveIntel.open_roles.length) {
          parsed.open_roles = liveIntel.open_roles;
        }

        const iCount = (liveIntel.immediate_triggers || []).length;
        const sCount = (liveIntel.strategic_triggers || []).length;
        const rCount = (liveIntel.open_roles || []).length;
        logger.info(`Live triggers applied for ${account.name}: ${iCount} immediate, ${sCount} strategic, ${rCount} open roles (${liveIntel.intelligence_quality} quality)`);'''

if old_apply_end in researcher:
    researcher = researcher.replace(old_apply_end, new_apply_end)
    with open(researcher_path, 'w') as f:
        f.write(researcher)
    print("Done — researcher.js updated to save open_roles")
else:
    print("WARNING — researcher apply pattern not found")

# ── Step 4: Add Open Roles tab to dashboard ──
dashboard_path = os.path.join(base, "src", "dashboard.html")
with open(dashboard_path, 'r') as f:
    dash = f.read()

# Add Open Roles to the tabs definition
old_tabs = "var tbs=[{id:'contacts',l:'Contacts',n:(r.contacts||[]).length},{id:'tech',l:'Technology',n:(r.tech||[]).length},{id:'counsel',l:'Counsel',n:(r.counsel||[]).length},{id:'alsp',l:'ALSPs',n:(r.alsp||[]).length+(r.flex||[]).length},{id:'litigation',l:'Litigation',n:(r.litigation||[]).length},{id:'regulatory',l:'Regulatory',n:(r.regulatory||[]).length},{id:'financial',l:'Financial Intel',n:null},{id:'triggers',l:'Sales Triggers',n:(r.sales_triggers||[]).length},{id:'outreach',l:'Outreach',n:null}];"

new_tabs = "var tbs=[{id:'contacts',l:'Contacts',n:(r.contacts||[]).length},{id:'openroles',l:'Open Roles',n:(r.open_roles||[]).length},{id:'tech',l:'Technology',n:(r.tech||[]).length},{id:'counsel',l:'Counsel',n:(r.counsel||[]).length},{id:'alsp',l:'ALSPs',n:(r.alsp||[]).length+(r.flex||[]).length},{id:'litigation',l:'Litigation',n:(r.litigation||[]).length},{id:'regulatory',l:'Regulatory',n:(r.regulatory||[]).length},{id:'financial',l:'Financial Intel',n:null},{id:'triggers',l:'Sales Triggers',n:(r.sales_triggers||[]).length},{id:'outreach',l:'Outreach',n:null}];"

if old_tabs in dash:
    dash = dash.replace(old_tabs, new_tabs)
    print("Done — Open Roles tab added to dashboard")
else:
    print("WARNING — tabs pattern not found in dashboard")

# Add Open Roles tab content renderer
old_triggers_tab = "  }else if(tab==='triggers'){"
new_roles_tab = """  }else if(tab==='openroles'){
    var roles=r.open_roles||[];
    if(!roles.length){
      c.innerHTML='<div class="ep"><p>No open legal roles found</p><p style="font-size:12px;margin-top:6px;color:var(--g5)">Research this account to check for current job postings</p></div>';
      return;
    }
    var roleSignals={
      'contract':'ALSP contract review opportunity',
      'ediscovery':'eDiscovery outsourcing signal',
      'litigation':'Litigation support surge',
      'legal ops':'Legal operations transformation',
      'privacy':'Privacy program build-out',
      'compliance':'Compliance program expansion',
      'counsel':'In-house capacity gap',
      'attorney':'Legal team scaling',
      'paralegal':'Litigation or contract volume surge',
    };
    var h='<div class="sl">Open legal positions ('+roles.length+')</div>';
    roles.forEach(function(role){
      var sig='';
      var titleLow=(role.title||'').toLowerCase();
      Object.keys(roleSignals).forEach(function(k){if(titleLow.includes(k))sig=roleSignals[k];});
      h+='<div style="background:#fff;border:1px solid var(--g2);border-left:3px solid #5B45C7;border-radius:var(--rl);padding:13px 16px;margin-bottom:8px">';
      h+='<div style="display:flex;align-items:center;gap:8px;margin-bottom:5px">';
      h+='<span style="font-size:13px;font-weight:600;color:var(--g9)">'+role.title+'</span>';
      if(role.posted)h+='<span style="font-size:11px;color:var(--g4)">'+role.posted+'</span>';
      if(role.location)h+='<span style="font-size:11px;background:var(--g1);color:var(--g6);padding:1px 7px;border-radius:10px">'+role.location+'</span>';
      h+='</div>';
      if(sig||role.signal)h+='<div style="font-size:12px;color:var(--teal)">&#8594; '+(role.signal||sig)+'</div>';
      h+='</div>';
    });
    // Summary insight
    var roleTypes=roles.map(function(r){return (r.title||'').toLowerCase();});
    var hasEdiscovery=roleTypes.some(function(t){return t.includes('ediscovery')||t.includes('e-discovery');});
    var hasOps=roleTypes.some(function(t){return t.includes('ops')||t.includes('operations');});
    var hasLitigation=roleTypes.some(function(t){return t.includes('litigation')||t.includes('paralegal');});
    var hasContract=roleTypes.some(function(t){return t.includes('contract')||t.includes('attorney');});
    var insights=[];
    if(hasEdiscovery)insights.push('eDiscovery hiring = likely evaluating vendors');
    if(hasOps)insights.push('Legal ops hiring = transformation initiative underway');
    if(hasLitigation)insights.push('Litigation hiring = document review surge');
    if(hasContract)insights.push('Contract attorney hiring = contract volume overflow');
    if(insights.length){
      h+='<div style="background:linear-gradient(135deg,#FFF8E7,#FFFBF0);border:1px solid #FDE68A;border-radius:var(--rl);padding:12px 14px;margin-top:8px">';
      h+='<div style="font-size:10px;font-weight:700;color:var(--amber);text-transform:uppercase;letter-spacing:.08em;margin-bottom:4px">Sales signal</div>';
      insights.forEach(function(i){h+='<div style="font-size:13px;color:var(--g7);margin-bottom:3px">&#8226; '+i+'</div>';});
      h+='</div>';
    }
    c.innerHTML=h;
  """ + old_triggers_tab

if old_triggers_tab in dash:
    dash = dash.replace(old_triggers_tab, new_roles_tab)
    print("Done — Open Roles tab renderer added to dashboard")
else:
    print("WARNING — triggers tab not found in dashboard for insertion")

with open(dashboard_path, 'w') as f:
    f.write(dash)

# ── Step 5: Add open roles to digest prompt ──
prompts_path = os.path.join(base, "src", "prompts.js")
with open(prompts_path, 'r') as f:
    prompts = f.read()

old_contact_summary = "        `ACCOUNT: ${a.name} (${a.industry}, ${a.location})`,"
new_contact_summary = """        `ACCOUNT: ${a.name} (${a.industry}, ${a.location})`,
        `Open legal roles: ${(d.open_roles || []).map(r => r.title + (r.posted ? " (posted " + r.posted + ")" : "")).join(", ") || "None currently posted"}`,"""

if old_contact_summary in prompts:
    prompts = prompts.replace(old_contact_summary, new_contact_summary)
    with open(prompts_path, 'w') as f:
        f.write(prompts)
    print("Done — open roles added to weekly digest prompt")
else:
    print("WARNING — digest prompt pattern not found")

print("")
print("="*50)
print("OPEN ROLES FEATURE INSTALLED")
print("="*50)
print("")
print("What was added:")
print("  1. Fourth Perplexity search: current legal job postings")
print("  2. Claude parses postings into structured roles with signals")
print("  3. Open Roles tab in dashboard (between Contacts and Technology)")
print("  4. Open roles added as immediate triggers")
print("  5. Open roles included in weekly digest")
print("")
print("Restart: pkill -f 'node src/index.js' && npm start")
print("")
print("Then test:")
print('  npm run research:account "Microsoft"')
print("  Check the Open Roles tab in the dashboard")
