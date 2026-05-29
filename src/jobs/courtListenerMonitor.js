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

// Known plaintiff-side litigation firms — they represent plaintiffs not corporate defendants
const PLAINTIFF_FIRMS = [
  // Securities/class action plaintiff firms
  "lieff cabraser", "milberg", "hagens berman", "girard sharp",
  "susman godfrey", "bernstein litowitz", "labaton", "keller rohrback",
  "scott+scott", "cohen milstein", "robbins geller", "wolf popper",
  "pomerantz", "kaplan fox", "glancy prongay", "levi & korsinsky",
  "bleichmar fonti", "grant & eisenhofer", "simmons hanly", "motley rice",
  "weitz & luxenberg", "seeger weiss", "levin papantonio", "morgan & morgan",
  "consumer attorneys", "laffey leitner", "beasley allen", "rosen law",
  "karpf karpf", "the rosen law", "chimicles", "faruqi", "bronstein",
  "wolf haldenstein", "saxena white", "bottini & bottini",
  "kilsheimer", "kirby mcinerney", "block & leviton", "kessler topaz",
  "berger montague", "kessler", "abraham fruchter", "kahn swick",
  "schubert jonckheer", "rigrodsky", "monteverde",
  // Copyright/IP plaintiff firms  
  "tousley", "cowan debaets", "hartline barger", "copyright",
  "boies schiller", "susman godfrey",
  // Employment plaintiff firms
  "hawks quindel", "bryan schwartz", "outten & golden", "sanford heisler",
  "nichols kaster", "joseph & kirschenbaum", "virginia employment",
  "mixon law", "karpf", "consumer law",
  // Consumer/fraud plaintiff firms
  "doyle lowther", "blood hurst", "capstone law", "callahan & blaine",
  "stevenson & keppelman", "siri glimstad", "migliaccio",
  "law offices of david n lake", "edelson",
  // Mass tort plaintiff firms
  "arnold & itkin", "napoli shkolnik",
];

// Known BigLaw defense firms — these almost always represent corporations
// AmLaw 200 + adjacent national defense/BigLaw firms. Lowercase, fuzzy-substring matched.
// Refresh annually when AmLaw publishes the new ranking.
const BIGLAW_DEFENSE = [
  // Top 50 — the original list, kept here
  "orrick", "perkins coie", "davis wright", "dechert", "kirkland",
  "paul weiss", "sullivan & cromwell", "skadden", "latham", "gibson dunn",
  "sidley austin", "jones day", "mayer brown", "willkie farr", "cooley",
  "wilson sonsini", "fenwick", "morrison & foerster", "covington",
  "hogan lovells", "white & case", "cleary gottlieb", "paul hastings",
  "fish & richardson", "quinn emanuel", "irell & manella", "weil gotshal",
  "simpson thacher", "debevoise", "cahill gordon", "cravath",
  "milbank", "shearman", "freshfields", "linklaters", "allen & overy",
  // AmLaw 51–100
  "akin gump", "alston & bird", "arnold & porter", "ballard spahr",
  "barnes & thornburg", "bryan cave", "buchanan ingersoll", "carlton fields",
  "cozen o'connor", "crowell & moring", "duane morris", "epstein becker",
  "faegre drinker", "finnegan", "foley & lardner", "foley hoag",
  "fox rothschild", "fragomen", "fried frank", "gardere",
  "goldberg segalla", "goodwin procter", "greenberg traurig", "haynes and boone",
  "hogan & hartson", "holland & knight", "husch blackwell", "jackson lewis",
  "k&l gates", "kasowitz", "katten muchin", "kilpatrick townsend",
  "king & spalding", "littler mendelson", "locke lord", "loeb & loeb",
  "manatt phelps", "mcdermott will", "mcguirewoods", "miller canfield",
  "morgan lewis", "munger tolles", "nelson mullins", "nixon peabody",
  "norton rose", "ogletree deakins", "polsinelli", "proskauer",
  "reed smith", "ropes & gray", "saul ewing", "schulte roth",
  "seyfarth shaw", "shearman & sterling", "sheppard mullin", "shook hardy",
  "shumaker loop", "snell & wilmer", "squire patton boggs", "steptoe & johnson",
  "stoel rives", "stradley ronon", "thompson coburn", "thompson hine",
  "troutman pepper", "venable", "vinson & elkins", "wachtell",
  "wiggin and dana", "wiley rein", "williams & connolly", "winston & strawn",
  // AmLaw 101–200
  "adams and reese", "akerman", "armstrong teasdale", "baker botts",
  "baker hostetler", "baker mckenzie", "baker donelson", "bakerhostetler",
  "ballard", "blank rome", "boies schiller flexner", "bradley arant",
  "buchalter", "burns & levinson", "butler snow", "cadwalader",
  "carmody torrance", "chapman and cutler", "clark hill", "cole schotz",
  "constangy brooks", "cordell parvin", "cotton schmidt", "crowe & dunlevy",
  "curtis mallet", "davis polk", "day pitney", "dechert llp",
  "dentons", "dickinson wright", "dla piper", "dorsey & whitney",
  "dykema", "eckert seamans", "fennemore craig", "ford harrison",
  "frost brown todd", "gibson dunn & crutcher", "godfrey & kahn",
  "gordon rees", "gordon arata", "graydon head", "greenberg glusker",
  "gunderson dettmer", "hanson bridgett", "harris beach", "harter secrest",
  "haynsworth sinkler", "herbert smith", "honigman", "hunton andrews",
  "jackson kelly", "jackson walker", "jaffe raitt", "jenner & block",
  "johnson & bell", "kelley drye", "kennedys", "kirton mcconkie",
  "krieg devault", "kutak rock", "lewis brisbois", "lewis roca",
  "lewis rice", "lindquist & vennum", "littler", "long & levit",
  "lowenstein sandler", "macdonald devin", "mcdonald hopkins",
  "mintz levin", "moore & van allen", "morris james", "morris manning",
  "morris nichols", "moses & singer", "moss adams", "munsch hardt",
  "nutter mcclennen", "obermayer rebmann", "ogletree", "olshan frome",
  "patterson belknap", "peabody & arnold", "perkins coie llp",
  "phelps dunbar", "phillips lytle", "phillips nizer", "pillsbury winthrop",
  "porter wright", "potter anderson", "richards layton", "riker danzig",
  "roetzel & andress", "rumberger kirk", "saul ewing arnstein",
  "saunders & silverstein", "schiff hardin", "schwabe williamson",
  "shipman & goodwin", "sills cummis", "smith gambrell",
  "spencer fane", "spilman thomas", "stinson", "stites & harbison",
  "stoll keenon", "stradling yocca", "strasburger & price",
  "sullivan & worcester", "taft stettinius", "thompson & knight",
  "trenam law", "tucker arensberg", "tucker ellis",
  "varnum", "warner norcross", "waller lansden", "weintraub tobin",
  "white and williams", "wilentz", "williams kastner", "williams mullen",
  "wilmer cutler pickering", "wilmerhale", "winstead",
  "womble bond dickinson", "young conaway",
];

function isDefenseFirm(firmName) {
  if (!firmName) return false;
  const lower = firmName.toLowerCase();
  return BIGLAW_DEFENSE.some(df => lower.includes(df));
}

function isPlaintiffFirm(firmName) {
  if (!firmName) return false;
  const lower = firmName.toLowerCase();
  return PLAINTIFF_FIRMS.some(pf => lower.includes(pf));
}

function isValidFirm(firmName, partyNames) {
  if (!firmName || firmName.length < 5 || firmName.length > 80) return false;
  if (partyNames.has(firmName.toLowerCase().trim())) return false; // pro se
  if (/^\d/.test(firmName)) return false; // starts with number
  if (firmName.toLowerCase().includes('direct:')) return false; // phone
  if (firmName.toLowerCase().includes('e-filing')) return false;
  return true;
}

function isValidAttorney(name, partyNames) {
  if (!name || name.length < 4 || name.length > 60) return false;
  if (partyNames.has(name.toLowerCase().trim())) return false;
  if (name.toLowerCase().includes('e-filing')) return false;
  if (/^\d/.test(name)) return false;
  if (name.toLowerCase().includes('direct:')) return false;
  const words = name.trim().split(/\s+/);
  if (words.length < 2) return false; // need first + last name
  return true;
}

// Extract counsel and correctly identify plaintiff vs defense firms
function extractDefenseCounsel(attorneys, firms, parties, companyName, companyIsDefendant = true) {
  const partyNames = new Set((parties || []).map(p => p.toLowerCase().trim()));

  const validFirms = (firms || []).filter(f => isValidFirm(f, partyNames));
  const validAttorneys = (attorneys || []).filter(a => isValidAttorney(a, partyNames));

  // Match attorneys to their firms using index position
  // CourtListener returns attorneys and firms as parallel arrays
  // attorney[i] is associated with firm[i]
  const attorneyFirmMap = {};
  const rawFirms = firms || [];
  const rawAttorneys = attorneys || [];
  for (let i = 0; i < rawAttorneys.length; i++) {
    const atty = rawAttorneys[i];
    const firm = rawFirms[i] || rawFirms[0] || null;
    if (atty && firm) {
      if (!attorneyFirmMap[firm]) attorneyFirmMap[firm] = [];
      attorneyFirmMap[firm].push(atty);
    }
  }

  // Separate firms into three buckets:
  // 1. Known defense/BigLaw firms — show as defense counsel
  // 2. Known plaintiff firms — label as plaintiff counsel
  // 3. Unknown — could be either side

  const knownDefenseFirms = validFirms.filter(f => isDefenseFirm(f));
  const knownPlaintiffFirms = validFirms.filter(f => isPlaintiffFirm(f));
  const unknownFirms = validFirms.filter(f => !isDefenseFirm(f) && !isPlaintiffFirm(f));

  // Only call something "defense" if we know it is.
  // Never promote unknown firms — doing so risks labeling a plaintiff firm
  // (e.g., Kilsheimer) as defense counsel, which burns sales credibility.
  const defenseFirms = knownDefenseFirms;
  // Unknown firms are kept separately and shown without a side label.
  const unclassifiedFirms = unknownFirms;

  const plaintiffFirms = knownPlaintiffFirms;
  const primaryFirm = defenseFirms[0] || null;

  // If company is plaintiff (suing someone), show their own counsel
  if (!companyIsDefendant) {
    return {
      firms: defenseFirms.length ? defenseFirms.slice(0, 3) : validFirms.slice(0, 3),
      attorneys: validAttorneys.slice(0, 4),
      primary_firm: defenseFirms[0] || validFirms[0] || null,
      plaintiff_firms: [],
      unclassified_firms: unclassifiedFirms.slice(0, 5),
      counsel_role: "plaintiff",
    };
  }

  // Company is defendant — show defense counsel, label plaintiff counsel separately
  // Get attorneys specifically associated with the defense firm
  let defenseAttorneys = [];
  if (primaryFirm) {
    // Try exact match first
    defenseAttorneys = (attorneyFirmMap[primaryFirm] || []).filter(a => isValidAttorney(a, partyNames));
    // If no match, try partial match
    if (!defenseAttorneys.length) {
      for (const [firm, attys] of Object.entries(attorneyFirmMap)) {
        if (isDefenseFirm(firm) && !isPlaintiffFirm(firm)) {
          defenseAttorneys = attys.filter(a => isValidAttorney(a, partyNames));
          if (defenseAttorneys.length) break;
        }
      }
    }
  }

  return {
    firms: defenseFirms.slice(0, 3),
    attorneys: defenseAttorneys.slice(0, 4),
    primary_firm: primaryFirm,
    plaintiff_firms: plaintiffFirms.slice(0, 2),
    unclassified_firms: unclassifiedFirms.slice(0, 5),
    counsel_role: primaryFirm ? "defense" : (plaintiffFirms.length ? "plaintiff_only" : "unknown"),
    company_is_defendant: true,
  };
}

// Get NOS description
// Generate immediate and strategic triggers from CourtListener cases
function generateTriggersFromCases(cases, accountName) {
  const immediate = [];
  const strategic = [];

  // NOS codes that indicate very high document volume
  const CRITICAL_NOS = new Set(["410", "850"]);
  const HIGH_NOS = new Set(["830", "820", "470", "480"]);

  for (const c of cases) {
    if (!c.is_high_value) continue;

    const nosCode = (c.suit_nature || "").match(/^(\d+)/)?.[1] || "";
    const urgency = CRITICAL_NOS.has(nosCode) ? "Critical" :
                    HIGH_NOS.has(nosCode) ? "High" : "Medium";

    const counsel = c.outside_counsel_firm ?
      `Outside counsel: ${c.outside_counsel_firm}` +
      (c.lead_partners?.length ? ` (${c.lead_partners.slice(0,2).join(", ")})` : "") :
      "Outside counsel not yet identified";

    const filedDate = (c.period || "").split(" ")[0] || "Recently";

    // Immediate trigger — new case filed in last 6 months
    if (c.is_new || c.courtlistener_verified) {
      immediate.push({
        trigger: `${c.case_name || c.type} (${c.case_number || "docket pending"}) — ${c.suit_nature || c.type} filed in ${c.court || "federal court"}. ${counsel}.`,
        date: filedDate,
        sales_implication: buildSalesImplication(c),
        urgency,
        source: "CourtListener/PACER",
        case_number: c.case_number,
        court: c.court,
        outside_counsel: c.outside_counsel_firm,
      });
    }

    // Strategic trigger for sustained litigation patterns
    if (cases.filter(x => x.is_high_value).length >= 3) {
      // Multiple high-value cases = strategic pattern
      strategic.push({
        trigger: `${accountName} has ${cases.filter(x => x.is_high_value).length} active high-value federal cases including ${c.type} — sustained litigation creating ongoing document review and eDiscovery demand.`,
        timeframe: "Active now",
        sales_implication: `Position Consilio as preferred eDiscovery and document review partner. Multiple simultaneous matters create opportunity for master services agreement and volume pricing conversation.`,
        angle: "Enterprise eDiscovery partnership — master services agreement",
        source: "CourtListener/PACER",
      });
      break; // Only add one strategic trigger per account
    }
  }

  return { immediate, strategic };
}

function buildSalesImplication(litItem) {
  const nos = (litItem.suit_nature || "").toLowerCase();
  const counsel = litItem.outside_counsel_firm || "outside counsel";

  if (nos.includes("410") || nos.includes("antitrust")) {
    return `Antitrust cases typically involve millions of documents. ${counsel} will need eDiscovery support immediately. Contact now before vendor selection is finalized — typically happens within 60 days of case filing.`;
  } else if (nos.includes("850") || nos.includes("securities")) {
    return `Securities class actions require rapid custodian collection and large-scale document review. ${counsel} typically selects eDiscovery vendor within 30-60 days. Reach out now.`;
  } else if (nos.includes("830") || nos.includes("patent")) {
    return `Patent cases require technical document review and prior art searches. ${counsel} needs specialized eDiscovery support. Source code review may be required.`;
  } else if (nos.includes("820") || nos.includes("copyright")) {
    return `Copyright litigation requires content analysis and large-scale document collection. ${counsel} will need eDiscovery support for discovery phase.`;
  } else if (nos.includes("470") || nos.includes("rico")) {
    return `RICO cases involve complex multi-party document review across long time periods. Very high document volume expected. ${counsel} should be contacted immediately.`;
  } else if (nos.includes("480") || nos.includes("consumer")) {
    return `Consumer protection class actions require structured data analysis alongside document review. ${counsel} needs eDiscovery support.`;
  } else {
    return `Active federal litigation creates immediate document review and eDiscovery needs. Contact ${counsel} to position Consilio as preferred vendor.`;
  }
}

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
  // Determine if company is plaintiff or defendant from case name
  const caseName = searchResult.caseName || "";
  const vIndex = caseName.toLowerCase().indexOf(" v. ");
  const companyFirst = companyName.toLowerCase().split(" ")[0];

  let companyIsDefendant = true; // assume defendant by default
  if (vIndex > -1) {
    const afterV = caseName.slice(vIndex + 4).toLowerCase();
    const beforeV = caseName.slice(0, vIndex).toLowerCase();
    companyIsDefendant = afterV.includes(companyFirst); // company after "v." = defendant
  }

  const counsel = extractDefenseCounsel(
    searchResult.attorney,
    searchResult.firm,
    searchResult.party,
    companyName,
    companyIsDefendant
  );

  const nosDesc = getNOSDescription(searchResult.suitNature);
  const isHigh = isHighValueCase(searchResult.suitNature);

  const hasDefense = !!(counsel?.primary_firm);
  const counselNote = !hasDefense && counsel?.plaintiff_firms?.length
    ? `Plaintiff counsel identified (${counsel.plaintiff_firms[0]}) — defense counsel not yet confirmed in court records`
    : (!hasDefense ? "Defense counsel not yet confirmed in court records" : null);

  return {
    case_name: searchResult.caseName,
    case_number: searchResult.docketNumber,
    court: searchResult.court_id || searchResult.court,
    type: nosDesc || searchResult.cause || searchResult.caseName,
    period: (searchResult.dateFiled || "").slice(0, 7) + " to present",
    summary: `${searchResult.caseName} — ${searchResult.cause || nosDesc || "Federal case"} — Filed ${searchResult.dateFiled || "recently"} in ${(searchResult.court_id || "").toUpperCase()}`,
    status: "Pending",
    outside_counsel_firm: hasDefense ? counsel.primary_firm : null,
    all_counsel_firms: counsel?.firms || [],
    unclassified_counsel: counsel?.unclassified_firms || [],
    lead_partners: hasDefense ? (counsel?.attorneys || []) : [],
    plaintiff_counsel: counsel?.plaintiff_firms || [],
    counsel_verified: hasDefense,
    counsel_role: counsel?.counsel_role || "unknown",
    counsel_note: counselNote,
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
        // Skip cases with no meaningful identifiers
        if (!searchCase.caseName || !searchCase.docketNumber) continue;
        if (searchCase.caseName === "Unknown" || searchCase.docketNumber === "Unknown") continue;

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
        // Generate triggers from high-value CourtListener cases
        const highValueCases = (data.litigation || []).filter(l =>
          l.courtlistener_verified && l.is_high_value
        );

        if (highValueCases.length > 0) {
          const { immediate, strategic } = generateTriggersFromCases(highValueCases, account.name);

          // Merge with existing triggers — CourtListener triggers take priority
          const existingImmediate = (data.immediate_triggers || []).filter(t =>
            t.source !== "CourtListener/PACER"
          );
          const existingStrategic = (data.strategic_triggers || []).filter(t =>
            t.source !== "CourtListener/PACER"
          );

          data.immediate_triggers = [...immediate, ...existingImmediate];
          data.strategic_triggers = [...strategic, ...existingStrategic];

          // Also update flat sales_triggers for backwards compat
          const courtTriggers = immediate.map(t =>
            `IMMEDIATE [${t.urgency}] [${t.date}] ${t.trigger} — ${t.sales_implication}`
          );
          const existingFlat = (data.sales_triggers || []).filter(t =>
            !t.includes("CourtListener") && !t.includes("PACER")
          );
          data.sales_triggers = [...courtTriggers, ...existingFlat];

          logger.info(`  Generated ${immediate.length} immediate + ${strategic.length} strategic triggers from court data`);
        }

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
