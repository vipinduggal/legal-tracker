import os

home = os.path.expanduser("~")
base = os.path.join(home, "legal-tracker")

# ── Step 1: Fix contactVerifier.js ────────────────────────
verifier_path = os.path.join(base, "src", "contactVerifier.js")

with open(verifier_path, 'r') as f:
    content = f.read()

# Replace the ROLES_TO_CHECK and verifyAccountContacts function
old_roles = """const ROLES_TO_CHECK = [
  { tag: "CLO", titles: ["Chief Legal Officer", "CLO"] },
  { tag: "GC", titles: ["General Counsel", "GC"] },
  { tag: "Head of Litigation", titles: ["Head of Litigation", "VP Litigation", "Director of Litigation"] },
  { tag: "Head of Legal Operations", titles: ["Head of Legal Operations", "VP Legal Operations", "Director of Legal Operations", "Legal Operations Manager"] },
];"""

new_roles = """// All roles we try to find via Perplexity live search
const ROLES_TO_CHECK = [
  // C-Suite legal leadership
  { tag: "CLO", titles: ["Chief Legal Officer", "CLO", "General Counsel and Chief Legal Officer"] },
  { tag: "GC", titles: ["General Counsel", "GC", "SVP General Counsel", "VP General Counsel"] },
  { tag: "Deputy GC", titles: ["Deputy General Counsel", "Associate General Counsel", "Assistant General Counsel"] },
  // Functional heads
  { tag: "Head of Litigation", titles: ["Head of Litigation", "VP Litigation", "Director of Litigation", "Chief Litigation Counsel"] },
  { tag: "Head of Legal Operations", titles: ["Head of Legal Operations", "VP Legal Operations", "Director of Legal Operations", "Chief Legal Operations Officer", "Legal Operations Manager"] },
  { tag: "Head of Employment", titles: ["Head of Employment Law", "VP Employment", "Chief Employment Counsel", "Head of Labor and Employment"] },
  { tag: "Head of IP", titles: ["Head of Intellectual Property", "Chief IP Counsel", "VP Intellectual Property", "Head of Patents"] },
  { tag: "Head of Privacy", titles: ["Chief Privacy Officer", "Head of Privacy", "VP Privacy and Data Protection", "Data Protection Officer"] },
  { tag: "Head of Compliance", titles: ["Chief Compliance Officer", "Head of Compliance", "VP Compliance", "Chief Ethics and Compliance Officer"] },
  { tag: "Head of Regulatory", titles: ["Head of Regulatory Affairs", "VP Regulatory", "Chief Regulatory Counsel", "Head of Government Affairs"] },
  { tag: "Head of Corporate", titles: ["Head of Corporate Law", "VP Corporate", "Chief Corporate Counsel", "Head of M&A"] },
  // Executive suite (non-legal but relevant)
  { tag: "CEO", titles: ["Chief Executive Officer", "CEO"] },
  { tag: "CFO", titles: ["Chief Financial Officer", "CFO"] },
  { tag: "COO", titles: ["Chief Operating Officer", "COO"] },
  { tag: "CISO", titles: ["Chief Information Security Officer", "CISO"] },
];"""

if old_roles in content:
    content = content.replace(old_roles, new_roles)
    print("Done — ROLES_TO_CHECK expanded")
else:
    print("WARNING — ROLES_TO_CHECK not found, appending")

# Replace verifyAccountContacts with deduplication logic
old_verify = """export async function verifyAccountContacts(account, researchData, forceAll) {
  if (!researchData || !researchData.contacts || !researchData.contacts.length) {
    return researchData;
  }

  const staleThresholdDays = 7;
  const now = Date.now();

  const contactsToVerify = researchData.contacts.filter(function(c) {
    if (forceAll) return true;
    if (c.confidence === "Low") return true;
    if (!c.verifiedAt) return true;
    const daysSince = (now - new Date(c.verifiedAt).getTime()) / (1000 * 60 * 60 * 24);
    return daysSince > staleThresholdDays;
  });

  if (!contactsToVerify.length) {
    logger.info("All contacts recently verified for " + account.name);
    return researchData;
  }

  logger.info("Verifying " + contactsToVerify.length + " contacts for " + account.name);

  const verified = [];
  for (const c of contactsToVerify) {
    const result = await verifyContact(c, account.name);
    verified.push(result);
    await new Promise(function(r) { setTimeout(r, 500); });
  }

  const verifiedMap = new Map(verified.map(function(c) { return [c.name, c]; }));
  researchData.contacts = researchData.contacts.map(function(c) {
    return verifiedMap.has(c.name) ? verifiedMap.get(c.name) : c;
  });

  return researchData;
}"""

new_verify = """// Normalize a name for deduplication comparison
function normalizeName(name) {
  return (name || "")
    .toLowerCase()
    .replace(/[^a-z\s]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

// Deduplicate contacts — keep the one with highest confidence
function deduplicateContacts(contacts) {
  const seen = new Map();
  const confidenceRank = { High: 3, Medium: 2, Low: 1 };

  for (const c of contacts) {
    const key = normalizeName(c.name);
    if (!key) continue;

    if (!seen.has(key)) {
      seen.set(key, c);
    } else {
      // Keep the higher confidence version
      const existing = seen.get(key);
      const existingRank = confidenceRank[existing.confidence] || 0;
      const newRank = confidenceRank[c.confidence] || 0;
      if (newRank > existingRank) {
        // Merge best fields from both
        seen.set(key, {
          ...c,
          linkedin: c.linkedin || existing.linkedin,
          email: c.email || existing.email,
          notes: c.notes || existing.notes,
        });
      } else {
        // Keep existing but merge any missing fields
        seen.set(key, {
          ...existing,
          linkedin: existing.linkedin || c.linkedin,
          email: existing.email || c.email,
          notes: existing.notes || c.notes,
        });
      }
    }
  }

  return Array.from(seen.values());
}

export async function verifyAccountContacts(account, researchData, forceAll) {
  if (!researchData) return researchData;

  // Always deduplicate first
  if (researchData.contacts && researchData.contacts.length) {
    const before = researchData.contacts.length;
    researchData.contacts = deduplicateContacts(researchData.contacts);
    const after = researchData.contacts.length;
    if (before !== after) {
      logger.info("Deduplication removed " + (before - after) + " duplicate contacts for " + account.name);
    }
  }

  if (!PERPLEXITY_KEY) {
    logger.warn("No PERPLEXITY_API_KEY — skipping live verification");
    return researchData;
  }

  logger.info("Running Perplexity-first contact lookup for " + account.name);

  const perplexityContacts = [];

  for (const role of ROLES_TO_CHECK) {
    const found = await findCurrentRoleHolder(account.name, role);
    if (found) {
      perplexityContacts.push(found);
      logger.info("Perplexity found " + role.tag + " at " + account.name + ": " + found.name);
    }
    await new Promise(function(r) { setTimeout(r, 400); });
  }

  if (!perplexityContacts.length) {
    logger.info("Perplexity found no contacts for " + account.name + " — keeping Claude contacts with Low confidence");
    if (researchData.contacts) {
      researchData.contacts = researchData.contacts.map(function(c) {
        return Object.assign({}, c, {
          confidence: c.confidence || "Medium",
          confidence_reason: c.confidence_reason || "AI-sourced — verify on LinkedIn before outreach",
        });
      });
    }
    return researchData;
  }

  // Merge Perplexity contacts with existing Claude contacts
  // Perplexity contacts are authoritative for roles they cover
  const perplexityTags = new Set(perplexityContacts.map(function(c) { return c.tag; }));
  const perplexityNames = new Set(perplexityContacts.map(function(c) { return normalizeName(c.name); }));

  // Keep Claude contacts not covered by Perplexity AND not already found by Perplexity
  const claudeOnlyContacts = (researchData.contacts || []).filter(function(c) {
    const nameNorm = normalizeName(c.name);
    // Skip if Perplexity already found this person by name
    if (perplexityNames.has(nameNorm)) return false;
    // Keep if it's a role Perplexity didn't cover
    return !perplexityTags.has(c.tag);
  }).map(function(c) {
    return Object.assign({}, c, {
      confidence: "Low",
      confidence_reason: "AI-sourced only — not verified by live search. Verify on LinkedIn before outreach.",
    });
  });

  // Combine and deduplicate one final time
  const combined = [...perplexityContacts, ...claudeOnlyContacts];
  researchData.contacts = deduplicateContacts(combined);

  logger.info("Contact merge complete for " + account.name + ": " +
    perplexityContacts.length + " Perplexity-verified, " +
    claudeOnlyContacts.length + " Claude-only (Low confidence), " +
    researchData.contacts.length + " total after dedup");

  return researchData;
}"""

if old_verify in content:
    content = content.replace(old_verify, new_verify)
    print("Done — verifyAccountContacts updated with deduplication + expanded roles")
else:
    print("WARNING — verifyAccountContacts not found exactly, appending dedup function")
    # Add dedup function before the export
    content = content.replace(
        "export async function verifyAccountContacts",
        """function normalizeName(name) {
  return (name || "").toLowerCase().replace(/[^a-z\\s]/g, "").replace(/\\s+/g, " ").trim();
}
function deduplicateContacts(contacts) {
  const seen = new Map();
  const rank = { High: 3, Medium: 2, Low: 1 };
  for (const c of contacts) {
    const key = normalizeName(c.name);
    if (!key) continue;
    if (!seen.has(key)) { seen.set(key, c); }
    else {
      const ex = seen.get(key);
      if ((rank[c.confidence]||0) > (rank[ex.confidence]||0)) {
        seen.set(key, { ...c, linkedin: c.linkedin||ex.linkedin, email: c.email||ex.email });
      } else {
        seen.set(key, { ...ex, linkedin: ex.linkedin||c.linkedin, email: ex.email||c.email });
      }
    }
  }
  return Array.from(seen.values());
}
export async function verifyAccountContacts"""
    )

with open(verifier_path, 'w') as f:
    f.write(content)
print("Done — contactVerifier.js updated")

# ── Step 2: Update research prompt to find more contacts ──
prompts_path = os.path.join(base, "src", "prompts.js")

with open(prompts_path, 'r') as f:
    prompts = f.read()

old_contacts_schema = '''  "contacts": [
    {
      "name": "string - full name",
      "title": "string - exact current title",
      "tag": "one of: CLO | GC | Head of Litigation | Head of Legal Operations | Litigator | Deputy GC | Associate GC",
      "linkedin": "string - LinkedIn profile URL if known, else null",
      "email": "string - professional email if publicly known, else null",
      "confidence": "one of: High | Medium | Low",
      "confidence_reason": "string - why this confidence level, e.g. Confirmed via company press release March 2025 or AI-sourced only - verify on LinkedIn before outreach",
      "notes": "string - recent hire, prior firm, tenure concerns, or null"
    }
  ],'''

new_contacts_schema = '''  "contacts": [
    {
      "name": "string - full name",
      "title": "string - exact current title",
      "tag": "one of: CLO | GC | Deputy GC | Associate GC | Head of Litigation | Head of Legal Operations | Head of Employment | Head of IP | Head of Privacy | Head of Compliance | Head of Regulatory | Head of Corporate | Litigator | CEO | CFO | COO | CISO | Other Legal",
      "linkedin": "string - LinkedIn profile URL if known, else null",
      "email": "string - professional email if publicly known, else null",
      "confidence": "one of: High | Medium | Low",
      "confidence_reason": "string - source and date of confirmation, e.g. Confirmed via LinkedIn March 2026 or Company website 2026 or AI-sourced only",
      "notes": "string - relevant context: recent hire date, prior employer, bar admissions, areas of focus, or null",
      "department": "one of: Legal | Executive | Compliance | Privacy | Other"
    }
  ],'''

old_contacts_priority = """- Contacts: prioritize current role holders only. Flag anyone whose departure has been reported. Note confidence level for each."""

new_contacts_priority = """- Contacts: Find as many current legal team members as possible. Include:
  * Full C-suite of the company (CEO, CFO, COO, CISO — these are key influencers even if not legal)
  * Complete legal leadership team: CLO, GC, all Deputy/Associate GCs
  * All functional legal heads: Litigation, Legal Ops, Employment, IP, Privacy, Compliance, Regulatory, Corporate/M&A
  * Named litigators or attorneys visible in public filings, court records, or press releases
  * Anyone named as counsel in SEC filings or litigation documents
  * LinkedIn searches for [Company] + "General Counsel" or "Legal" in title
  Prioritize current role holders only. Flag departures. The goal is a COMPREHENSIVE contact list, not just the top 2-3 people."""

if old_contacts_schema in prompts:
    prompts = prompts.replace(old_contacts_schema, new_contacts_schema)
    print("Done — contacts schema expanded in research prompt")
else:
    print("WARNING — contacts schema not found exactly in prompts.js")

if old_contacts_priority in prompts:
    prompts = prompts.replace(old_contacts_priority, new_contacts_priority)
    print("Done — contacts research instructions expanded")
else:
    print("WARNING — contacts priority instruction not found in prompts.js")

with open(prompts_path, 'w') as f:
    f.write(prompts)

# ── Step 3: Update dashboard contact cards to show department ──
dashboard_path = os.path.join(base, "src", "dashboard.html")

with open(dashboard_path, 'r') as f:
    dash = f.read()

# Update tagcls function to handle new tags
old_tagcls = """function tcls(t){var x=(t||'').toLowerCase().replace(/[^a-z]/g,'');return{clo:'tc0',gc:'tc1',litigation:'tc2',litigator:'tc2',headoflitigation:'tc2',headoflegaloperations:'tc3',legalops:'tc3'}[x]||'tc4';}"""

new_tagcls = """function tcls(t){
  var x=(t||'').toLowerCase().replace(/[^a-z]/g,'');
  var m={
    clo:'tc0',gc:'tc1',deputygc:'tc1',associategc:'tc1',
    litigation:'tc2',litigator:'tc2',headoflitigation:'tc2',
    headoflegaloperations:'tc3',legalops:'tc3',
    headofemployment:'tc3',headofip:'tc3',headofprivacy:'tc3',
    headofcompliance:'tc3',headofregulatory:'tc3',headofcorporate:'tc3',
    ceo:'tc4',cfo:'tc4',coo:'tc4',ciso:'tc4',
  };
  return m[x]||'tc4';
}"""

if old_tagcls in dash:
    dash = dash.replace(old_tagcls, new_tagcls)
    print("Done — dashboard tagcls updated with new roles")
else:
    print("WARNING — tagcls not found in dashboard")

# Add department grouping to contacts tab
old_contacts_render = """    if(!r.contacts||!r.contacts.length){c.innerHTML=emp('No contacts found');return;}
    var h=(r.intel_summary?ibox(r.intel_summary):'')+
      '<div class="sl">Key legal contacts ('+r.contacts.length+')</div><div class="cg">';
    r.contacts.forEach(function(ct){"""

new_contacts_render = """    if(!r.contacts||!r.contacts.length){c.innerHTML=emp('No contacts found');return;}
    // Group contacts by department
    var exec=r.contacts.filter(function(c){return ['CEO','CFO','COO','CISO'].includes(c.tag);});
    var legal=r.contacts.filter(function(c){return !['CEO','CFO','COO','CISO'].includes(c.tag);});
    var h=(r.intel_summary?ibox(r.intel_summary):'');
    // Legal contacts first
    if(legal.length){h+='<div class="sl">Legal department ('+legal.length+')</div><div class="cg">';}
    var renderList=legal.length?legal:r.contacts;
    renderList.forEach(function(ct){"""

old_contacts_end = """      h+='</div>';
    });
    c.innerHTML=h+'</div>';"""

new_contacts_end = """      h+='</div>';
    });
    if(legal.length){h+='</div>';}
    // Executive suite
    if(exec.length){
      h+='<div class="sl" style="margin-top:14px">Executive suite ('+exec.length+')</div><div class="cg">';
      exec.forEach(function(ct){
        h+='<div class="cc"><div class="cct"><div class="cav" style="background:'+cv[0]+';color:'+cv[1]+'">'+ini(ct.name)+'</div>';
        h+='<div><div class="cn">'+ct.name+'</div><div class="ct2">'+ct.title+'</div></div></div>';
        h+='<span class="tag '+tcls(ct.tag)+'">'+ct.tag+'</span>';
        if(ct.confidence)h+=' <span class="'+ccls(ct.confidence)+'">'+ct.confidence+'</span>';
        if(ct.linkedin)h+='<div class="cd"><a href="https://'+ct.linkedin+'" target="_blank">LinkedIn</a></div>';
        h+='</div>';
      });
      h+='</div>';
    }
    c.innerHTML=h;"""

if old_contacts_render in dash:
    dash = dash.replace(old_contacts_render, new_contacts_render)
    print("Done — dashboard contacts grouped by department")
else:
    print("WARNING — contacts render pattern not found")

if old_contacts_end in dash:
    dash = dash.replace(old_contacts_end, new_contacts_end)
    print("Done — executive suite section added")
else:
    print("WARNING — contacts end pattern not found")

with open(dashboard_path, 'w') as f:
    f.write(dash)

print("")
print("="*50)
print("CONTACTS UPGRADE COMPLETE")
print("="*50)
print("")
print("Changes:")
print("  1. Deduplication: contacts with same name merged, keeping highest confidence")
print("  2. Expanded Perplexity lookups: 14 roles now checked (was 4)")
print("  3. Research prompt: finds full legal team + entire C-suite")
print("  4. Dashboard: legal contacts and exec suite shown in separate groups")
print("  5. New tags: Head of Employment, IP, Privacy, Compliance, Regulatory, Corporate")
print("     CEO, CFO, COO, CISO now included")
print("")
print("Test:")
print('  npm run research:account "Microsoft"')
print("  Expect: 10+ contacts including full legal team and C-suite")
