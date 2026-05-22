import os

home = os.path.expanduser("~")
base = os.path.join(home, "legal-tracker")

# ── Step 1: Add trigger generation to courtListenerMonitor.js ──
cl_path = os.path.join(base, "src", "jobs", "courtListenerMonitor.js")

with open(cl_path, 'r') as f:
    content = f.read()

# Add trigger generation function after the HIGH_VALUE_NOS definition
old_function = '''function getNOSDescription(suitNature) {'''

new_function = '''// Generate immediate and strategic triggers from CourtListener cases
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

function getNOSDescription(suitNature) {'''

if old_function in content:
    content = content.replace(old_function, new_function)
    print("Done — trigger generation function added")
else:
    print("WARNING — getNOSDescription not found")

# Now add trigger saving after enrichment
old_save = '''      if (newCases > 0 || updatedCases > 0) {
        data.courtlistener_last_checked = new Date().toISOString();
        await setResearch(account.id, data);
        results.enriched++;
        logger.info(`  ${account.name}: ${newCases} new cases, ${updatedCases} updated`);
      }'''

new_save = '''      if (newCases > 0 || updatedCases > 0) {
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
      }'''

if old_save in content:
    content = content.replace(old_save, new_save)
    print("Done — triggers now generated from CourtListener cases")
else:
    print("WARNING — save pattern not found")

with open(cl_path, 'w') as f:
    f.write(content)

# ── Step 2: Update digest prompt to use CourtListener data ──
prompts_path = os.path.join(base, "src", "prompts.js")
with open(prompts_path, 'r') as f:
    prompts = f.read()

old_lit_summary = '''        `Active litigation: ${(d.litigation || []).filter(l => !["Resolved","Settled","Dismissed"].includes(l.status)).map(l => l.type + (l.is_new ? " [NEW]" : "")).join(", ") || "None"}`,'''

new_lit_summary = '''        `Active litigation (${(d.litigation || []).filter(l => !["Resolved","Settled","Dismissed"].includes(l.status)).length} cases): ${
          (d.litigation || [])
            .filter(l => !["Resolved","Settled","Dismissed"].includes(l.status))
            .slice(0, 5)
            .map(l => {
              const base = (l.case_name || l.type) + (l.case_number ? " (" + l.case_number + ")" : "");
              const counsel = l.outside_counsel_firm ? " — counsel: " + l.outside_counsel_firm : "";
              const partners = (l.lead_partners || []).slice(0,2).join(", ");
              const partnerStr = partners ? " (" + partners + ")" : "";
              const verified = l.courtlistener_verified ? " [COURT VERIFIED]" : "";
              return base + counsel + partnerStr + verified + (l.is_new ? " [NEW]" : "");
            }).join(" | ") || "None"
        }`,'''

if old_lit_summary in prompts:
    prompts = prompts.replace(old_lit_summary, new_lit_summary)
    with open(prompts_path, 'w') as f:
        f.write(prompts)
    print("Done — digest prompt updated with CourtListener case details")
else:
    print("WARNING — digest prompt litigation pattern not found")

print("")
print("="*60)
print("COURTLISTENER → TRIGGERS → DIGEST PIPELINE COMPLETE")
print("="*60)
print("")
print("What was built:")
print("  1. CourtListener cases automatically generate triggers:")
print("     - Antitrust/Securities → Critical urgency")
print("     - Patent/Copyright/RICO → High urgency")
print("     - Contract/Employment → Medium urgency")
print("  2. Triggers include case name, docket number, outside counsel")
print("  3. Sales implication is case-type specific")
print("  4. Weekly digest now includes verified case names and counsel")
print("  5. Multiple high-value cases → strategic MSA opportunity trigger")
print("")
print("Test:")
print("  npm run court:account microsoft")
print("  Then check Sales Triggers tab for Microsoft")
print("")
print("Generate updated digest:")
print("  npm run digest:weekly")
