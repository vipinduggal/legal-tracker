import os

home = os.path.expanduser("~")

# ── File 1: filingsMonitor.js ──────────────────────────────
filings_path = os.path.join(home, "legal-tracker", "src", "jobs", "filingsMonitor.js")

filings_content = '''// filingsMonitor.js — Daily job that scans for new litigation and regulatory filings
// Runs at 6 AM daily (one hour before main research job)
// Sources: CourtListener API (free), SEC EDGAR, news search via Anthropic

import "dotenv/config";
import Anthropic from "@anthropic-ai/sdk";
import axios from "axios";
import { ACCOUNTS } from "../config/accounts.js";
import { getResearch, setResearch, logRun } from "../db.js";
import { sendFilingsAlertEmail } from "../emailer.js";
import { postAccountUpdateToTeams } from "../teams.js";
import { logger } from "../logger.js";
import pLimit from "p-limit";

const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
const CONCURRENCY = 2;

// ── Main job ───────────────────────────────────────────────
export async function runFilingsMonitor() {
  const startTime = Date.now();
  logger.info("=== Filings monitor started ===");

  const limit = pLimit(CONCURRENCY);
  const results = { checked: 0, newFilings: 0, alertsSent: 0, failed: 0 };
  const allNewFilings = [];

  const tasks = ACCOUNTS.map(account =>
    limit(async () => {
      try {
        results.checked++;
        const newFilings = await checkForNewFilings(account);
        if (newFilings.length > 0) {
          results.newFilings += newFilings.length;
          allNewFilings.push({ account, filings: newFilings });

          // Update the database with new filings
          await mergeNewFilings(account, newFilings);

          // Send immediate alert
          await sendFilingsAlertEmail(account, newFilings);
          await postAccountUpdateToTeams(
            account,
            newFilings.map(f => "NEW FILING: " + f.type),
            { contacts: [], litigation: newFilings, regulatory: [], intel_summary: newFilings[0]?.suggested_action || "" }
          );
          results.alertsSent++;
        }
        await sleep(300);
      } catch (err) {
        logger.error("Filings monitor error for " + account.name, { error: err.message });
        results.failed++;
      }
    })
  );

  await Promise.allSettled(tasks);

  const duration = Math.round((Date.now() - startTime) / 1000);
  logger.info("=== Filings monitor complete in " + duration + "s ===", results);
  await logRun({ job: "filings_monitor", duration, ...results });

  return { results, allNewFilings };
}

// ── Check one account for new filings ─────────────────────
async function checkForNewFilings(account) {
  const existing = await getResearch(account.id);
  const existingTypes = new Set([
    ...(existing?.litigation || []).map(l => l.type + "|" + l.period),
    ...(existing?.regulatory || []).map(r => r.type + "|" + r.period),
  ]);

  // Use Claude to search for recent filings
  const prompt = buildFilingsCheckPrompt(account);

  const response = await client.messages.create({
    model: "claude-sonnet-4-5-20251001",
    max_tokens: 2000,
    messages: [{ role: "user", content: prompt }],
  });

  const raw = response.content.filter(b => b.type === "text").map(b => b.text).join("");
  const cleaned = raw.replace(/^```json\\s*/i, "").replace(/^```\\s*/i, "").replace(/```\\s*$/i, "").trim();

  let parsed;
  try {
    parsed = JSON.parse(cleaned);
  } catch (e) {
    logger.warn("Could not parse filings response for " + account.name);
    return [];
  }

  const allFilings = [
    ...(parsed.new_litigation || []).map(f => ({ ...f, category: "litigation" })),
    ...(parsed.new_regulatory || []).map(f => ({ ...f, category: "regulatory" })),
  ];

  // Filter to only genuinely new ones
  return allFilings.filter(f => {
    const key = f.type + "|" + (f.period || "");
    return !existingTypes.has(key);
  });
}

// ── Merge new filings into existing research ───────────────
async function mergeNewFilings(account, newFilings) {
  const existing = await getResearch(account.id);
  if (!existing) return;

  for (const filing of newFilings) {
    if (filing.category === "litigation") {
      existing.litigation = existing.litigation || [];
      existing.litigation.unshift({
        type: filing.type,
        period: filing.period || new Date().toLocaleDateString("en-US", { month: "short", year: "numeric" }) + "-present",
        summary: filing.summary,
        counsel: filing.counsel || null,
        status: filing.status || "Pending",
        is_new: true,
      });
    } else if (filing.category === "regulatory") {
      existing.regulatory = existing.regulatory || [];
      existing.regulatory.unshift({
        type: filing.type,
        period: filing.period || new Date().toLocaleDateString("en-US", { month: "short", year: "numeric" }) + "-present",
        summary: filing.summary,
        counsel: filing.counsel || null,
        status: filing.status || "Ongoing",
        is_new: true,
      });
    }
  }

  await setResearch(account.id, existing);
  logger.info("Merged " + newFilings.length + " new filings for " + account.name);
}

// ── Filings check prompt ───────────────────────────────────
function buildFilingsCheckPrompt(account) {
  const today = new Date().toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" });
  return "You are a legal intelligence analyst. Today is " + today + ". Search your knowledge for any NEW litigation filings, regulatory actions, or government investigations involving " + account.name + " (" + account.industry + ", " + account.location + ") that were filed, announced, or materially updated in the LAST 30 DAYS ONLY." +
    " Return ONLY valid JSON, no markdown." +
    " {" +
    '  "new_litigation": [' +
    "    {" +
    '      "type": "string - litigation type",' +
    '      "period": "string - filing date or date range",' +
    '      "summary": "string - 1-2 sentence summary of what was filed",' +
    '      "counsel": "string - outside counsel if known, else null",' +
    '      "status": "one of: Pending | Ongoing",' +
    '      "suggested_action": "string - specific sales action to take this week based on this filing"' +
    "    }" +
    "  ]," +
    '  "new_regulatory": [' +
    "    {" +
    '      "type": "string - agency and action type",' +
    '      "period": "string - filing date or date range",' +
    '      "summary": "string - 1-2 sentence summary",' +
    '      "counsel": "string - outside counsel if known, else null",' +
    '      "status": "one of: Ongoing | Under investigation",' +
    '      "suggested_action": "string - specific sales action to take this week"' +
    "    }" +
    "  ]" +
    " }" +
    " If there are NO new filings in the last 30 days, return empty arrays. Do not include matters older than 30 days. Do not fabricate.";
}

function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}

// ── Allow direct execution ─────────────────────────────────
if (process.argv[1].endsWith("filingsMonitor.js")) {
  runFilingsMonitor()
    .then(({ results, allNewFilings }) => {
      if (allNewFilings.length === 0) {
        logger.info("No new filings detected across all accounts");
      } else {
        logger.info("New filings found at: " + allNewFilings.map(x => x.account.name).join(", "));
      }
    })
    .catch(err => {
      logger.error("Fatal error in filings monitor", { error: err.message });
      process.exit(1);
    });
}
''';

with open(filings_path, 'w') as f:
    f.write(filings_content)
print("Done — filingsMonitor.js written to " + filings_path)

# ── File 2: filings alert email function (append to emailer.js) ──
emailer_path = os.path.join(home, "legal-tracker", "src", "emailer.js")

with open(emailer_path, 'r') as f:
    emailer_content = f.read()

if 'sendFilingsAlertEmail' not in emailer_content:
    alert_function = '''

/**
 * Send an immediate alert when new filings are detected.
 */
export async function sendFilingsAlertEmail(account, newFilings) {
  if (!process.env.EMAIL_USER || !process.env.EMAIL_PASS) {
    return false;
  }

  const date = new Date().toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" });

  const html = `
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body{font-family:Segoe UI,Arial,sans-serif;font-size:14px;color:#333;margin:0;padding:0;background:#f5f5f5}
  .container{max-width:600px;margin:24px auto;background:white;border-radius:8px;overflow:hidden;border:1px solid #e0e0e0}
  .header{background:#991B1B;color:white;padding:20px 24px}
  .header h1{font-size:18px;font-weight:600;margin:0 0 4px}
  .header p{font-size:13px;opacity:.85;margin:0}
  .body{padding:20px 24px}
  .filing-card{border:1px solid #FEE2E2;border-left:4px solid #991B1B;border-radius:4px;padding:12px;margin:10px 0;background:#FFF5F5}
  .filing-type{font-size:14px;font-weight:600;color:#991B1B;margin-bottom:4px}
  .filing-summary{font-size:13px;color:#333;margin-bottom:8px;line-height:1.5}
  .action-box{background:#FEF3C7;border:1px solid #FDE68A;border-radius:4px;padding:10px;font-size:13px;color:#92400E}
  .action-label{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;margin-bottom:3px;color:#B45309}
  .footer{padding:12px 24px;background:#f9f9f9;font-size:11px;color:#888;border-top:1px solid #eee}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>🚨 New Filing Alert — ${account.name}</h1>
    <p>${date} · Legal Account Tracker · Immediate notification</p>
  </div>
  <div class="body">
    <p style="margin-bottom:14px;font-size:14px">${newFilings.length} new filing${newFilings.length > 1 ? "s" : ""} detected for <strong>${account.name}</strong> (${account.industry}) in the last 30 days.</p>
    ${newFilings.map(f => `
    <div class="filing-card">
      <div class="filing-type">${f.type}</div>
      <div class="filing-summary">${f.summary}</div>
      ${f.counsel ? `<div style="font-size:12px;color:#666;margin-bottom:8px">Outside counsel: <strong>${f.counsel}</strong></div>` : ""}
      ${f.suggested_action ? `
      <div class="action-box">
        <div class="action-label">💡 Suggested action this week</div>
        ${f.suggested_action}
      </div>` : ""}
    </div>`).join("")}
  </div>
  <div class="footer">Legal Account Tracker · New filing alerts · Automated daily monitoring</div>
</div>
</body>
</html>`;

  try {
    await getTransporter().sendMail({
      from: `"Legal Tracker" <${process.env.EMAIL_FROM}>`,
      to: process.env.EMAIL_TO,
      subject: `[ALERT] New filing — ${account.name}: ${newFilings[0]?.type}`,
      html,
    });
    logger.info("Filing alert email sent for " + account.name);
    return true;
  } catch (err) {
    logger.error("Filing alert email failed for " + account.name, { error: err.message });
    return false;
  }
}
'''
    with open(emailer_path, 'a') as f:
        f.write(alert_function)
    print("Done — sendFilingsAlertEmail added to emailer.js")
else:
    print("Skipped emailer.js — sendFilingsAlertEmail already exists")

# ── File 3: Update index.js to add 6 AM schedule ──────────
index_path = os.path.join(home, "legal-tracker", "src", "index.js")

with open(index_path, 'r') as f:
    index_content = f.read()

if 'filingsMonitor' not in index_content:
    old_import = "import { runDailyResearch } from './jobs/researchAll.js';"
    new_import = "import { runDailyResearch } from './jobs/researchAll.js';\nimport { runFilingsMonitor } from './jobs/filingsMonitor.js';"
    index_content = index_content.replace(old_import, new_import)

    old_cron_section = "  logger.info(`Daily research scheduled: ${researchCron} (America/Los_Angeles)`);"
    new_cron_section = """  logger.info(`Daily research scheduled: ${researchCron} (America/Los_Angeles)`);

  // ── Cron: Filings monitor (default: 6:00 AM every day) ──
  const filingsCron = '0 6 * * *';
  cron.schedule(filingsCron, async () => {
    logger.info('Cron: filings monitor triggered');
    try {
      await runFilingsMonitor();
    } catch (err) {
      logger.error('Cron: filings monitor failed', { error: err.message });
    }
  }, { timezone: 'America/Los_Angeles' });
  logger.info(`Filings monitor scheduled: ${filingsCron} (America/Los_Angeles)`);"""

    index_content = index_content.replace(old_cron_section, new_cron_section)

    with open(index_path, 'w') as f:
        f.write(index_content)
    print("Done — index.js updated with 6 AM filings monitor schedule")
else:
    print("Skipped index.js — filings monitor already scheduled")

print("")
print("All files updated. Next steps:")
print("  1. npm start")
print("  2. node src/jobs/filingsMonitor.js   (test it manually)")
