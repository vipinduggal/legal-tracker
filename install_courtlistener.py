import os

home = os.path.expanduser("~")
base = os.path.join(home, "legal-tracker")

path = os.path.join(base, "src", "jobs", "courtListenerMonitor.js")

content = '''// courtListenerMonitor.js
// Pulls real docket data from CourtListener for active litigation
// Extracts: outside counsel, named partners, scheduling orders,
// discovery cutoff dates, trial dates, and case phase
// Runs daily at 6:45 AM after the litigation monitor

import "dotenv/config";
import axios from "axios";
import { ACCOUNTS } from "../../config/accounts.js";
import { getResearch, setResearch, logRun, hasBeenNotified, markNotified } from "../db.js";
import { logger } from "../logger.js";

const CL_BASE = "https://www.courtlistener.com/api/rest/v4";
const CL_TOKEN = process.env.COURTLISTENER_TOKEN;

function clHeaders() {
  return {
    "Authorization": `Token ${CL_TOKEN}`,
    "Content-Type": "application/json",
  };
}

// Search for dockets by company name
async function searchDockets(companyName, dateAfter) {
  try {
    const since = dateAfter || new Date(Date.now() - 2 * 365 * 24 * 60 * 60 * 1000)
      .toISOString().split("T")[0]; // 2 years back

    const response = await axios.get(`${CL_BASE}/dockets/`, {
      headers: clHeaders(),
      params: {
        q: `"${companyName}"`,
        order_by: "-date_filed",
        page_size: 10,
        fields: "id,case_name,court_id,date_filed,date_terminated,docket_number,nature_of_suit,cause,assigned_to_str,parties_roles",
      },
      timeout: 15000,
    });

    return response.data?.results || [];
  } catch(err) {
    if (err.response?.status === 401) {
      logger.warn("CourtListener auth failed — check COURTLISTENER_TOKEN in .env");
    } else {
      logger.warn(`CourtListener docket search failed for ${companyName}: ${err.message}`);
    }
    return [];
  }
}

// Get attorneys for a docket
async function getDocketAttorneys(docketId) {
  try {
    const response = await axios.get(`${CL_BASE}/dockets/${docketId}/`, {
      headers: clHeaders(),
      params: { fields: "parties" },
      timeout: 10000,
    });

    const parties = response.data?.parties || [];
    const attorneys = [];

    for (const party of parties) {
      if (!party.attorneys) continue;
      for (const atty of party.attorneys) {
        attorneys.push({
          name: atty.name,
          firm: atty.contact_raw?.split("\\n")?.[0] || null,
          contact: atty.contact_raw,
          role: atty.roles?.map(r => r.role_raw).join(", ") || null,
          party_name: party.name,
          party_type: party.party_types?.map(pt => pt.name).join(", ") || null,
        });
      }
    }

    return attorneys;
  } catch(err) {
    logger.warn(`Attorney lookup failed for docket ${docketId}: ${err.message}`);
    return [];
  }
}

// Get recent docket entries to find scheduling orders and phase signals
async function getRecentEntries(docketId, daysBack = 180) {
  try {
    const since = new Date(Date.now() - daysBack * 24 * 60 * 60 * 1000)
      .toISOString().split("T")[0];

    const response = await axios.get(`${CL_BASE}/docket-entries/`, {
      headers: clHeaders(),
      params: {
        docket: docketId,
        date_filed__gte: since,
        order_by: "-date_filed",
        page_size: 20,
        fields: "id,date_filed,entry_number,description,pacer_doc_id",
      },
      timeout: 15000,
    });

    return response.data?.results || [];
  } catch(err) {
    logger.warn(`Docket entries lookup failed for ${docketId}: ${err.message}`);
    return [];
  }
}

// Parse docket entries to find scheduling info and phase
function analyzeDocketEntries(entries) {
  const result = {
    case_phase: null,
    is_in_discovery: false,
    discovery_cutoff: null,
    trial_date: null,
    expert_deadline: null,
    summary_judgment_deadline: null,
    last_activity: null,
    phase_signal: null,
    key_entries: [],
  };

  if (!entries.length) return result;

  result.last_activity = entries[0].date_filed;

  const discoverySignals = [
    "scheduling order", "rule 26", "discovery plan", "fact discovery",
    "discovery cutoff", "discovery deadline", "esi protocol",
    "electronically stored", "deposition", "interrogator",
    "motion to compel", "protective order", "litigation hold",
    "document production", "discovery period",
  ];

  const postDiscoverySignals = [
    "motion for summary judgment", "summary judgment",
    "expert report", "daubert", "motion in limine",
    "pretrial order", "pretrial conference",
  ];

  const trialSignals = [
    "trial date", "jury selection", "trial brief",
    "verdict", "judgment",
  ];

  for (const entry of entries) {
    const desc = (entry.description || "").toLowerCase();
    const date = entry.date_filed;

    // Check for scheduling order / discovery phase
    if (discoverySignals.some(s => desc.includes(s))) {
      result.is_in_discovery = true;
      result.case_phase = "discovery";
      result.phase_signal = entry.description;
      result.key_entries.push({
        date,
        description: entry.description,
        significance: "Discovery phase signal",
      });

      // Try to extract dates from description
      const dateMatches = entry.description.match(
        /(January|February|March|April|May|June|July|August|September|October|November|December)\\s+\\d{1,2},?\\s+\\d{4}/gi
      );
      if (dateMatches) {
        if (desc.includes("discovery cutoff") || desc.includes("fact discovery")) {
          result.discovery_cutoff = dateMatches[0];
        } else if (desc.includes("trial")) {
          result.trial_date = dateMatches[0];
        }
      }
    }

    // Check for post-discovery signals
    if (!result.is_in_discovery && postDiscoverySignals.some(s => desc.includes(s))) {
      result.case_phase = "post-discovery";
      result.key_entries.push({
        date,
        description: entry.description,
        significance: "Post-discovery signal",
      });
    }

    // Check for trial signals
    if (trialSignals.some(s => desc.includes(s))) {
      result.case_phase = "trial";
      result.key_entries.push({
        date,
        description: entry.description,
        significance: "Trial phase signal",
      });
    }
  }

  // Default to pending if no phase detected
  if (!result.case_phase) {
    result.case_phase = "pending";
  }

  return result;
}

// Extract defense counsel from attorneys list
function extractDefenseCounsel(attorneys, companyName) {
  if (!attorneys.length) return null;

  const companyWords = companyName.toLowerCase().split(" ").filter(w => w.length > 3);

  // Find attorneys representing the defendant (our account)
  const defenseAttorneys = attorneys.filter(a => {
    const partyName = (a.party_name || "").toLowerCase();
    const partyType = (a.party_type || "").toLowerCase();
    return companyWords.some(w => partyName.includes(w)) ||
           partyType.includes("defendant") ||
           partyType.includes("respondent");
  });

  const relevantAttorneys = defenseAttorneys.length ? defenseAttorneys : attorneys.slice(0, 5);

  if (!relevantAttorneys.length) return null;

  // Extract firm names and attorney names
  const firms = new Set();
  const partners = [];

  for (const atty of relevantAttorneys) {
    if (atty.name && atty.name.length > 2) {
      partners.push(atty.name);
    }
    if (atty.firm && atty.firm.length > 3) {
      // Clean firm name
      const firm = atty.firm
        .replace(/\\d+.*$/, "") // Remove addresses
        .replace(/,.*$/, "")    // Remove city/state
        .trim();
      if (firm.length > 3 && firm.length < 60) {
        firms.add(firm);
      }
    }
  }

  return {
    firms: [...firms].slice(0, 2),
    partners: partners.slice(0, 4),
    primary_firm: [...firms][0] || null,
  };
}

// Main job
export async function runCourtListenerMonitor(accountId) {
  if (!CL_TOKEN) {
    logger.warn("COURTLISTENER_TOKEN not set — skipping CourtListener monitor");
    return { checked: 0, enriched: 0, failed: 0 };
  }

  const startTime = Date.now();
  const targetAccounts = accountId
    ? ACCOUNTS.filter(a => a.id === accountId)
    : ACCOUNTS;

  logger.info(`=== CourtListener monitor started — ${targetAccounts.length} accounts ===`);
  const results = { checked: 0, enriched: 0, alerts: 0, failed: 0 };

  for (const account of targetAccounts) {
    try {
      const data = await getResearch(account.id);
      if (!data) continue;

      const activeLit = (data.litigation || []).filter(l =>
        !["Resolved", "Settled", "Dismissed"].includes(l.status)
      );
      if (!activeLit.length) continue;

      results.checked++;
      logger.info(`Searching CourtListener for ${account.name} (${activeLit.length} active cases)`);

      // Search for dockets
      const dockets = await searchDockets(account.name);
      if (!dockets.length) {
        logger.info(`  No CourtListener dockets found for ${account.name}`);
        await new Promise(r => setTimeout(r, 500));
        continue;
      }

      logger.info(`  Found ${dockets.length} dockets for ${account.name}`);

      let enriched = false;

      for (const docket of dockets.slice(0, 5)) {
        // Skip terminated cases
        if (docket.date_terminated) continue;

        const caseName = docket.case_name || "Unknown";
        const docketNum = docket.docket_number || "Unknown";
        const court = docket.court_id || "Unknown";

        logger.info(`  Checking: ${caseName} (${docketNum})`);

        // Get attorneys
        const attorneys = await getDocketAttorneys(docket.id);
        const counsel = extractDefenseCounsel(attorneys, account.name);

        // Get recent entries
        const entries = await getRecentEntries(docket.id);
        const phaseInfo = analyzeDocketEntries(entries);

        // Find matching litigation item or create new one
        let litItem = activeLit.find(l => {
          const nameWords = caseName.toLowerCase().split(" ").filter(w => w.length > 4);
          return nameWords.some(w => (l.type || "").toLowerCase().includes(w) ||
                                     (l.summary || "").toLowerCase().includes(w));
        });

        if (!litItem) {
          // Create new item from CourtListener data
          litItem = {
            type: caseName,
            period: docket.date_filed ? docket.date_filed.slice(0, 7) + " to present" : "Active",
            summary: `Federal case: ${caseName}. Court: ${court.toUpperCase()}. Docket: ${docketNum}.`,
            status: "Pending",
            is_new: true,
            courtlistener_verified: true,
          };
          data.litigation = data.litigation || [];
          data.litigation.push(litItem);
        }

        // Enrich with CourtListener data
        litItem.case_name = caseName;
        litItem.case_number = docketNum;
        litItem.court = court.toUpperCase();
        litItem.case_phase = phaseInfo.case_phase;
        litItem.is_in_discovery = phaseInfo.is_in_discovery;
        litItem.courtlistener_verified = true;
        litItem.courtlistener_id = docket.id;
        litItem.last_docket_activity = phaseInfo.last_activity;
        litItem.key_entries = phaseInfo.key_entries.slice(0, 3);

        if (phaseInfo.discovery_cutoff) litItem.discovery_cutoff = phaseInfo.discovery_cutoff;
        if (phaseInfo.trial_date) litItem.trial_date = phaseInfo.trial_date;

        if (counsel) {
          litItem.outside_counsel_firm = counsel.primary_firm || litItem.outside_counsel_firm;
          litItem.all_counsel_firms = counsel.firms;
          litItem.lead_partners = counsel.partners;
          litItem.counsel_verified = true;
          if (counsel.primary_firm) {
            logger.info(`  Defense counsel: ${counsel.primary_firm} — Partners: ${counsel.partners.slice(0,2).join(", ")}`);
          }
        }

        if (phaseInfo.key_dates) {
          litItem.key_dates = [
            phaseInfo.discovery_cutoff,
            phaseInfo.trial_date,
          ].filter(Boolean);
        }

        enriched = true;

        // Alert if newly in discovery
        const alertKey = `cl:${docket.id}:discovery`;
        if (phaseInfo.is_in_discovery && !hasBeenNotified(account.id, alertKey)) {
          await markNotified(account.id, alertKey);
          results.alerts++;
          logger.info(`  DISCOVERY ALERT: ${account.name} — ${caseName} — ${counsel?.primary_firm || "Unknown counsel"}`);
        }

        await new Promise(r => setTimeout(r, 800));
      }

      if (enriched) {
        await setResearch(account.id, data);
        results.enriched++;
        logger.info(`  ${account.name} litigation enriched with CourtListener data`);
      }

      await new Promise(r => setTimeout(r, 500));

    } catch(err) {
      logger.error(`CourtListener monitor failed for ${account.name}`, { error: err.message });
      results.failed++;
    }
  }

  const duration = Math.round((Date.now() - startTime) / 1000);
  logger.info(`=== CourtListener monitor complete in ${duration}s ===`, results);
  await logRun({ job: "courtlistener_monitor", duration, ...results });
  return results;
}

// Direct execution
if (process.argv[1] && process.argv[1].endsWith("courtListenerMonitor.js")) {
  const accountId = process.argv[2] || null;
  runCourtListenerMonitor(accountId)
    .then(results => {
      console.log("\\nCourtListener monitor complete:", results);
      process.exit(0);
    })
    .catch(err => {
      console.error("Fatal:", err.message);
      process.exit(1);
    });
}
''';

with open(path, 'w') as f:
    f.write(content)
print("Done — courtListenerMonitor.js written")

# Add to package.json
import json
pkg_path = os.path.join(base, "package.json")
with open(pkg_path, 'r') as f:
    pkg = json.load(f)

pkg["scripts"]["court:monitor"] = "node src/jobs/courtListenerMonitor.js"
pkg["scripts"]["court:account"] = "node src/jobs/courtListenerMonitor.js"

with open(pkg_path, 'w') as f:
    json.dump(pkg, f, indent=2)
print("Done — court:monitor script added")

# Schedule in index.js at 6:45 AM
index_path = os.path.join(base, "src", "index.js")
with open(index_path, 'r') as f:
    index = f.read()

if 'courtListenerMonitor' not in index:
    old_import = "import { runLitigationMonitor } from './jobs/litigationMonitor.js';"
    new_import = """import { runLitigationMonitor } from './jobs/litigationMonitor.js';
import { runCourtListenerMonitor } from './jobs/courtListenerMonitor.js';"""

    if old_import in index:
        index = index.replace(old_import, new_import)

    old_cron = "// ── Cron: Litigation intelligence monitor"
    new_cron = """// ── Cron: CourtListener docket monitor (6:45 AM daily) ──
  const clCron = process.env.COURTLISTENER_CRON || '45 6 * * *';
  cron.schedule(clCron, async () => {
    logger.info('Cron: CourtListener monitor triggered');
    try { await runCourtListenerMonitor(); } catch(e) { logger.error('CourtListener monitor failed', { error: e.message }); }
  }, { timezone: 'America/Los_Angeles' });
  logger.info(`CourtListener monitor scheduled: ${clCron} (America/Los_Angeles)`);

  // ── Cron: Litigation intelligence monitor"""

    if old_cron in index:
        index = index.replace(old_cron, new_cron)
        print("Done — CourtListener monitor scheduled at 6:45 AM")

    with open(index_path, 'w') as f:
        f.write(index)

# Update dashboard to show CourtListener verified badge and key entries
dashboard_path = os.path.join(base, "src", "dashboard.html")
with open(dashboard_path, 'r') as f:
    dash = f.read()

old_sec_badge = """        if(l.sec_verified)h+='<span style="font-size:10px;background:#DCFCE7;color:#166534;padding:2px 8px;border-radius:20px;font-weight:600">SEC VERIFIED</span>';"""

new_sec_badge = """        if(l.sec_verified)h+='<span style="font-size:10px;background:#DCFCE7;color:#166534;padding:2px 8px;border-radius:20px;font-weight:600">SEC VERIFIED</span>';
        if(l.courtlistener_verified)h+='<span style="font-size:10px;background:#EDE9FE;color:#5B21B6;padding:2px 8px;border-radius:20px;font-weight:600">COURT RECORD</span>';"""

if old_sec_badge in dash:
    dash = dash.replace(old_sec_badge, new_sec_badge)
    print("Done — COURT RECORD badge added to dashboard")

# Add key docket entries display
old_case_num = """        if(l.case_number||l.court)h+='<div style="font-size:11px;color:var(--g4);margin-bottom:4px">'+(l.court||'')+(l.case_number?' &middot; Case No. '+l.case_number:'')+(l.amount_at_stake?' &middot; Exposure: '+l.amount_at_stake:'')+'</div>';"""

new_case_num = """        if(l.case_number||l.court)h+='<div style="font-size:11px;color:var(--g4);margin-bottom:4px">'+(l.court||'')+(l.case_number?' &middot; Case No. '+l.case_number:'')+(l.amount_at_stake?' &middot; Exposure: '+l.amount_at_stake:'')+'</div>';
        if(l.discovery_cutoff||l.trial_date){
          h+='<div style="font-size:11px;background:#F0FDF4;border:1px solid #BBF7D0;border-radius:6px;padding:5px 8px;margin-bottom:6px;display:flex;gap:12px">';
          if(l.discovery_cutoff)h+='<span>&#128197; Discovery cutoff: <strong>'+l.discovery_cutoff+'</strong></span>';
          if(l.trial_date)h+='<span>&#9878;&#65039; Trial: <strong>'+l.trial_date+'</strong></span>';
          h+='</div>';
        }
        if(l.last_docket_activity)h+='<div style="font-size:11px;color:var(--g4);margin-bottom:4px">Last docket activity: '+l.last_docket_activity+'</div>';
        if(l.key_entries&&l.key_entries.length){
          h+='<div style="font-size:11px;font-weight:600;color:var(--g5);text-transform:uppercase;letter-spacing:.05em;margin-bottom:3px">Recent docket entries</div>';
          l.key_entries.slice(0,2).forEach(function(e){
            h+='<div style="font-size:11px;color:var(--g6);margin-bottom:2px">'+e.date+' — '+e.description.slice(0,100)+'</div>';
          });
        }"""

if old_case_num in dash:
    dash = dash.replace(old_case_num, new_case_num)
    print("Done — discovery cutoff, trial date, and docket entries added to dashboard")

with open(dashboard_path, 'w') as f:
    f.write(dash)

print("")
print("="*60)
print("COURTLISTENER INTEGRATION INSTALLED")
print("="*60)
print("")
print("What was built:")
print("  - Searches CourtListener for active federal cases by company name")
print("  - Extracts defense counsel firm and named partners from court records")
print("  - Finds scheduling orders — discovery cutoff and trial dates")
print("  - Detects discovery phase from docket entries")
print("  - Sends alert when case enters discovery with verified counsel")
print("  - Dashboard shows COURT RECORD badge, discovery cutoff, trial date")
print("  - Runs daily at 6:45 AM")
print("")
print("Test on Microsoft first:")
print("  npm run court:account microsoft")
print("")
print("Then all accounts:")
print("  npm run court:monitor")
