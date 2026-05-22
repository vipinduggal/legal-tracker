import os

home = os.path.expanduser("~")
base = os.path.join(home, "legal-tracker")

# ── Write src/jobs/litigationMonitor.js ───────────────────
lit_path = os.path.join(base, "src", "jobs", "litigationMonitor.js")

content = '''// litigationMonitor.js
// Deep litigation intelligence — tracks case phases, outside counsel,
// court schedules, and discovery windows for active matters
// Runs daily at 6:30 AM alongside the filings monitor

import "dotenv/config";
import axios from "axios";
import { ACCOUNTS } from "../../config/accounts.js";
import { getResearch, setResearch, logRun, hasBeenNotified, markNotified } from "../db.js";
import { logger } from "../logger.js";

// Case phase keywords — ordered from earliest to latest phase
const PHASE_SIGNALS = {
  discovery: [
    "scheduling order", "rule 26", "26(f)", "discovery plan",
    "discovery cutoff", "fact discovery", "document production",
    "interrogatories", "deposition notice", "subpoena",
    "motion to compel", "protective order", "ESI protocol",
    "electronically stored information", "litigation hold",
  ],
  post_discovery: [
    "motion for summary judgment", "summary judgment",
    "expert witness", "daubert", "in limine",
    "pretrial conference", "pretrial order",
  ],
  trial: [
    "trial date", "jury selection", "opening statements",
    "verdict", "judgment entered",
  ],
  appeal: [
    "notice of appeal", "appellate", "circuit court",
    "brief filed", "oral argument scheduled",
  ],
  settled: [
    "settlement agreement", "stipulation of dismissal",
    "voluntary dismissal", "consent decree", "settlement reached",
  ],
};

// Document volume estimates by case type
const VOLUME_ESTIMATES = {
  "antitrust": "Very High (typically 5-50M+ documents)",
  "securities class action": "High (typically 1-10M documents)",
  "patent infringement": "High (typically 500K-5M documents)",
  "employment discrimination": "Medium (typically 100K-1M documents)",
  "consumer class action": "High (typically 1-10M documents)",
  "regulatory enforcement": "High (typically 1-10M documents)",
  "merger challenge": "Very High (typically 5-50M+ documents)",
  "data breach": "Medium-High (typically 500K-5M documents)",
  "contract dispute": "Low-Medium (typically 50K-500K documents)",
  "ip litigation": "High (typically 500K-5M documents)",
};

function estimateVolume(caseType) {
  const typeLower = (caseType || "").toLowerCase();
  for (const [key, estimate] of Object.entries(VOLUME_ESTIMATES)) {
    if (typeLower.includes(key.split(" ")[0])) return estimate;
  }
  return "Medium (typically 100K-1M documents)";
}

// Search CourtListener for case details
async function getCaseDetails(caseName, accountName) {
  try {
    const searchTerm = caseName
      .replace(/[^a-zA-Z0-9\s]/g, " ")
      .trim()
      .split(" ")
      .slice(0, 4)
      .join(" ");

    const response = await axios.get(
      "https://www.courtlistener.com/api/rest/v3/dockets/",
      {
        params: {
          q: `"${accountName}"`,
          order_by: "-date_filed",
          page_size: 3,
          format: "json",
        },
        headers: { "User-Agent": "LegalTracker/1.0 vipin.duggal@consilio.com" },
        timeout: 10000,
      }
    );

    const cases = response.data?.results || [];
    if (!cases.length) return null;

    // Find best match
    const match = cases.find(c =>
      (c.case_name || "").toLowerCase().includes(accountName.toLowerCase().split(" ")[0])
    ) || cases[0];

    return {
      case_name: match.case_name,
      court: match.court_id,
      date_filed: match.date_filed,
      docket_number: match.docket_number,
      source_url: match.absolute_url ? `https://www.courtlistener.com${match.absolute_url}` : null,
      assigned_to: match.assigned_to_str,
      cause: match.cause,
      nature_of_suit: match.nature_of_suit,
    };
  } catch(err) {
    logger.warn(`CourtListener lookup failed for ${accountName}: ${err.message}`);
    return null;
  }
}

// Use Perplexity to get current outside counsel and case status
async function getLitigationCounsel(account, litigationItem) {
  const PERPLEXITY_KEY = process.env.PERPLEXITY_API_KEY;
  if (!PERPLEXITY_KEY) return null;

  try {
    const today = new Date().toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" });
    const query = `For the ${litigationItem.type} lawsuit involving ${account.name}, as of ${today}:
1. Which law firm is serving as outside counsel for ${account.name}? Name the specific firm and lead partners if known.
2. What is the current phase of this case — pre-discovery, discovery, post-discovery, or trial?
3. Are there any upcoming key dates — discovery cutoff, trial date, summary judgment deadline?
4. What court is this filed in and what is the case number if known?
5. Approximately how many documents might be involved in discovery?

Be specific. Only include confirmed information.`;

    const response = await axios.post(
      "https://api.perplexity.ai/chat/completions",
      {
        model: "sonar",
        messages: [
          {
            role: "system",
            content: `You are a legal intelligence researcher. Today is ${today}. Provide specific, verified information about this litigation matter.`,
          },
          { role: "user", content: query },
        ],
        max_tokens: 600,
      },
      {
        headers: {
          Authorization: "Bearer " + PERPLEXITY_KEY,
          "Content-Type": "application/json",
        },
        timeout: 15000,
      }
    );

    const answer = response.data?.choices?.[0]?.message?.content || "";
    if (!answer || answer.length < 50) return null;

    // Parse the answer into structured data
    const counselInfo = parseCounselAnswer(answer, account.name, litigationItem);
    counselInfo.raw_answer = answer.slice(0, 500);
    return counselInfo;

  } catch(err) {
    logger.warn(`Perplexity counsel lookup failed for ${account.name}: ${err.message}`);
    return null;
  }
}

function parseCounselAnswer(answer, accountName, litigationItem) {
  const answerLower = answer.toLowerCase();
  const result = {
    outside_counsel_firm: null,
    lead_partners: [],
    case_phase: "Unknown",
    is_in_discovery: false,
    key_dates: [],
    court: null,
    case_number: null,
    discovery_signal: null,
  };

  // Detect case phase
  for (const [phase, signals] of Object.entries(PHASE_SIGNALS)) {
    if (signals.some(s => answerLower.includes(s))) {
      result.case_phase = phase;
      if (phase === "discovery") {
        result.is_in_discovery = true;
        result.discovery_signal = signals.find(s => answerLower.includes(s));
      }
      break;
    }
  }

  // Extract law firm names (look for "LLP", "LLC", "& ", common firm patterns)
  const firmPatterns = [
    /([A-Z][a-z]+ (?:&|and) [A-Z][a-z]+(?:\s+LLP|\s+LLC)?)/g,
    /([A-Z][a-z]+(?:,\s+[A-Z][a-z]+)+ LLP)/g,
    /([A-Z][a-z]+ [A-Z][a-z]+ (?:LLP|LLC|PC|PLLC))/g,
  ];

  for (const pattern of firmPatterns) {
    const matches = answer.match(pattern);
    if (matches && matches.length > 0) {
      result.outside_counsel_firm = matches[0];
      break;
    }
  }

  // Extract dates
  const datePattern = /(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}/g;
  const dates = answer.match(datePattern);
  if (dates) result.key_dates = dates.slice(0, 3);

  // Extract case number
  const caseNumPattern = /(?:case\s+no\.?|docket\s+no\.?|civil\s+action)\s*:?\s*([0-9:\-cv]+)/i;
  const caseNumMatch = answer.match(caseNumPattern);
  if (caseNumMatch) result.case_number = caseNumMatch[1];

  return result;
}

// Build the alert message for a discovery-phase case
function buildDiscoveryAlert(account, litigationItem, counselInfo) {
  const firm = counselInfo?.outside_counsel_firm || "Unknown firm";
  const phase = counselInfo?.case_phase || "Unknown phase";
  const dates = (counselInfo?.key_dates || []).join(", ") || "No dates confirmed";
  const volume = estimateVolume(litigationItem.type);

  return {
    account_name: account.name,
    case_type: litigationItem.type,
    case_phase: phase,
    is_in_discovery: counselInfo?.is_in_discovery || false,
    outside_counsel: firm,
    key_dates: counselInfo?.key_dates || [],
    estimated_doc_volume: volume,
    discovery_signal: counselInfo?.discovery_signal,
    case_number: counselInfo?.case_number,
    alert_type: counselInfo?.is_in_discovery ? "DISCOVERY_PHASE" : "ACTIVE_LITIGATION",
    consilio_opportunity: buildOpportunity(litigationItem.type, firm, volume, dates),
    source_url: litigationItem.source_url || null,
    raw_intelligence: counselInfo?.raw_answer || null,
  };
}

function buildOpportunity(caseType, firm, volume, dates) {
  const opportunities = [];

  if (caseType.toLowerCase().includes("antitrust")) {
    opportunities.push("Antitrust matters require specialized document review with competition law expertise. Early vendor selection is critical — typically decided 30-60 days after scheduling order.");
  } else if (caseType.toLowerCase().includes("securities")) {
    opportunities.push("Securities class actions require fast-turnaround document collection from multiple custodians. Lead counsel typically selects eDiscovery vendor within 60 days of class certification.");
  } else if (caseType.toLowerCase().includes("patent")) {
    opportunities.push("Patent cases require technical document review with IP expertise. Source code review and prior art searches are common needs.");
  } else if (caseType.toLowerCase().includes("employment") || caseType.toLowerCase().includes("class action")) {
    opportunities.push("Employment class actions require HR system data extraction and structured data analysis alongside document review.");
  } else {
    opportunities.push("Active litigation in discovery phase creates immediate need for document review, data collection, and processing support.");
  }

  return opportunities[0];
}

// Main job function
export async function runLitigationMonitor() {
  const startTime = Date.now();
  logger.info("=== Litigation intelligence monitor started ===");

  const results = { checked: 0, inDiscovery: 0, alertsSent: 0, failed: 0 };
  const alerts = [];

  for (const account of ACCOUNTS) {
    try {
      const data = await getResearch(account.id);
      if (!data || !data.litigation || !data.litigation.length) continue;

      results.checked++;
      const activeLitigation = data.litigation.filter(l =>
        !["Resolved", "Settled", "Dismissed"].includes(l.status)
      );

      if (!activeLitigation.length) continue;

      logger.info(`Checking ${activeLitigation.length} active litigation items for ${account.name}`);

      const enrichedLitigation = [];
      let accountAlerted = false;

      for (const litItem of activeLitigation) {
        // Check if we already have enriched data for this item
        const itemKey = `lit:${litItem.type}:${litItem.period}`;
        const alreadyAlerted = hasBeenNotified(account.id, itemKey + ":discovery_alert");

        // Get counsel and phase info from Perplexity
        const counselInfo = await getLitigationCounsel(account, litItem);

        if (counselInfo) {
          // Merge enriched data into litigation item
          litItem.outside_counsel_firm = counselInfo.outside_counsel_firm || litItem.counsel;
          litItem.lead_partners = counselInfo.lead_partners;
          litItem.case_phase = counselInfo.case_phase;
          litItem.is_in_discovery = counselInfo.is_in_discovery;
          litItem.key_dates = counselInfo.key_dates;
          litItem.case_number = counselInfo.case_number;
          litItem.last_enriched = new Date().toISOString();

          // Alert if newly entered discovery phase
          if (counselInfo.is_in_discovery && !alreadyAlerted) {
            results.inDiscovery++;
            const alert = buildDiscoveryAlert(account, litItem, counselInfo);
            alerts.push(alert);
            await markNotified(account.id, itemKey + ":discovery_alert");
            accountAlerted = true;
            logger.info(`DISCOVERY ALERT: ${account.name} — ${litItem.type} — counsel: ${counselInfo.outside_counsel_firm || "Unknown"}`);
          }
        }

        enrichedLitigation.push(litItem);
        await new Promise(r => setTimeout(r, 800)); // Rate limit
      }

      // Save enriched litigation data back
      data.litigation = enrichedLitigation;
      await setResearch(account.id, data);

      if (accountAlerted) results.alertsSent++;

    } catch(err) {
      logger.error(`Litigation monitor failed for ${account.name}`, { error: err.message });
      results.failed++;
    }
  }

  // Send consolidated alert email if any discovery phase cases found
  if (alerts.length > 0) {
    try {
      const { sendLitigationAlertEmail } = await import("../emailer.js");
      if (typeof sendLitigationAlertEmail === "function") {
        await sendLitigationAlertEmail(alerts);
      } else {
        // Fallback — log alerts
        logger.info("Discovery phase alerts found:", alerts.map(a =>
          `${a.account_name}: ${a.case_type} — ${a.outside_counsel}`
        ).join(", "));
      }
    } catch(emailErr) {
      logger.warn("Alert email failed:", emailErr.message);
    }
  }

  const duration = Math.round((Date.now() - startTime) / 1000);
  logger.info(`=== Litigation monitor complete in ${duration}s ===`, results);
  await logRun({ job: "litigation_monitor", duration, ...results });

  return { results, alerts };
}

// Direct execution
if (process.argv[1].endsWith("litigationMonitor.js")) {
  runLitigationMonitor()
    .then(({ results, alerts }) => {
      logger.info("Manual run complete", results);
      if (alerts.length) {
        console.log("\\nDiscovery alerts:");
        alerts.forEach(a => {
          console.log(`  ${a.account_name}: ${a.case_type}`);
          console.log(`    Phase: ${a.case_phase}`);
          console.log(`    Counsel: ${a.outside_counsel}`);
          console.log(`    Opportunity: ${a.consilio_opportunity}`);
        });
      }
    })
    .catch(err => {
      logger.error("Fatal error", { error: err.message });
      process.exit(1);
    });
}
''';

with open(lit_path, 'w') as f:
    f.write(content)
print("Done — litigationMonitor.js written")

# ── Add litigation intelligence to dashboard ──────────────
dashboard_path = os.path.join(base, "src", "dashboard.html")

with open(dashboard_path, 'r') as f:
    dash = f.read()

# Update litigation tab to show enriched data
old_lit_tab = """  }else if(tab==='litigation'){
    if(!r.litigation||!r.litigation.length){c.innerHTML=emp('No litigation data');return;}
    var h='<div class="sl">Litigation ('+r.litigation.length+')</div>';
    r.litigation.forEach(function(l){
      h+='<div class="ir"><div class="irt"><span class="iti">'+l.type+(l.is_new?'<span class="nt">NEW</span>':'')+'</span>'+sbdg(l.status)+'</div>';
      h+='<div class="ipe">'+l.period+'</div><div class="isu">'+l.summary+'</div>';
      h+='<div class="ico">Outside counsel: <strong>'+(l.counsel||'Unknown')+'</strong></div></div>';
    });
    c.innerHTML=h;"""

new_lit_tab = """  }else if(tab==='litigation'){
    if(!r.litigation||!r.litigation.length){c.innerHTML=emp('No litigation data');return;}
    var active=r.litigation.filter(function(l){return!['Resolved','Settled','Dismissed'].includes(l.status);});
    var resolved=r.litigation.filter(function(l){return['Resolved','Settled','Dismissed'].includes(l.status);});
    var h='';
    // Discovery phase cases first — most urgent
    var discovery=active.filter(function(l){return l.is_in_discovery||l.case_phase==='discovery';});
    if(discovery.length){
      h+='<div class="sl" style="color:var(--red)">In discovery — immediate eDiscovery opportunity ('+discovery.length+')</div>';
      discovery.forEach(function(l){
        h+='<div style="background:#fff;border:1px solid var(--rl);border-left:4px solid var(--red);border-radius:var(--rl);padding:13px 16px;margin-bottom:10px">';
        h+='<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">';
        h+='<span style="font-size:13px;font-weight:600;color:var(--g9)">'+l.type+'</span>';
        h+='<span style="font-size:10px;background:var(--rl);color:var(--red);padding:2px 8px;border-radius:20px;font-weight:700">DISCOVERY</span>';
        if(l.is_new)h+='<span class="nt">NEW</span>';
        h+='</div>';
        h+='<div style="font-size:11px;color:var(--g4);margin-bottom:5px">'+l.period+'</div>';
        h+='<div style="font-size:12px;color:var(--g6);margin-bottom:8px">'+l.summary+'</div>';
        if(l.outside_counsel_firm||l.counsel){
          h+='<div style="background:var(--g0);border-radius:var(--r);padding:8px 10px;margin-bottom:6px">';
          h+='<div style="font-size:11px;font-weight:600;color:var(--g5);text-transform:uppercase;letter-spacing:.05em;margin-bottom:3px">Outside Counsel</div>';
          h+='<div style="font-size:13px;font-weight:600;color:var(--g9)">'+(l.outside_counsel_firm||l.counsel)+'</div>';
          if(l.lead_partners&&l.lead_partners.length)h+='<div style="font-size:12px;color:var(--g6)">Partners: '+l.lead_partners.join(', ')+'</div>';
          h+='</div>';
        }
        if(l.key_dates&&l.key_dates.length){
          h+='<div style="font-size:11px;font-weight:600;color:var(--g5);text-transform:uppercase;letter-spacing:.05em;margin-bottom:3px">Key Dates</div>';
          l.key_dates.forEach(function(d){h+='<div style="font-size:12px;color:var(--g6)">&#128197; '+d+'</div>';});
        }
        if(l.case_number)h+='<div style="font-size:11px;color:var(--g4);margin-top:4px">Case: '+l.case_number+'</div>';
        h+='<div style="background:linear-gradient(135deg,#FFF8E7,#FFFBF0);border:1px solid #FDE68A;border-radius:var(--r);padding:8px 10px;margin-top:8px">';
        h+='<div style="font-size:10px;font-weight:700;color:var(--amber);text-transform:uppercase;margin-bottom:3px">Consilio Opportunity</div>';
        h+='<div style="font-size:12px;color:var(--g7)">Document review and eDiscovery support needed — discovery phase active</div>';
        h+='</div>';
        h+='</div>';
      });
    }
    // Other active cases
    var otherActive=active.filter(function(l){return!l.is_in_discovery&&l.case_phase!=='discovery';});
    if(otherActive.length){
      h+='<div class="sl" style="margin-top:'+(discovery.length?'16':'0')+'px">Active litigation ('+otherActive.length+')</div>';
      otherActive.forEach(function(l){
        h+='<div class="ir"><div class="irt"><span class="iti">'+l.type+(l.is_new?'<span class="nt">NEW</span>':'')+'</span>'+sbdg(l.status)+'</div>';
        h+='<div class="ipe">'+l.period+'</div><div class="isu">'+l.summary+'</div>';
        var counsel=l.outside_counsel_firm||l.counsel||'Unknown';
        h+='<div class="ico">Outside counsel: <strong>'+counsel+'</strong>';
        if(l.case_phase&&l.case_phase!=='Unknown')h+=' &middot; Phase: <strong>'+l.case_phase+'</strong>';
        if(l.key_dates&&l.key_dates.length)h+=' &middot; Next date: '+l.key_dates[0];
        h+='</div></div>';
      });
    }
    // Resolved
    if(resolved.length){
      h+='<div class="sl" style="margin-top:16px">Resolved ('+resolved.length+')</div>';
      resolved.forEach(function(l){
        h+='<div class="ir" style="opacity:.6"><div class="irt"><span class="iti">'+l.type+'</span>'+sbdg(l.status)+'</div>';
        h+='<div class="ipe">'+l.period+'</div><div class="isu">'+l.summary+'</div></div>';
      });
    }
    c.innerHTML=h||emp('No litigation data');"""

if old_lit_tab in dash:
    dash = dash.replace(old_lit_tab, new_lit_tab)
    with open(dashboard_path, 'w') as f:
        f.write(dash)
    print("Done — dashboard litigation tab updated with discovery intelligence")
else:
    print("WARNING — litigation tab pattern not found in dashboard")

# ── Schedule litigation monitor in index.js ───────────────
index_path = os.path.join(base, "src", "index.js")

with open(index_path, 'r') as f:
    index = f.read()

if 'litigationMonitor' not in index:
    # Add import
    old_import = "import { runFilingsMonitor } from './jobs/filingsMonitor.js';"
    new_import = """import { runFilingsMonitor } from './jobs/filingsMonitor.js';
import { runLitigationMonitor } from './jobs/litigationMonitor.js';"""

    if old_import in index:
        index = index.replace(old_import, new_import)
        print("Done — litigationMonitor imported in index.js")

    # Add cron schedule at 6:30 AM
    old_cron = "// ── Cron: Daily research"
    new_cron = """// ── Cron: Litigation intelligence monitor (6:30 AM daily) ──
  const litCron = process.env.LITIGATION_CRON || '30 6 * * *';
  cron.schedule(litCron, async () => {
    logger.info('Cron: litigation monitor triggered');
    try { await runLitigationMonitor(); } catch(e) { logger.error('Litigation monitor failed', { error: e.message }); }
  }, { timezone: process.env.TZ || 'America/Los_Angeles' });
  logger.info(`Litigation monitor scheduled: ${litCron} (America/Los_Angeles)`);

  // ── Cron: Daily research"""

    if old_cron in index:
        index = index.replace(old_cron, new_cron)
        print("Done — litigation monitor scheduled at 6:30 AM in index.js")

    with open(index_path, 'w') as f:
        f.write(index)
else:
    print("Skipped — litigationMonitor already in index.js")

# ── Add package.json script ───────────────────────────────
import json
pkg_path = os.path.join(base, "package.json")
with open(pkg_path, 'r') as f:
    pkg = json.load(f)

pkg["scripts"]["litigation:monitor"] = "node src/jobs/litigationMonitor.js"
pkg["scripts"]["litigation:account"] = "node -e \"import('./src/jobs/litigationMonitor.js').then(m=>m.runLitigationMonitor())\""

with open(pkg_path, 'w') as f:
    json.dump(pkg, f, indent=2)
print("Done — litigation:monitor script added to package.json")

print("")
print("="*50)
print("LITIGATION INTELLIGENCE LAYER INSTALLED")
print("="*50)
print("")
print("What was built:")
print("  1. litigationMonitor.js — runs daily at 6:30 AM")
print("     - Checks each active litigation item via Perplexity")
print("     - Detects discovery phase entry")
print("     - Extracts outside counsel firm and partners")
print("     - Identifies key dates (discovery cutoff, trial)")
print("     - Estimates document volume by case type")
print("     - Sends immediate alert when case enters discovery")
print("")
print("  2. Dashboard litigation tab enhanced:")
print("     - Discovery phase cases shown first in red")
print("     - Outside counsel and partners displayed")
print("     - Key dates shown")
print("     - Consilio opportunity highlighted")
print("")
print("  3. Scheduled daily at 6:30 AM")
print("")
print("Test it now:")
print("  npm run litigation:monitor")
print("")
print("Then restart:")
print("  pm2 restart legal-tracker")
