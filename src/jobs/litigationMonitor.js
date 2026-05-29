// litigationMonitor.js
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
    "scheduling order", "rule 26", "26(f) conference", "discovery plan",
    "discovery cutoff", "fact discovery deadline",
    "interrogatories served", "deposition notice", "deposition scheduled",
    "motion to compel", "ESI protocol", "electronically stored information",
    "litigation hold notice", "document production deadline",
    "discovery period", "discovery phase",
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
    const query = `Today is ${today}. I need current information about active litigation involving ${account.name}.

Case type: ${litigationItem.type}
Case description: ${litigationItem.summary || "See case type"}

Please search for the CURRENT status of this case as of ${today} and answer:

1. OUTSIDE COUNSEL: Which specific law firm represents ${account.name} in this matter RIGHT NOW? Give the firm name AND the names of the lead partners or attorneys of record. Format as: "Firm: [name], Partners: [name1], [name2]"

2. CASE PHASE: Is this case currently in pre-discovery, discovery, post-discovery, or trial phase as of ${today}? What specific event indicates the current phase (e.g. scheduling order entered, depositions noticed, summary judgment filed)?

3. KEY DATES: List any upcoming or recent court dates — discovery cutoff, expert deadlines, summary judgment deadline, trial date. Include the actual dates.

4. CASE NUMBER AND COURT: What is the full case name, case number, and court?

5. CURRENT STATUS: What happened most recently in this case — any rulings, filings, or developments in the last 90 days?

Only include information you can confirm. If the case was resolved or settled, say so explicitly.`;

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

function cleanMarkdown(text) {
  // Remove markdown formatting that Perplexity sometimes adds
  return (text || "")
    .replace(/\*\*/g, "")
    .replace(/\*/g, "")
    .replace(/#+\s*/g, "")
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
    .replace(/^[-•]\s*/gm, "")
    .trim();
}

function parseCounselAnswer(answer, accountName, litigationItem) {
  const clean = cleanMarkdown(answer);
  const cleanLower = clean.toLowerCase();
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
    if (signals.some(s => cleanLower.includes(s))) {
      result.case_phase = phase;
      if (phase === "discovery") {
        result.is_in_discovery = true;
        result.discovery_signal = signals.find(s => cleanLower.includes(s));
      }
      break;
    }
  }

  // Extract firm name — must be a real law firm name
  // Valid: "Wilson Sonsini LLP", "Orrick Herrington & Sutcliffe LLP"
  // Invalid: "not confirmed from available sources", "Microsoft's January 2024"
  const firmLabelMatch = clean.match(/(?:Firm|Outside Counsel|Defense Counsel|Represented by):\s*([A-Z][^\n]{3,60}(?:LLP|LLC|PC|PLLC|LPA))/i);
  if (firmLabelMatch) {
    const candidate = cleanMarkdown(firmLabelMatch[1]).trim();
    // Validate it looks like a real firm name
    if (candidate.match(/LLP|LLC|PC|PLLC/) && candidate.length < 60 && !candidate.includes("not ") && !candidate.includes("unavailable")) {
      result.outside_counsel_firm = candidate;
    }
  } else {
    // Pattern match for law firm names
    const firmPatterns = [
      /([A-Z][a-z]+(?:,? [A-Z][a-z]+)* (?:LLP|LLC|PC|PLLC|LPA))/g,
      /([A-Z][a-z]+ (?:&|and) [A-Z][a-z]+(?: [A-Z][a-z]+)? LLP)/g,
    ];
    for (const pattern of firmPatterns) {
      const matches = clean.match(pattern);
      if (matches && matches.length > 0) {
        // Filter out garbage matches
        const valid = matches.filter(m =>
          m.length > 8 &&
          m.length < 60 &&
          !m.match(/^\d/) &&
          !m.toLowerCase().includes("scheduling") &&
          !m.toLowerCase().includes("november") &&
          !m.toLowerCase().includes("january")
        );
        if (valid.length) { result.outside_counsel_firm = valid[0]; break; }
      }
    }
  }

  // Extract named partners
  const partnersLabelMatch = clean.match(/Partners?:\s*([^\n]{5,100})/i);
  if (partnersLabelMatch) {
    const partnerText = cleanMarkdown(partnersLabelMatch[1]);
    result.lead_partners = partnerText
      .split(/,|;| and /)
      .map(p => p.trim())
      .filter(p =>
        p.length > 4 &&
        p.length < 40 &&
        /^[A-Z]/.test(p) &&
        !p.toLowerCase().includes("scheduling") &&
        !p.toLowerCase().includes("discovery") &&
        p.split(" ").length >= 2
      )
      .slice(0, 3);
  } else {
    // Look for "represented by [Name]" or "lead attorney [Name]"
    const repPatterns = [
      /represented by ([A-Z][a-z]+ [A-Z][a-z]+)/g,
      /lead (?:partner|attorney|counsel)[:\s]+([A-Z][a-z]+ [A-Z][a-z]+)/gi,
      /attorney of record[:\s]+([A-Z][a-z]+ [A-Z][a-z]+)/gi,
    ];
    for (const pattern of repPatterns) {
      const matches = [...clean.matchAll(pattern)];
      if (matches.length > 0) {
        result.lead_partners = matches.slice(0, 2).map(m => m[1].trim());
        break;
      }
    }
  }

  // Extract future dates only — filter out today and past dates
  const datePattern = /(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+202[5-9]/g;
  const today = new Date();
  const allDates = clean.match(datePattern) || [];
  result.key_dates = [...new Set(allDates)]
    .filter(d => {
      try {
        const dt = new Date(d);
        // Only include future dates that are at least 2 days from now
        return dt > new Date(today.getTime() + 2 * 24 * 60 * 60 * 1000);
      } catch(e) { return false; }
    })
    .slice(0, 3);

  // Extract case number
  const caseNumPattern = /(?:case\s+no\.?|civil\s+action\s+no\.?|docket)[:\s]+([0-9][0-9:\-cvCV]+)/i;
  const caseNumMatch = clean.match(caseNumPattern);
  if (caseNumMatch) result.case_number = caseNumMatch[1];

  // If we couldn't find a real firm name, mark as unverified
  if (!result.outside_counsel_firm ||
      result.outside_counsel_firm.length < 5 ||
      result.outside_counsel_firm.toLowerCase().includes("scheduling") ||
      result.outside_counsel_firm.toLowerCase().includes("searching") ||
      result.outside_counsel_firm.toLowerCase().includes("various") ||
      result.outside_counsel_firm.toLowerCase().includes("unknown")) {
    result.outside_counsel_firm = null;
    result.counsel_verified = false;
  } else {
    result.counsel_verified = true;
  }

  return result;
}

// Build the alert message for a discovery-phase case
function buildDiscoveryAlert(account, litigationItem, counselInfo) {
  const firm = counselInfo?.outside_counsel_firm || "Unknown firm";
  const phase = counselInfo?.case_phase || "Unknown phase";
  const dates = (counselInfo?.key_dates || []).join(", ") || "No dates confirmed";
  const volume = estimateVolume(litigationItem.type);

  // Three counsel buckets, classified by courtListenerMonitor's lists.
  // De-dup case-insensitively (data sometimes has "Dechert LLP" and "Dechert, LLP").
  const dedup = (arr) => {
    const seen = new Set();
    return (Array.isArray(arr) ? arr : []).filter(x => {
      if (!x) return false;
      const k = x.toLowerCase().replace(/[,.]/g, "").trim();
      if (seen.has(k)) return false;
      seen.add(k); return true;
    });
  };
  const defenseFirms = dedup(litigationItem.all_counsel_firms);
  const plaintiffFirms = dedup(litigationItem.plaintiff_counsel);
  const unclassifiedFirms = dedup(litigationItem.unclassified_counsel);
  // "counselKnown" now means: we have at least one *defense* firm identified.
  const counselKnown = defenseFirms.length > 0;
  // counselFirms kept for any old code path that reads it (back-compat).
  const counselFirms = defenseFirms;
  // Parties: shown as flat list. Filter the tracked client's own name out so the rest reads as "others involved".
  const allParties = Array.isArray(litigationItem.parties) ? litigationItem.parties : [];
  const acctLower = (account.name || "").toLowerCase();
  const otherParties = allParties.filter(p => p && !p.toLowerCase().includes(acctLower));

  return {
    account_name: account.name,
    case_name: litigationItem.case_name || null,
    case_type: litigationItem.type,
    case_phase: phase,
    is_in_discovery: counselInfo?.is_in_discovery || false,
    outside_counsel: firm,
    counsel_firms: counselFirms,
    defense_firms: defenseFirms,
    plaintiff_firms: plaintiffFirms,
    unclassified_firms: unclassifiedFirms,
    counsel_known: counselKnown,
    other_parties: otherParties,
    courtlistener_url: litigationItem.courtlistener_url || null,
    key_dates: counselInfo?.key_dates || [],
    estimated_doc_volume: volume,
    discovery_signal: counselInfo?.discovery_signal,
    case_number: counselInfo?.case_number || litigationItem.case_number || null,
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
    const caseTypeLower = (caseType || "").toLowerCase();
    if (caseTypeLower.includes("antitrust") || caseTypeLower.includes("competition")) {
      opportunities.push("Antitrust litigation typically involves millions of documents across communications, contracts, and financial records. Early engagement with outside counsel on eDiscovery strategy is critical.");
    } else if (caseTypeLower.includes("cyber") || caseTypeLower.includes("breach") || caseTypeLower.includes("privacy")) {
      opportunities.push("Cybersecurity and privacy matters require forensic data collection, log analysis, and technical document review. Specialized eDiscovery expertise in security incidents is needed.");
    } else if (caseTypeLower.includes("securities") || caseTypeLower.includes("class action")) {
      opportunities.push("Securities class actions require rapid collection from multiple custodians and complex financial data analysis alongside document review.");
    } else {
      opportunities.push("Active litigation in discovery phase creates immediate need for document review, data collection, and processing support.");
    }
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
        // Skip resolved/settled cases
        if (["Resolved", "Settled", "Dismissed"].includes(litItem.status)) continue;

        const itemKey = `lit:${litItem.type}:${litItem.period}`;
        const alreadyAlerted = hasBeenNotified(account.id, itemKey + ":discovery_alert");

        // Skip if already enriched in last 3 days (avoid redundant Perplexity calls)
        const lastEnriched = litItem.last_enriched ? new Date(litItem.last_enriched) : null;
        const daysSinceEnriched = lastEnriched ? (Date.now() - lastEnriched.getTime()) / (1000 * 60 * 60 * 24) : 999;
        if (daysSinceEnriched < 3 && litItem.case_phase && litItem.case_phase !== "Unknown") {
          logger.info(`Skipping ${account.name} ${litItem.type} — enriched ${Math.round(daysSinceEnriched)}d ago`);
          enrichedLitigation.push(litItem);
          continue;
        }

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
          // Only alert on actual civil litigation discovery, not regulatory investigations
          const isRegulatoryOnly = (litItem.type || "").toLowerCase().match(
            /regulatory|investigation|ftc|sec inquiry|doj investigation|eu commission|congressional|agency action/
          );
          if (counselInfo.is_in_discovery && !alreadyAlerted && !isRegulatoryOnly && litItem.courtlistener_id) {
            results.inDiscovery++;
            const alert = buildDiscoveryAlert(account, litItem, counselInfo);
            alerts.push(alert);
            await markNotified(account.id, itemKey + ":discovery_alert");
            accountAlerted = true;
            logger.info(`DISCOVERY ALERT: ${account.name} — ${litItem.type} — counsel: ${counselInfo.outside_counsel_firm || "Unknown"}`);
          } else if (counselInfo.is_in_discovery && isRegulatoryOnly) {
            logger.info(`Skipping discovery alert for regulatory matter: ${account.name} — ${litItem.type}`);
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
if (process.argv[1] && process.argv[1].endsWith("litigationMonitor.js")) {
  runLitigationMonitor()
    .then(({ results, alerts }) => {
      logger.info("Manual run complete", results);
      if (alerts.length) {
        console.log("\nDiscovery alerts:");
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
