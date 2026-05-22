import os

home = os.path.expanduser("~")
path = os.path.join(home, "legal-tracker", "src", "jobs", "litigationMonitor.js")

with open(path, 'r') as f:
    content = f.read()

# Fix 1: Tighten discovery phase detection
# Only trigger on signals that mean actual federal litigation discovery
# not regulatory investigations
old_signals = '''const PHASE_SIGNALS = {
  discovery: [
    "scheduling order", "rule 26", "26(f)", "discovery plan",
    "discovery cutoff", "fact discovery", "document production",
    "interrogatories", "deposition notice", "subpoena",
    "motion to compel", "protective order", "ESI protocol",
    "electronically stored information", "litigation hold",
  ],'''

new_signals = '''const PHASE_SIGNALS = {
  discovery: [
    "scheduling order", "rule 26", "26(f) conference", "discovery plan",
    "discovery cutoff", "fact discovery deadline",
    "interrogatories served", "deposition notice", "deposition scheduled",
    "motion to compel", "ESI protocol", "electronically stored information",
    "litigation hold notice", "document production deadline",
    "discovery period", "discovery phase",
  ],'''

if old_signals in content:
    content = content.replace(old_signals, new_signals)
    print("Done — discovery signals tightened")
else:
    print("WARNING — discovery signals not found")

# Fix 2: Only mark as discovery if it's actual federal/civil litigation
# Add a litigation type check before marking discovery
old_discovery_check = '''          if (counselInfo.is_in_discovery && !alreadyAlerted) {
            results.inDiscovery++;
            const alert = buildDiscoveryAlert(account, litItem, counselInfo);
            alerts.push(alert);
            await markNotified(account.id, itemKey + ":discovery_alert");
            accountAlerted = true;
            logger.info(`DISCOVERY ALERT: ${account.name} — ${litItem.type} — counsel: ${counselInfo.outside_counsel_firm || "Unknown"}`);
          }'''

new_discovery_check = '''          // Only alert on actual civil litigation discovery, not regulatory investigations
          const isRegulatoryOnly = (litItem.type || "").toLowerCase().match(
            /regulatory|investigation|ftc|sec inquiry|doj investigation|eu commission|congressional|agency action/
          );
          if (counselInfo.is_in_discovery && !alreadyAlerted && !isRegulatoryOnly) {
            results.inDiscovery++;
            const alert = buildDiscoveryAlert(account, litItem, counselInfo);
            alerts.push(alert);
            await markNotified(account.id, itemKey + ":discovery_alert");
            accountAlerted = true;
            logger.info(`DISCOVERY ALERT: ${account.name} — ${litItem.type} — counsel: ${counselInfo.outside_counsel_firm || "Unknown"}`);
          } else if (counselInfo.is_in_discovery && isRegulatoryOnly) {
            logger.info(`Skipping discovery alert for regulatory matter: ${account.name} — ${litItem.type}`);
          }'''

if old_discovery_check in content:
    content = content.replace(old_discovery_check, new_discovery_check)
    print("Done — regulatory matters excluded from discovery alerts")
else:
    print("WARNING — discovery check pattern not found")

# Fix 3: Fix the outside counsel display
# The problem is the parser grabs sentence fragments
# Add stricter validation to the firm name extraction
old_firm_label = '''  // Extract firm name — structured label first
  const firmLabelMatch = clean.match(/(?:Firm|Outside Counsel|Counsel for [^:]+):\\s*([A-Z][^\\n,]{3,50}(?:LLP|LLC|PC|PLLC|LPA)?)/i);
  if (firmLabelMatch) {
    result.outside_counsel_firm = cleanMarkdown(firmLabelMatch[1]).trim();
  } else {'''

new_firm_label = '''  // Extract firm name — must be a real law firm name
  // Valid: "Wilson Sonsini LLP", "Orrick Herrington & Sutcliffe LLP"
  // Invalid: "not confirmed from available sources", "Microsoft's January 2024"
  const firmLabelMatch = clean.match(/(?:Firm|Outside Counsel|Defense Counsel|Represented by):\\s*([A-Z][^\\n]{3,60}(?:LLP|LLC|PC|PLLC|LPA))/i);
  if (firmLabelMatch) {
    const candidate = cleanMarkdown(firmLabelMatch[1]).trim();
    // Validate it looks like a real firm name
    if (candidate.match(/LLP|LLC|PC|PLLC/) && candidate.length < 60 && !candidate.includes("not ") && !candidate.includes("unavailable")) {
      result.outside_counsel_firm = candidate;
    }
  } else {'''

if old_firm_label in content:
    content = content.replace(old_firm_label, new_firm_label)
    print("Done — firm name validation strengthened")
else:
    print("WARNING — firm label pattern not found")

# Fix 4: Fix the key dates — filter out today's date
old_dates = '''  // Extract dates — full month names only
  const datePattern = /(?:January|February|March|April|May|June|July|August|September|October|November|December)\\s+\\d{1,2},?\\s+202[5-9]/g;
  const dates = clean.match(datePattern);
  if (dates) result.key_dates = [...new Set(dates)].slice(0, 3);'''

new_dates = '''  // Extract future dates only — filter out today and past dates
  const datePattern = /(?:January|February|March|April|May|June|July|August|September|October|November|December)\\s+\\d{1,2},?\\s+202[5-9]/g;
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
    .slice(0, 3);'''

if old_dates in content:
    content = content.replace(old_dates, new_dates)
    print("Done — today's date filtered from key dates")
else:
    print("WARNING — dates pattern not found")

# Fix 5: Update the Consilio opportunity to be case-type specific
old_opportunity = '''    opportunities.push("Active litigation in discovery phase creates immediate need for document review, data collection, and processing support.");'''

new_opportunity = '''    const caseTypeLower = (caseType || "").toLowerCase();
    if (caseTypeLower.includes("antitrust") || caseTypeLower.includes("competition")) {
      opportunities.push("Antitrust litigation typically involves millions of documents across communications, contracts, and financial records. Early engagement with outside counsel on eDiscovery strategy is critical.");
    } else if (caseTypeLower.includes("cyber") || caseTypeLower.includes("breach") || caseTypeLower.includes("privacy")) {
      opportunities.push("Cybersecurity and privacy matters require forensic data collection, log analysis, and technical document review. Specialized eDiscovery expertise in security incidents is needed.");
    } else if (caseTypeLower.includes("securities") || caseTypeLower.includes("class action")) {
      opportunities.push("Securities class actions require rapid collection from multiple custodians and complex financial data analysis alongside document review.");
    } else {
      opportunities.push("Active litigation in discovery phase creates immediate need for document review, data collection, and processing support.");
    }'''

if old_opportunity in content:
    content = content.replace(old_opportunity, new_opportunity)
    print("Done — opportunity text is now case-type specific")
else:
    print("WARNING — opportunity pattern not found")

with open(path, 'w') as f:
    f.write(content)

print("")
print("="*50)
print("LITIGATION QUALITY FIXES COMPLETE")
print("="*50)
print("")
print("Changes:")
print("  1. Discovery signals tightened — won't fire on regulatory matters")
print("  2. Regulatory investigations excluded from discovery alerts")
print("  3. Firm name validation — rejects sentence fragments")
print("  4. Key dates — today's date filtered out")
print("  5. Consilio opportunity — case-type specific messaging")
print("")
print("Clear Microsoft cache and test:")
print('  node << \'EOF\'')
print('  import { initDb, getResearch, setResearch } from \'./src/db.js\';')
print('  await initDb();')
print('  const d = await getResearch(\'microsoft\');')
print('  if(d && d.litigation) { d.litigation.forEach(l => { delete l.last_enriched; delete l.case_phase; delete l.outside_counsel_firm; delete l.lead_partners; }); await setResearch(\'microsoft\', d); console.log(\'Cleared\'); }')
print('  EOF')
print("")
print("Then: npm run litigation:monitor 2>&1 | grep -A 15 'Microsoft'")
