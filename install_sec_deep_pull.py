import os

home = os.path.expanduser("~")
base = os.path.join(home, "legal-tracker")

# Write src/jobs/secFilingsPuller.js
sec_path = os.path.join(base, "src", "jobs", "secFilingsPuller.js")

content = '''// secFilingsPuller.js
// Pulls verified litigation data from SEC 10-K and 10-Q filings
// Uses SEC EDGAR full-text search API (free, no auth required)
// Extracts Legal Proceedings section for verified case names,
// case numbers, courts, and current status

import "dotenv/config";
import axios from "axios";
import { ACCOUNTS } from "../../config/accounts.js";
import { getResearch, setResearch, logRun } from "../db.js";
import { logger } from "../logger.js";

const EDGAR_BASE = "https://data.sec.gov";
const EDGAR_SEARCH = "https://efts.sec.gov/LATEST/search-index";
const HEADERS = {
  "User-Agent": "Consilio Legal Tracker vipin.duggal@consilio.com",
  "Accept-Encoding": "gzip, deflate",
};

// Map account names to SEC CIK numbers for reliable lookup
// CIK = Central Index Key — unique identifier for each filer
const KNOWN_CIKS = {
  "microsoft": "0000789019",
  "amd": "0000002488",
  "intel": "0000050863",
  "apple": "0000320193",
  "alphabet": "0001652044",
  "google": "0001652044",
  "meta": "0001326801",
  "amazon": "0001018724",
  "netflix": "0001065280",
  "nvidia": "0001045810",
  "salesforce": "0001108524",
  "oracle": "0001341439",
  "snap": "0001564408",
  "twitter": "0001418091",
  "uber": "0001543151",
  "lyft": "0001759509",
  "airbnb": "0001559720",
  "instacart": "0001704720",
  "stripe": null, // private
  "databricks": null, // private
  "palo alto networks": "0001327567",
  "paloaltonetworks": "0001327567",
  "workday": "0001327811",
  "snowflake": "0001640147",
  "godaddy": "0001609711",
  "reddit": "0001713445",
  "roblox": "0001315098",
  "electronic arts": "0000712515",
  "ea": "0000712515",
  "take-two": "0000906709",
  "take two": "0000906709",
  "intuit": "0000896878",
  "freeport-mcmoran": "0000831259",
  "freeport mcmoran": "0000831259",
  "starbucks": "0000829224",
  "costco": "0000909832",
  "southern california edison": "0000827054",
  "pge": "0001004440",
  "pg&e": "0001004440",
  "las vegas sands": "0001300514",
  "yelp": "0001345016",
  "unisys": "0000078814",
  "wipro": "0000907526",
  "sony": "0000313838",
  "milliman": null, // private
  "bechtel": null, // private
  "cargill": null, // private
};

// Search EDGAR for a company's CIK by name
async function findCIK(accountName) {
  // Check known CIKs first
  const nameKey = accountName.toLowerCase().replace(/[^a-z0-9\s]/g, "").trim();
  for (const [key, cik] of Object.entries(KNOWN_CIKS)) {
    if (nameKey.includes(key) || key.includes(nameKey.split(" ")[0])) {
      if (cik) return cik;
      return null; // Known private company
    }
  }

  try {
    const response = await axios.get(
      `https://efts.sec.gov/LATEST/search-index?q="${encodeURIComponent(accountName)}"&dateRange=custom&startdt=2024-01-01&forms=10-K`,
      { headers: HEADERS, timeout: 10000 }
    );
    const hits = response.data?.hits?.hits || [];
    if (hits.length > 0) {
      return hits[0]._source?.entity_id || null;
    }
    return null;
  } catch(err) {
    return null;
  }
}

// Get most recent 10-K and 10-Q filings for a company
async function getRecentFilings(cik) {
  try {
    const paddedCik = cik.replace(/^0+/, "").padStart(10, "0");
    const response = await axios.get(
      `${EDGAR_BASE}/submissions/CIK${paddedCik}.json`,
      { headers: HEADERS, timeout: 10000 }
    );

    const filings = response.data?.filings?.recent;
    if (!filings) return [];

    const forms = filings.form || [];
    const dates = filings.filingDate || [];
    const accNumbers = filings.accessionNumber || [];
    const primaryDocs = filings.primaryDocument || [];

    const relevant = [];
    for (let i = 0; i < forms.length; i++) {
      if (["10-K", "10-Q", "10-K/A", "10-Q/A"].includes(forms[i])) {
        relevant.push({
          form: forms[i],
          date: dates[i],
          accessionNumber: accNumbers[i],
          primaryDocument: primaryDocs[i],
          cik: paddedCik,
        });
        if (relevant.length >= 3) break; // Get last 3 filings
      }
    }
    return relevant;
  } catch(err) {
    logger.warn(`Failed to get filings for CIK ${cik}: ${err.message}`);
    return [];
  }
}

// Download and extract Legal Proceedings section from a filing
async function extractLegalProceedings(filing) {
  try {
    const accNo = filing.accessionNumber.replace(/-/g, "");
    const docUrl = `${EDGAR_BASE}/Archives/edgar/data/${parseInt(filing.cik)}/${accNo}/${filing.primaryDocument}`;

    const response = await axios.get(docUrl, {
      headers: HEADERS,
      timeout: 20000,
      maxContentLength: 5 * 1024 * 1024, // 5MB limit
    });

    const html = response.data || "";

    // Extract Legal Proceedings section
    // SEC filings use standardized section headers
    const legalSection = extractSection(html, [
      "LEGAL PROCEEDINGS",
      "Legal Proceedings",
      "ITEM 3",
      "Item 3.",
    ]);

    if (!legalSection) return null;

    return {
      form: filing.form,
      date: filing.date,
      content: legalSection.slice(0, 8000), // Limit size
      url: docUrl,
    };
  } catch(err) {
    logger.warn(`Failed to download filing: ${err.message}`);
    return null;
  }
}

// Extract a section from SEC filing HTML
function extractSection(html, sectionHeaders) {
  // Remove HTML tags for text extraction
  const text = html
    .replace(/<style[^>]*>[\s\S]*?<\/style>/gi, "")
    .replace(/<script[^>]*>[\s\S]*?<\/script>/gi, "")
    .replace(/<[^>]+>/g, " ")
    .replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/\s+/g, " ")
    .trim();

  for (const header of sectionHeaders) {
    const idx = text.indexOf(header);
    if (idx > -1) {
      // Find the end of the section (next major section header)
      const nextSection = text.indexOf("ITEM 4", idx + header.length);
      const endIdx = nextSection > idx ? nextSection : idx + 6000;
      return text.slice(idx, endIdx).trim();
    }
  }
  return null;
}

// Use Claude to parse Legal Proceedings into structured litigation items
async function parseLegalProceedings(account, filingContent) {
  try {
    const Anthropic = (await import("@anthropic-ai/sdk")).default;
    const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

    const prompt = `Extract all litigation and legal proceedings from this SEC filing excerpt for ${account.name}.

SEC FILING EXCERPT (${filingContent.form} filed ${filingContent.date}):
${filingContent.content.slice(0, 4000)}

For each legal matter mentioned, extract:
- Exact case name (as written in the filing)
- Case number if mentioned
- Court name if mentioned
- Type of matter (antitrust, securities, patent, employment, regulatory, etc.)
- Current status (pending, discovery, trial, settled, etc.)
- Plaintiff name
- Dollar amount at stake if mentioned
- Brief description

Return JSON array only:
[{
  "case_name": "string — exact case name from filing",
  "case_number": "string or null",
  "court": "string or null",
  "type": "string — litigation type",
  "status": "one of: Pending | Discovery | Trial | Settled | Resolved | Ongoing",
  "plaintiff": "string or null",
  "amount_at_stake": "string or null — dollar amount if mentioned",
  "summary": "string — 1-2 sentence description",
  "period": "string — filing period e.g. Q1 2025",
  "source": "SEC ${filingContent.form} ${filingContent.date}",
  "verified": true
}]

If no litigation is mentioned, return [].`;

    const response = await client.messages.create({
      model: "claude-sonnet-4-5",
      max_tokens: 2000,
      messages: [{ role: "user", content: prompt }],
    });

    const raw = response.content
      .filter(b => b.type === "text").map(b => b.text).join("")
      .replace(/^```json\s*/i, "").replace(/^```\s*/i, "").replace(/```\s*$/i, "").trim();

    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];

  } catch(err) {
    logger.warn(`Claude parsing failed for ${account.name}: ${err.message}`);
    return [];
  }
}

// Merge SEC-verified litigation with existing research data
function mergeLitigation(existing, secVerified) {
  if (!secVerified.length) return existing;

  const merged = [...(existing || [])];

  for (const secItem of secVerified) {
    // Check if this case already exists in research data
    const exists = merged.find(e =>
      (e.case_name && secItem.case_name && e.case_name.toLowerCase().includes(secItem.case_name.toLowerCase().split(" ")[0])) ||
      (e.case_number && secItem.case_number && e.case_number === secItem.case_number)
    );

    if (exists) {
      // Update existing item with verified SEC data
      exists.case_name = secItem.case_name;
      if (secItem.case_number) exists.case_number = secItem.case_number;
      if (secItem.court) exists.court = secItem.court;
      if (secItem.amount_at_stake) exists.amount_at_stake = secItem.amount_at_stake;
      exists.sec_verified = true;
      exists.sec_source = secItem.source;
      exists.verified = true;
      logger.info(`  Updated existing: ${secItem.case_name}`);
    } else {
      // Add new SEC-verified litigation item
      merged.push({
        ...secItem,
        is_new: true,
        sec_verified: true,
        counsel: null,
        outside_counsel_firm: null,
      });
      logger.info(`  Added new: ${secItem.case_name}`);
    }
  }

  return merged;
}

// Main job
export async function runSECFilingsPuller(accountId) {
  const startTime = Date.now();
  const targetAccounts = accountId
    ? ACCOUNTS.filter(a => a.id === accountId)
    : ACCOUNTS;

  logger.info(`=== SEC filings puller started — ${targetAccounts.length} accounts ===`);

  const results = { checked: 0, found: 0, updated: 0, failed: 0, private: 0 };

  for (const account of targetAccounts) {
    try {
      logger.info(`Checking SEC filings for ${account.name}...`);

      // Find CIK
      const cik = await findCIK(account.name);
      if (!cik) {
        logger.info(`  ${account.name} — private company or not found on EDGAR`);
        results.private++;
        await new Promise(r => setTimeout(r, 300));
        continue;
      }

      results.checked++;
      logger.info(`  CIK: ${cik}`);

      // Get recent filings
      const filings = await getRecentFilings(cik);
      if (!filings.length) {
        logger.info(`  No recent 10-K/10-Q found for ${account.name}`);
        continue;
      }

      logger.info(`  Found ${filings.length} recent filing(s): ${filings.map(f => f.form + " " + f.date).join(", ")}`);

      // Process most recent 10-K
      const tenK = filings.find(f => f.form === "10-K" || f.form === "10-K/A");
      const tenQ = filings.find(f => f.form === "10-Q" || f.form === "10-Q/A");
      const primaryFiling = tenQ || tenK; // Use most recent quarterly first

      if (!primaryFiling) continue;

      const filingContent = await extractLegalProceedings(primaryFiling);
      if (!filingContent) {
        logger.info(`  Could not extract legal proceedings from ${primaryFiling.form}`);
        continue;
      }

      logger.info(`  Extracted ${filingContent.content.length} chars from legal proceedings section`);
      results.found++;

      // Parse with Claude
      const secLitigation = await parseLegalProceedings(account, filingContent);
      logger.info(`  Claude found ${secLitigation.length} litigation items in SEC filing`);

      if (secLitigation.length > 0) {
        // Merge with existing research
        const data = await getResearch(account.id);
        if (data) {
          const before = (data.litigation || []).length;
          data.litigation = mergeLitigation(data.litigation, secLitigation);
          data.sec_filing_last_checked = new Date().toISOString();
          data.sec_filing_source = `${primaryFiling.form} filed ${primaryFiling.date}`;
          await setResearch(account.id, data);
          const after = data.litigation.length;
          logger.info(`  ${account.name}: litigation updated ${before} → ${after} items (${after - before} new from SEC)`);
          results.updated++;
        }
      }

      await new Promise(r => setTimeout(r, 1000)); // Rate limit EDGAR

    } catch(err) {
      logger.error(`SEC puller failed for ${account.name}`, { error: err.message });
      results.failed++;
    }
  }

  const duration = Math.round((Date.now() - startTime) / 1000);
  logger.info(`=== SEC filings puller complete in ${duration}s ===`, results);
  await logRun({ job: "sec_filings_puller", duration, ...results });
  return results;
}

// Direct execution
if (process.argv[1] && process.argv[1].endsWith("secFilingsPuller.js")) {
  const accountId = process.argv[2] || null;
  runSECFilingsPuller(accountId)
    .then(results => {
      console.log("\\nSEC filings pull complete:", results);
      process.exit(0);
    })
    .catch(err => {
      logger.error("Fatal error", { error: err.message });
      process.exit(1);
    });
}
''';

with open(sec_path, 'w') as f:
    f.write(content)
print("Done — secFilingsPuller.js written")

# ── Add to package.json ────────────────────────────────────
import json
pkg_path = os.path.join(base, "package.json")
with open(pkg_path, 'r') as f:
    pkg = json.load(f)

pkg["scripts"]["sec:pull"] = "node src/jobs/secFilingsPuller.js"
pkg["scripts"]["sec:account"] = "node src/jobs/secFilingsPuller.js"

with open(pkg_path, 'w') as f:
    json.dump(pkg, f, indent=2)
print("Done — sec:pull and sec:account scripts added")

# ── Schedule in index.js ───────────────────────────────────
index_path = os.path.join(base, "src", "index.js")
with open(index_path, 'r') as f:
    index = f.read()

if 'secFilingsPuller' not in index:
    old_import = "import { runLitigationMonitor } from './jobs/litigationMonitor.js';"
    new_import = """import { runLitigationMonitor } from './jobs/litigationMonitor.js';
import { runSECFilingsPuller } from './jobs/secFilingsPuller.js';"""

    if old_import in index:
        index = index.replace(old_import, new_import)

    # Schedule weekly on Sunday at 5 AM — SEC filings update quarterly
    old_cron = "// ── Cron: Litigation intelligence monitor"
    new_cron = """// ── Cron: SEC filings deep pull (Sunday 5:00 AM weekly) ──
  const secCron = process.env.SEC_CRON || '0 5 * * 0';
  cron.schedule(secCron, async () => {
    logger.info('Cron: SEC filings puller triggered');
    try { await runSECFilingsPuller(); } catch(e) { logger.error('SEC puller failed', { error: e.message }); }
  }, { timezone: 'America/Los_Angeles' });
  logger.info(`SEC filings puller scheduled: ${secCron} (Sundays 5 AM)`);

  // ── Cron: Litigation intelligence monitor"""

    if old_cron in index:
        index = index.replace(old_cron, new_cron)
        print("Done — SEC puller scheduled Sundays 5 AM")

    with open(index_path, 'w') as f:
        f.write(index)

# ── Update dashboard to show SEC verified badge ────────────
dashboard_path = os.path.join(base, "src", "dashboard.html")
with open(dashboard_path, 'r') as f:
    dash = f.read()

old_lit_header = """        h+='<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">';
        h+='<span style="font-size:13px;font-weight:600;color:var(--g9)">'+l.type+'</span>';
        h+='<span style="font-size:10px;background:var(--rl);color:var(--red);padding:2px 8px;border-radius:20px;font-weight:700">DISCOVERY</span>';
        if(l.is_new)h+='<span class="nt">NEW</span>';
        h+='</div>';"""

new_lit_header = """        h+='<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;flex-wrap:wrap">';
        h+='<span style="font-size:13px;font-weight:600;color:var(--g9)">'+(l.case_name||l.type)+'</span>';
        h+='<span style="font-size:10px;background:var(--rl);color:var(--red);padding:2px 8px;border-radius:20px;font-weight:700">DISCOVERY</span>';
        if(l.sec_verified)h+='<span style="font-size:10px;background:#DCFCE7;color:#166534;padding:2px 8px;border-radius:20px;font-weight:600">SEC VERIFIED</span>';
        if(l.is_new)h+='<span class="nt">NEW</span>';
        h+='</div>';
        if(l.case_number||l.court)h+='<div style="font-size:11px;color:var(--g4);margin-bottom:4px">'+(l.court||'')+(l.case_number?' &middot; Case No. '+l.case_number:'')+(l.amount_at_stake?' &middot; Exposure: '+l.amount_at_stake:'')+'</div>';"""

if old_lit_header in dash:
    dash = dash.replace(old_lit_header, new_lit_header)
    with open(dashboard_path, 'w') as f:
        f.write(dash)
    print("Done — dashboard shows SEC VERIFIED badge and case numbers")
else:
    print("WARNING — lit header pattern not found in dashboard")

print("")
print("="*60)
print("SEC EDGAR DEEP PULL INSTALLED")
print("="*60)
print("")
print("What was built:")
print("  - secFilingsPuller.js pulls 10-K and 10-Q filings from EDGAR")
print("  - Extracts Legal Proceedings section (SEC-mandated disclosure)")
print("  - Claude parses into structured litigation items")
print("  - Merges with existing data, updating case names/numbers")
print("  - Schedules weekly on Sundays at 5 AM")
print("  - Dashboard shows green SEC VERIFIED badge on confirmed cases")
print("  - Shows exact case name, case number, court, exposure amount")
print("")
print("Test on Microsoft first:")
print("  npm run sec:account microsoft")
print("")
print("Then run all public company accounts:")
print("  npm run sec:pull")
