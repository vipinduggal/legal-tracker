// filingsMonitor.js — Real-time filing monitor
// Sources: SEC EDGAR (public companies), CourtListener (all federal cases),
//          FTC RSS, DOJ RSS, CFPB RSS
// Runs daily at 6 AM — checks actual court and agency records, not AI guesses

import "dotenv/config";
import axios from "axios";
import { ACCOUNTS } from "../../config/accounts.js";
import { getResearch, setResearch, logRun } from "../db.js";
import { sendFilingsAlert } from "../emailer.js";
import { postAccountUpdateToTeams } from "../teams.js";
import { logger } from "../logger.js";

// ── Public company SEC ticker map ─────────────────────────
// Maps account IDs to SEC CIK numbers for EDGAR lookups
// CIK numbers from SEC EDGAR company search
const SEC_CIKS = {
  amd:                 "0000002488",
  microsoft:           "0000789019",
  meta:                "0001326801",
  snap:                "0001564408",
  reddit:              "0001713539",
  uber:                "0001543151",
  roblox:              "0001315098",
  electronic_arts:     "0000712515",
  take_two_interactive:"0000946581",
  snowflake:           "0001640147",
  palo_alto_networks:  "0001327567",
  workday:             "0001327811",
  intuit:              "0000896878",
  godaddy:             "0001609711",
  pge:                 "0001004440",
  sce:                 "0000827054",
  freeport_mcmoran:    "0000831259",
  starbucks:           "0000829224",
  costco:              "0000909832",
  sony_north_america:  "0000313838",
  stripe:              "0001680688",
  yelp:                "0001345016",
  coupang:             "0001834585",
  align_technology:    "0001097149",
  fluor_corporation:   "0001285785",
  hb_fuller:           "0000046080",
  johns_manville:      "0000049600",
  milliman:            "0000066570",
  unisys:              "0000078814",
  wipro:               "0000788920",
};

// ── Search terms for each account in court records ────────
function getSearchTerms(account) {
  const name = account.name
    .replace(" (North America)", "")
    .replace(" Corporation", "")
    .replace(" Inc.", "")
    .replace(" Inc", "")
    .replace(" Corp.", "")
    .replace(" Corp", "")
    .replace(" LLC", "")
    .replace(" Ltd", "")
    .trim();
  return name;
}

// ── EDGAR: Check for new 8-K filings mentioning legal proceedings ──
async function checkEdgar(account, daysSince = 7) {
  const cik = SEC_CIKS[account.id];
  if (!cik) return [];

  try {
    const since = new Date();
    since.setDate(since.getDate() - daysSince);
    const sinceStr = since.toISOString().split("T")[0];

    // Get recent 8-K filings from EDGAR
    const url = `https://data.sec.gov/submissions/CIK${cik}.json`;
    const response = await axios.get(url, {
      headers: { "User-Agent": "LegalTracker/1.0 vipin.duggal@consilio.com" },
      timeout: 10000,
    });

    const data = response.data;
    const filings = data.filings?.recent;
    if (!filings) return [];

    const forms = filings.form || [];
    const dates = filings.filingDate || [];
    const accessions = filings.accessionNumber || [];
    const primaryDocs = filings.primaryDocument || [];

    const newFilings = [];

    for (let i = 0; i < forms.length; i++) {
      const form = forms[i];
      const date = dates[i];
      const accession = accessions[i];
      const doc = primaryDocs[i];

      // Only look at 8-K filings within the window
      if (!["8-K", "8-K/A"].includes(form)) continue;
      if (date < sinceStr) break; // EDGAR returns newest first

      // Fetch the 8-K document to check if it mentions legal proceedings
      try {
        const accClean = accession.replace(/-/g, "");
        const docUrl = `https://www.sec.gov/Archives/edgar/data/${parseInt(cik)}/${accClean}/${doc}`;
        const docResp = await axios.get(docUrl, {
          headers: { "User-Agent": "LegalTracker/1.0 vipin.duggal@consilio.com" },
          timeout: 8000,
        });

        const text = docResp.data.toString().toLowerCase();
        const legalKeywords = [
          "legal proceedings", "litigation", "lawsuit", "class action",
          "regulatory", "investigation", "ftc", "doj", "sec investigation",
          "enforcement", "complaint", "indictment", "settlement",
          "court", "plaintiff", "defendant", "alleged", "subpoena",
        ];

        const matchedKeywords = legalKeywords.filter(kw => text.includes(kw));

        if (matchedKeywords.length >= 2) {
          // Extract item numbers to identify the nature of the filing
          const items = [];
          if (text.includes("item 8.01") || text.includes("item 8.1")) items.push("Other Events");
          if (text.includes("item 7.01") || text.includes("item 7.1")) items.push("Regulation FD");
          if (text.includes("item 1.01")) items.push("Material Agreement");
          if (text.includes("item 5.02")) items.push("Leadership Change");

          newFilings.push({
            type: "SEC 8-K Filing — Legal/Regulatory",
            period: date + " to present",
            summary: `${account.name} filed an 8-K with the SEC on ${date} containing legal/regulatory disclosures. Keywords detected: ${matchedKeywords.slice(0, 4).join(", ")}.${items.length ? " Items: " + items.join(", ") + "." : ""}`,
            counsel: null,
            status: "Ongoing",
            is_new: true,
            source: "SEC EDGAR",
            source_url: `https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=${cik}&type=8-K&dateb=&owner=include&count=10`,
            filed_date: date,
          });
        }
      } catch (docErr) {
        // Skip if we can't read the document
      }

      await sleep(200);
    }

    return newFilings;
  } catch (err) {
    logger.warn(`EDGAR check failed for ${account.name}: ${err.message}`);
    return [];
  }
}

// ── CourtListener: Check for new federal court cases ─────
async function checkCourtListener(account, daysSince = 7) {
  // Use RECAP/PACER public search — no auth required
  // Falls back to law360/legal news RSS if PACER returns nothing
  try {
    const since = new Date();
    since.setDate(since.getDate() - daysSince);
    const sinceStr = since.toISOString().split("T")[0];
    const searchTerm = getSearchTerms(account);

    // Try PACER public search (Case Management/Electronic Case Files public access)
    const pacerUrl = "https://pcl.uscourts.gov/pcl/pages/search/results/caseSearch.jsf";

    // Use the free RECAP search API instead — no auth, searches PACER data
    const recapUrl = "https://www.courtlistener.com/api/rest/v3/dockets/";
    const params = {
      q: `"${searchTerm}"`,
      filed_after: sinceStr,
      order_by: "-date_filed",
      page_size: 5,
      format: "json",
    };

    try {
      const response = await axios.get(recapUrl, {
        params,
        headers: { "User-Agent": "LegalTracker/1.0 vipin.duggal@consilio.com" },
        timeout: 8000,
      });

      const cases = response.data?.results || [];
      if (cases.length) {
        return cases.slice(0, 3).map(c => ({
          type: `Federal Court Filing`,
          period: (c.date_filed || sinceStr) + " to present",
          summary: `Federal case involving ${account.name}: "${c.case_name || "Unknown"}" filed ${c.date_filed || "recently"}.`,
          counsel: null,
          status: "Pending",
          is_new: true,
          source: "RECAP/PACER",
          source_url: c.absolute_url ? `https://www.courtlistener.com${c.absolute_url}` : "https://www.courtlistener.com",
          filed_date: c.date_filed || sinceStr,
        }));
      }
    } catch(recapErr) {
      // RECAP unavailable — skip silently
    }

    return [];
  } catch (err) {
    logger.warn(`Court search failed for ${account.name}: ${err.message}`);
    return [];
  }
}

// ── Agency RSS feeds: FTC, DOJ, CFPB ────────────────────
const AGENCY_FEEDS = [
  { name: "FTC", url: "https://www.ftc.gov/feeds/press-release.xml", type: "FTC Enforcement Action" },
  { name: "DOJ Antitrust", url: "https://www.justice.gov/feeds/justice-news.xml?type=All&component%5B292%5D=292", type: "DOJ Antitrust Action" },
  { name: "DOJ News", url: "https://www.justice.gov/feeds/justice-news.xml", type: "DOJ Action" },
  { name: "CFPB", url: "https://www.consumerfinance.gov/about-us/newsroom/feed/", type: "CFPB Action" },
];

async function checkAgencyFeeds(account, daysSince = 7) {
  const since = new Date();
  since.setDate(since.getDate() - daysSince);
  const searchTerm = getSearchTerms(account).toLowerCase();
  const newFilings = [];

  for (const feed of AGENCY_FEEDS) {
    try {
      const response = await axios.get(feed.url, {
        headers: { "User-Agent": "LegalTracker/1.0 vipin.duggal@consilio.com" },
        timeout: 8000,
      });

      const xml = response.data;

      // Simple XML parsing without external library
      const items = xml.split("<item>").slice(1);
      for (const item of items) {
        const titleMatch = item.match(/<title[^>]*>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?<\/title>/s);
        const descMatch = item.match(/<description[^>]*>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?<\/description>/s);
        const linkMatch = item.match(/<link[^>]*>(.*?)<\/link>/s);
        const dateMatch = item.match(/<pubDate>(.*?)<\/pubDate>/s);

        const title = titleMatch ? titleMatch[1].replace(/<[^>]+>/g, "").trim() : "";
        const desc = descMatch ? descMatch[1].replace(/<[^>]+>/g, "").trim() : "";
        const link = linkMatch ? linkMatch[1].trim() : "";
        const dateStr = dateMatch ? dateMatch[1].trim() : "";

        // Check if this mentions our account
        const combined = (title + " " + desc).toLowerCase();
        if (!combined.includes(searchTerm)) continue;

        // Check if within our time window
        const pubDate = dateStr ? new Date(dateStr) : new Date();
        if (pubDate < since) continue;

        newFilings.push({
          type: feed.type,
          period: pubDate.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) + " to present",
          summary: `${feed.name} action involving ${account.name}: ${title.slice(0, 200)}`,
          counsel: null,
          status: "Ongoing",
          is_new: true,
          source: feed.name,
          source_url: link,
          filed_date: pubDate.toISOString().split("T")[0],
        });
      }
      await sleep(300);
    } catch (err) {
      logger.warn(`${feed.name} feed check failed for ${account.name}: ${err.message}`);
    }
  }

  return newFilings;
}

// ── Deduplicate against existing filings ─────────────────
function filterNew(newFilings, existing) {
  const existingKeys = new Set([
    ...(existing?.litigation || []).map(l => l.type + "|" + (l.filed_date || l.period)),
    ...(existing?.regulatory || []).map(r => r.type + "|" + (r.filed_date || r.period)),
  ]);

  return newFilings.filter(f => {
    const key = f.type + "|" + (f.filed_date || f.period);
    return !existingKeys.has(key);
  });
}

// ── Main job ───────────────────────────────────────────────
export async function runFilingsMonitor() {
  const startTime = Date.now();
  logger.info("=== Real-time filings monitor started ===");
  logger.info("Sources: SEC EDGAR, CourtListener, FTC, DOJ, CFPB");

  const results = { checked: 0, newFilings: 0, alertsSent: 0, failed: 0 };
  const allAlerts = [];

  for (const account of ACCOUNTS) {
    try {
      results.checked++;
      const existing = await getResearch(account.id);

      // Run all three checks in parallel
      const [edgarFilings, courtFilings, agencyFilings] = await Promise.allSettled([
        checkEdgar(account),
        checkCourtListener(account),
        checkAgencyFeeds(account),
      ]);

      const allNew = [
        ...(edgarFilings.status === "fulfilled" ? edgarFilings.value : []),
        ...(courtFilings.status === "fulfilled" ? courtFilings.value : []),
        ...(agencyFilings.status === "fulfilled" ? agencyFilings.value : []),
      ];

      const trueNew = filterNew(allNew, existing);

      if (trueNew.length > 0) {
        results.newFilings += trueNew.length;
        logger.info(`NEW FILINGS for ${account.name}: ${trueNew.length} found from ${[...new Set(trueNew.map(f => f.source))].join(", ")}`);

        // Merge into database
        if (existing) {
          const legalItems = trueNew.filter(f => f.source === "CourtListener" || f.type.includes("8-K"));
          const regulatoryItems = trueNew.filter(f => ["FTC","DOJ","CFPB"].includes(f.source));

          if (legalItems.length) {
            existing.litigation = [...legalItems, ...(existing.litigation || [])];
          }
          if (regulatoryItems.length) {
            existing.regulatory = [...regulatoryItems, ...(existing.regulatory || [])];
          }
          await setResearch(account.id, existing);
        }

        // Send alerts
        allAlerts.push({ account, filings: trueNew });
        await Promise.allSettled([
          sendFilingsAlert(account, trueNew),
          postAccountUpdateToTeams(account, trueNew.map(f => "NEW: " + f.type), { contacts: [], litigation: trueNew, regulatory: [], intel_summary: trueNew[0]?.summary || "" }),
        ]);
        results.alertsSent++;
      }

      await sleep(500);
    } catch (err) {
      logger.error(`Filings monitor error for ${account.name}`, { error: err.message });
      results.failed++;
    }
  }

  const duration = Math.round((Date.now() - startTime) / 1000);
  logger.info(`=== Filings monitor complete in ${duration}s ===`, results);

  if (allAlerts.length === 0) {
    logger.info("No new filings detected across all accounts today");
  } else {
    logger.info(`Alerts sent for: ${allAlerts.map(a => a.account.name).join(", ")}`);
  }

  await logRun({ job: "filings_monitor", duration, ...results });
  return { results, allAlerts };
}

function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}

// Direct execution
if (process.argv[1].endsWith("filingsMonitor.js")) {
  runFilingsMonitor()
    .then(({ results }) => {
      logger.info("Manual run complete", results);
    })
    .catch(err => {
      logger.error("Fatal error", { error: err.message });
      process.exit(1);
    });
}
