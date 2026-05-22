// courtListenerMonitor.js
// Pulls real federal court docket data from CourtListener
// Uses search API only — no rate-limited detail endpoints
// Extracts: outside counsel, named partners, case type, suit nature
// Runs daily at 6:45 AM

import "dotenv/config";
import axios from "axios";
import { ACCOUNTS } from "../../config/accounts.js";
import { getResearch, setResearch, logRun, hasBeenNotified, markNotified } from "../db.js";
import { logger } from "../logger.js";

const CL_BASE = "https://www.courtlistener.com/api/rest/v4";
const CL_TOKEN = process.env.COURTLISTENER_TOKEN;

// High-value NOS codes — cases that generate significant eDiscovery
const HIGH_VALUE_NOS = {'410': 'Antitrust', '850': 'Securities Class Action', '830': 'Patent', '820': 'Copyright', '190': 'Contract Dispute', '191': 'Contract: Medicare', '192': 'Contract: Marine', '193': 'Contract: Miller Act', '195': 'Contract: Products Liability', '440': 'Civil Rights', '441': 'Civil Rights: Voting', '442': 'Civil Rights: Employment', '443': 'Civil Rights: Housing', '444': 'Civil Rights: Welfare', '445': 'Civil Rights: ADA Employment', '446': 'Civil Rights: ADA Other', '448': 'Civil Rights: Education', '791': 'ERISA', '470': 'RICO', '480': 'Consumer Credit', '890': 'Other Statutory Actions', '380': 'Personal Property Fraud'};

// NOS codes worth alerting on immediately
const IMMEDIATE_NOS = new Set(["410", "850", "830", "820", "470", "480"]);

function clHeaders() {
  return { "Authorization": `Token ${CL_TOKEN}` };
}

// Determine which attorneys represent the defendant (our account)
function extractDefenseCounsel(attorneys, firms, parties, companyName) {
  if (!attorneys?.length && !firms?.length) return null;

  const companyWords = companyName.toLowerCase().split(" ").filter(w => w.length > 3);

  // Find defense counsel by identifying which firms appear alongside the company
  // Filter out pro se litigants (people representing themselves — same name appears in both attorneys and parties)
  const partyNames = new Set((parties || []).map(p => p.toLowerCase().trim()));

  const validFirms = (firms || []).filter(f => {
    if (!f || f.length < 5) return false;
    // Skip if firm name matches a party (pro se)
    if (partyNames.has(f.toLowerCase().trim())) return false;
    // Skip obvious non-firms
    if (f.match(/^[A-Z][a-z]+ [A-Z][a-z]+$/) && !f.includes("LLP") && !f.includes("LLC") && !f.includes("PC")) {
      // Might be a person's name — check if it's in attorneys list too
      return false;
    }
    return true;
  });

  const validAttorneys = (attorneys || []).filter(a => {
    if (!a || a.length < 3) return false;
    // Skip if attorney name matches a party (pro se)
    if (partyNames.has(a.toLowerCase().trim())) return false;
    return true;
  });

  if (!validFirms.length && !validAttorneys.length) return null;

  return {
    firms: validFirms.slice(0, 3),
    attorneys: validAttorneys.slice(0, 4),
    primary_firm: validFirms[0] || null,
  };
}

// Get NOS description
function getNOSDescription(suitNature) {
  if (!suitNature) return null;
  // Extract NOS code from string like "410 Anti-Trust"
  const codeMatch = suitNature.match(/^(\d+)/);
  if (codeMatch) {
    const code = codeMatch[1];
    return HIGH_VALUE_NOS[code] || suitNature;
  }
  return suitNature;
}

// Determine if this is a high-value eDiscovery case
function isHighValueCase(suitNature) {
  if (!suitNature) return false;
  const codeMatch = suitNature.match(/^(\d+)/);
  if (codeMatch) return !!HIGH_VALUE_NOS[codeMatch[1]];
  // Also check by keywords
  const lower = suitNature.toLowerCase();
  return lower.includes("antitrust") || lower.includes("securities") ||
         lower.includes("patent") || lower.includes("copyright") ||
         lower.includes("rico") || lower.includes("class action");
}

// Search CourtListener for active cases involving a company
async function searchActiveCases(companyName) {
  try {
    // 18 months back — sweet spot for active discovery
    const cutoff = new Date(Date.now() - 18 * 30 * 24 * 60 * 60 * 1000)
      .toISOString().split("T")[0];

    const response = await axios.get(`${CL_BASE}/search/`, {
      headers: clHeaders(),
      params: {
        q: `"${companyName}"`,
        type: "d",
        order_by: "score desc",
        page_size: 30,
        filed_after: cutoff,
      },
      timeout: 15000,
    });

    const results = response.data?.results || [];
    const companyFirst = companyName.toLowerCase().split(" ")[0];

    // Filter to active cases where company is actually a party
    const active = results.filter(d => {
      const name = (d.caseName || "").toLowerCase();
      if (!name.includes(companyFirst)) return false;
      if (d.dateTerminated) return false;
      if (!d.docket_id) return false;
      return true;
    });

    // Prioritize high-value cases
    const highValue = active.filter(d => isHighValueCase(d.suitNature));
    const other = active.filter(d => !isHighValueCase(d.suitNature));

    logger.info(`  CourtListener: ${results.length} results → ${active.length} active (${highValue.length} high-value) for ${companyName}`);

    // Return high-value first, then others
    return [...highValue, ...other].slice(0, 10);

  } catch(err) {
    if (err.response?.status === 401) {
      logger.warn("CourtListener auth failed — check COURTLISTENER_TOKEN in .env");
    } else {
      logger.warn(`CourtListener search failed for ${companyName}: ${err.response?.status} ${err.message}`);
    }
    return [];
  }
}

// Build structured litigation item from CourtListener search result
function buildLitItem(searchResult, companyName) {
  const counsel = extractDefenseCounsel(
    searchResult.attorney,
    searchResult.firm,
    searchResult.party,
    companyName
  );

  const nosDesc = getNOSDescription(searchResult.suitNature);
  const isHigh = isHighValueCase(searchResult.suitNature);

  return {
    case_name: searchResult.caseName,
    case_number: searchResult.docketNumber,
    court: searchResult.court_id || searchResult.court,
    type: nosDesc || searchResult.cause || searchResult.caseName,
    period: (searchResult.dateFiled || "").slice(0, 7) + " to present",
    summary: `${searchResult.caseName} — ${searchResult.cause || nosDesc || "Federal case"} — Filed ${searchResult.dateFiled || "recently"} in ${(searchResult.court_id || "").toUpperCase()}`,
    status: "Pending",
    outside_counsel_firm: counsel?.primary_firm || null,
    all_counsel_firms: counsel?.firms || [],
    lead_partners: counsel?.attorneys || [],
    counsel_verified: !!(counsel?.primary_firm),
    courtlistener_verified: true,
    courtlistener_id: searchResult.docket_id,
    suit_nature: searchResult.suitNature,
    cause: searchResult.cause,
    parties: searchResult.party || [],
    is_high_value: isHigh,
    is_new: true,
    courtlistener_url: `https://www.courtlistener.com${searchResult.docket_absolute_url || ""}`,
    last_enriched: new Date().toISOString(),
  };
}

// Main job
export async function runCourtListenerMonitor(accountId) {
  if (!CL_TOKEN) {
    logger.warn("COURTLISTENER_TOKEN not set — skipping CourtListener monitor");
    return { checked: 0, enriched: 0, alerts: 0, failed: 0 };
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

      results.checked++;
      logger.info(`Searching CourtListener for ${account.name}...`);

      const cases = await searchActiveCases(account.name);

      if (!cases.length) {
        logger.info(`  No active cases found for ${account.name}`);
        await new Promise(r => setTimeout(r, 1000));
        continue;
      }

      // Merge new cases with existing litigation data
      const existingKeys = new Set(
        (data.litigation || []).map(l =>
          (l.case_number || l.case_name || "").toLowerCase()
        )
      );

      let newCases = 0;
      let updatedCases = 0;

      for (const searchCase of cases) {
        const caseNum = (searchCase.docketNumber || "").toLowerCase();
        const caseName = (searchCase.caseName || "").toLowerCase();

        const existing = (data.litigation || []).find(l =>
          (l.case_number || "").toLowerCase() === caseNum ||
          (l.case_name || "").toLowerCase().includes(caseName.split(" v.")[0]?.trim() || "")
        );

        const litItem = buildLitItem(searchCase, account.name);

        if (existing) {
          // Update existing with CourtListener data
          Object.assign(existing, {
            case_name: litItem.case_name,
            case_number: litItem.case_number,
            court: litItem.court,
            outside_counsel_firm: litItem.outside_counsel_firm || existing.outside_counsel_firm,
            all_counsel_firms: litItem.all_counsel_firms,
            lead_partners: litItem.lead_partners,
            counsel_verified: litItem.counsel_verified,
            courtlistener_verified: true,
            courtlistener_id: litItem.courtlistener_id,
            courtlistener_url: litItem.courtlistener_url,
            suit_nature: litItem.suit_nature,
            is_high_value: litItem.is_high_value,
            parties: litItem.parties,
            last_enriched: new Date().toISOString(),
          });
          updatedCases++;
        } else {
          // Add new case
          data.litigation = data.litigation || [];
          data.litigation.push({ ...litItem, is_new: true });
          newCases++;
          logger.info(`  New case: ${litItem.case_name} (${litItem.case_number}) — ${litItem.suit_nature}`);
          if (litItem.outside_counsel_firm) {
            logger.info(`  Defense counsel: ${litItem.outside_counsel_firm} — ${litItem.lead_partners.slice(0,2).join(", ")}`);
          }
        }

        // Alert on high-value new cases
        const alertKey = `cl:${searchCase.docket_id}:new_case`;
        if (litItem.is_high_value && !hasBeenNotified(account.id, alertKey)) {
          await markNotified(account.id, alertKey);
          results.alerts++;
          logger.info(`  HIGH VALUE CASE ALERT: ${account.name} — ${litItem.type} — ${litItem.outside_counsel_firm || "Unknown counsel"}`);
        }
      }

      if (newCases > 0 || updatedCases > 0) {
        data.courtlistener_last_checked = new Date().toISOString();
        await setResearch(account.id, data);
        results.enriched++;
        logger.info(`  ${account.name}: ${newCases} new cases, ${updatedCases} updated`);
      }

      // Polite delay between accounts
      await new Promise(r => setTimeout(r, 2000));

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
      console.log("\nCourtListener monitor complete:", results);
      process.exit(0);
    })
    .catch(err => {
      console.error("Fatal:", err.message);
      process.exit(1);
    });
}
