// secFilingsPuller.js
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
    const cikInt = parseInt(filing.cik).toString();
    const docUrl = `https://www.sec.gov/Archives/edgar/data/${cikInt}/${accNo}/${filing.primaryDocument}`;

    const response = await axios.get(docUrl, {
      headers: HEADERS,
      timeout: 60000,
      maxContentLength: 25 * 1024 * 1024,
      responseType: "text",
    });

    const html = response.data || "";

    // Clean HTML thoroughly
    const text = html
      .replace(/<style[^>]*>[\s\S]*?<\/style>/gi, "")
      .replace(/<script[^>]*>[\s\S]*?<\/script>/gi, "")
      .replace(/<[^>]+>/g, " ")
      .replace(/&nbsp;/g, " ")
      .replace(/&#160;/g, " ")
      .replace(/&amp;/g, "&")
      .replace(/&lt;/g, "<")
      .replace(/&gt;/g, ">")
      .replace(/&#8217;/g, "'")
      .replace(/&#8212;/g, "—")
      .replace(/&#[0-9]+;/g, " ")
      .replace(/\s+/g, " ")
      .trim();

    // Strategy 1: Find "Other Contingencies" section which has dollar amounts
    const contingIdx = text.indexOf("Other Contingencies");
    if (contingIdx > -1) {
      const section = text.slice(Math.max(0, contingIdx - 500), contingIdx + 3000);
      if (section.includes("accrued") || section.includes("million") || section.includes("claims")) {
        logger.info("  Found contingencies section with financial data");
        return {
          form: filing.form,
          date: filing.date,
          content: section,
          url: docUrl,
          section_type: "contingencies",
        };
      }
    }

    // Strategy 2: Find legal proceedings by searching for multiple legal keywords
    // and extracting the surrounding context
    const legalKeywords = ["antitrust", "class action", "patent infringement", "GDPR",
      "regulatory action", "legal proceedings", "plaintiff", "defendant"];

    const hits = [];
    for (const kw of legalKeywords) {
      const idx = text.toLowerCase().indexOf(kw.toLowerCase());
      if (idx > -1) hits.push({ keyword: kw, position: idx });
    }

    if (hits.length > 0) {
      // Sort by position and extract a wide window around all hits
      hits.sort((a, b) => a.position - b.position);
      const firstHit = hits[0].position;
      const lastHit = hits[hits.length - 1].position;

      // Find the start of the section (look back for Item 3 header)
      const sectionStart = Math.max(0, firstHit - 1000);
      const sectionEnd = Math.min(text.length, lastHit + 3000);
      const section = text.slice(sectionStart, sectionEnd);

      if (section.length > 200) {
        return {
          form: filing.form,
          date: filing.date,
          content: section.slice(0, 8000),
          url: docUrl,
          section_type: "legal_proceedings",
        };
      }
    }

    logger.warn(`  No legal proceedings content found in ${filing.form} for ${docUrl}`);
    return null;

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
    let searchFrom = 0;
    let attempts = 0;

    while (attempts < 5) {
      const idx = text.indexOf(header, searchFrom);
      if (idx === -1) break;
      attempts++;
      searchFrom = idx + header.length;

      // Skip table of contents hits — real section has substantive content
      // ToC hits are short (just page numbers), real section has paragraphs
      const nextHeaders = ["ITEM 4", "Item 4", "ITEM 1A", "Item 1A", "MINE SAFETY", "Risk Factors"];
      let endIdx = idx + 10000;
      for (const next of nextHeaders) {
        const nextIdx = text.indexOf(next, idx + header.length + 50);
        if (nextIdx > idx && nextIdx < endIdx) endIdx = nextIdx;
      }

      const section = text.slice(idx, endIdx).trim();

      // Real legal proceedings section has actual case descriptions
      // Skip if it looks like a ToC entry (too short or just page numbers)
      const hasSubstance = section.length > 500 &&
        (section.includes("plaintiff") || section.includes("defendant") ||
         section.includes("lawsuit") || section.includes("litigation") ||
         section.includes("complaint") || section.includes("court") ||
         section.includes("alleged") || section.includes("proceedings") ||
         section.includes("v.") || section.includes("vs."));

      if (hasSubstance) {
        return section.slice(0, 8000);
      }
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

    let raw = response.content
      .filter(b => b.type === "text").map(b => b.text).join("").trim();

    // Strip ALL markdown code fences aggressively
    raw = raw.replace(/^```(?:json)?\s*/im, "").replace(/```\s*$/im, "").trim();

    // Find the JSON array — start from first [ 
    const arrStart = raw.indexOf("[");
    const arrEnd = raw.lastIndexOf("]");
    if (arrStart > -1 && arrEnd > arrStart) {
      raw = raw.slice(arrStart, arrEnd + 1);
    }

    try {
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed : [];
    } catch(e2) {
      // Try to recover truncated JSON
      const lastBrace = raw.lastIndexOf("}");
      if (lastBrace > 0) {
        try {
          const recovered = JSON.parse(raw.slice(0, lastBrace + 1) + "]");
          return Array.isArray(recovered) ? recovered : [];
        } catch(e3) {}
      }
      logger.warn("SEC JSON recovery failed: " + e2.message);
      return [];
    }

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
      console.log("\nSEC filings pull complete:", results);
      process.exit(0);
    })
    .catch(err => {
      logger.error("Fatal error", { error: err.message });
      process.exit(1);
    });
}
