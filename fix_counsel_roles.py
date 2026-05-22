import os

home = os.path.expanduser("~")
base = os.path.join(home, "legal-tracker")

with open(os.path.join(base, "src", "jobs", "courtListenerMonitor.js"), 'r') as f:
    content = f.read()

# ── Replace extractDefenseCounsel ──────────────────────────
old_fn = '''// Determine which attorneys represent the defendant (our account)
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
}'''

new_fn = '''// Known plaintiff-side litigation firms — they represent plaintiffs not corporate defendants
const PLAINTIFF_FIRMS = [
  "lieff cabraser", "milberg", "hagens berman", "girard sharp",
  "susman godfrey", "bernstein litowitz", "labaton", "keller rohrback",
  "scott+scott", "cohen milstein", "robbins geller", "wolf popper",
  "pomerantz", "kaplan fox", "glancy prongay", "levi & korsinsky",
  "bleichmar fonti", "grant & eisenhofer", "simmons hanly", "motley rice",
  "weitz & luxenberg", "seeger weiss", "levin papantonio", "morgan & morgan",
  "consumer attorneys", "laffey leitner", "beasley allen", "rosen law",
  "karpf karpf", "the rosen law", "chimicles", "faruqi", "bronstein",
  "wolf haldenstein", "saxena white", "bottini & bottini",
];

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
function extractDefenseCounsel(attorneys, firms, parties, companyName) {
  const partyNames = new Set((parties || []).map(p => p.toLowerCase().trim()));

  const validFirms = (firms || []).filter(f => isValidFirm(f, partyNames));
  const validAttorneys = (attorneys || []).filter(a => isValidAttorney(a, partyNames));

  // Separate plaintiff firms from defense firms
  const defenseFirms = validFirms.filter(f => !isPlaintiffFirm(f));
  const plaintiffFirms = validFirms.filter(f => isPlaintiffFirm(f));

  const primaryFirm = defenseFirms[0] || null;

  return {
    firms: defenseFirms.slice(0, 3),
    attorneys: primaryFirm ? validAttorneys.slice(0, 4) : [],
    primary_firm: primaryFirm,
    plaintiff_firms: plaintiffFirms.slice(0, 2),
    counsel_role: primaryFirm ? "defense" : (plaintiffFirms.length ? "plaintiff_only" : "unknown"),
  };
}'''

if old_fn in content:
    content = content.replace(old_fn, new_fn)
    print("Done — extractDefenseCounsel rewritten with plaintiff/defense separation")
else:
    print("WARNING — extractDefenseCounsel pattern not found")

# ── Update buildLitItem to store counsel roles ─────────────
old_build = '''  return {
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
  };'''

new_build = '''  const hasDefense = !!(counsel?.primary_firm);
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
  };'''

if old_build in content:
    content = content.replace(old_build, new_build)
    print("Done — buildLitItem stores plaintiff/defense separately")
else:
    print("WARNING — buildLitItem pattern not found")

with open(os.path.join(base, "src", "jobs", "courtListenerMonitor.js"), 'w') as f:
    f.write(content)

# ── Update dashboard to show counsel roles clearly ─────────
with open(os.path.join(base, "src", "dashboard.html"), 'r') as f:
    dash = f.read()

old_active = '''        var aPartners=(l.lead_partners||[]).filter(function(p){return p&&p.length>3&&p.length<60&&!p.toLowerCase().includes('e-filing')&&!p.match(/^\\d/);});
        if(aPartners.length)h+=' &mdash; '+aPartners.slice(0,3).join(', ');'''

new_active = '''        var aPartners=(l.lead_partners||[]).filter(function(p){
          return p&&p.length>4&&p.length<60&&!p.toLowerCase().includes('e-filing')&&
          !p.toLowerCase().includes('currently')&&!p.match(/^\\d/)&&p.split(' ').length>=2;
        });
        if(aPartners.length)h+=' &mdash; '+aPartners.slice(0,3).join(', ');
        if(l.plaintiff_counsel&&l.plaintiff_counsel.length){
          h+='<div style="font-size:11px;color:var(--g4);margin-top:2px">Plaintiff counsel: '+l.plaintiff_counsel.join(', ')+'</div>';
        }
        if(l.counsel_note){
          h+='<div style="font-size:11px;color:var(--amber);margin-top:2px">&#9888; '+l.counsel_note+'</div>';
        }'''

if old_active in dash:
    dash = dash.replace(old_active, new_active)
    print("Done — dashboard shows plaintiff counsel and counsel notes")
else:
    print("WARNING — dashboard active counsel pattern not found")

with open(os.path.join(base, "src", "dashboard.html"), 'w') as f:
    f.write(dash)

print("")
print("="*50)
print("PLAINTIFF/DEFENSE COUNSEL FIX COMPLETE")
print("="*50)
print("")
print("Changes:")
print("  - Known plaintiff firms list (Lieff Cabraser, Milberg, etc)")
print("  - Defense firms shown as Outside Counsel")
print("  - Plaintiff firms shown separately labeled correctly")
print("  - Warning shown when only plaintiff counsel found")
print("  - Pro se litigants filtered out")
print("")
print("Test: npm run court:account microsoft")
print("Bird v. Microsoft: Lieff Cabraser → Plaintiff counsel label")
print("Bryant v. Microsoft: Dechert LLP → Outside counsel (defense)")
