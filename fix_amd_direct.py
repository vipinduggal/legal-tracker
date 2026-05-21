import os, json
from datetime import datetime

home = os.path.expanduser("~")
db_path = os.path.join(home, "legal-tracker", "data", "db.json")

with open(db_path, 'r') as f:
    db = json.load(f)

amd = db["research"]["amd"]

# ── Apply triggers directly from verified Perplexity + Claude output ──
amd["immediate_triggers"] = [
    {
        "trigger": "Adeia Inc. v. AMD — 10 patent infringement claims filed in W.D. Texas covering hybrid bonding technology behind AMD's 3D V-Cache and advanced process node technology",
        "date": "2026 (recent filing)",
        "sales_implication": "High-volume document review needed for patent prosecution history, technical specifications, and prior art across 17 patents. Discovery requires specialized technical reviewers with semiconductor expertise.",
        "urgency": "High"
    },
    {
        "trigger": "Network System Technologies v. AMD and Xilinx — patent case filed in W.D. Texas, case no. 1:2025cv01648",
        "date": "October 14, 2025",
        "sales_implication": "Cross-company eDiscovery needed across AMD and acquired Xilinx entities. Post-merger document collection complexity.",
        "urgency": "High"
    },
    {
        "trigger": "Empire Technology Development v. AMD — patent case filed in District of Delaware, case no. 1:2025cv01049",
        "date": "August 21, 2025",
        "sales_implication": "Delaware patent venue moves quickly. Need for expedited document review, expert coordination, and claim construction support.",
        "urgency": "High"
    },
    {
        "trigger": "AMD/HP defective CPU class action — summary judgment motions denied October 29-30, 2025, case advancing to discovery/trial",
        "date": "October 29-30, 2025",
        "sales_implication": "Massive consumer class action advancing to discovery. Will require document review of technical specs, marketing materials, internal communications about fTPM defects across Ryzen/Athlon product lines.",
        "urgency": "High"
    }
]

amd["strategic_triggers"] = [
    {
        "trigger": "ZT Systems acquisition integration completed 2025 — four active litigations across merged entities, legacy document systems to harmonize",
        "timeframe": "Past 12 months",
        "sales_implication": "Post-merger integration creates ongoing eDiscovery complexity. Need to harmonize document retention policies, integrate legacy legal hold systems, and ensure data mapping across combined entities.",
        "angle": "Post-M&A legal operations optimization — data rationalization, legacy system migration, unified information governance"
    },
    {
        "trigger": "Export control pressures and China business restrictions — $390M MI308 revenue disclosed, ongoing OFAC/BIS compliance requirements",
        "timeframe": "Ongoing 2025-2026",
        "sales_implication": "Export compliance creates heightened regulatory risk. Need for compliance-focused document review, FCPA risk assessment, and government investigation preparation.",
        "angle": "Regulatory compliance document review, government inquiry response preparation, ongoing monitoring for OFAC/BIS violations"
    },
    {
        "trigger": "Business model transformation to system-led AI infrastructure — major new contract types, supply chain partners, IP licensing arrangements",
        "timeframe": "2026 strategic shift",
        "sales_implication": "Major business model change creates new contract types and higher contract volumes. Legal team capacity unlikely to scale at same rate as business growth.",
        "angle": "Flexible legal talent for contract review surge, ALSP support for new business line legal intake"
    },
    {
        "trigger": "Aggressive AI roadmap with Financial Analyst Day projections of greater than 35% revenue CAGR — hyper-growth creating legal department strain",
        "timeframe": "2026 forward",
        "sales_implication": "Hyper-growth creates increased IP filings, more commercial contracts, higher M&A activity, regulatory scrutiny. Legal team capacity unlikely to scale at 35% CAGR.",
        "angle": "Flex legal talent for hypergrowth, contract lifecycle management support, legal department efficiency consulting"
    }
]

# Flat sales_triggers for backwards compatibility
amd["sales_triggers"] = [
    "IMMEDIATE [High] [2026] Adeia v. AMD — 10 patent claims on 3D V-Cache and process node tech — high-volume specialized document review needed",
    "IMMEDIATE [High] [October 14, 2025] Network System Technologies v. AMD & Xilinx — cross-company eDiscovery across merged entities",
    "IMMEDIATE [High] [August 21, 2025] Empire Technology v. AMD — Delaware patent case, fast-moving venue, expedited review needed",
    "IMMEDIATE [High] [October 29-30, 2025] AMD/HP defective CPU class action advancing to discovery — millions of Ryzen/Athlon documents to review",
    "STRATEGIC [Past 12 months] ZT Systems integration — harmonize document retention, legacy legal holds, unified governance across 4 active litigations",
    "STRATEGIC [Ongoing 2025-2026] China export controls — $390M MI308 disclosed, OFAC/BIS compliance document review and monitoring needed",
    "STRATEGIC [2026 strategic shift] Business model transformation to rack-scale AI — contract surge requires flex legal talent and ALSP support",
    "STRATEGIC [2026 forward] 35% revenue CAGR target — legal team cannot scale at same pace, outsourced review and flex talent critical"
]

amd["intelligence_quality"] = "High"
amd["intelligence_date"] = datetime.now().strftime("%B %d, %Y")
amd["live_intel_retrieved"] = datetime.now().isoformat()

# Also fix contacts — remove Ava Hahn duplicates, keep only CLO
seen_names = {}
clean_contacts = []
role_rank = {
    "CLO": 14, "GC": 13, "Deputy GC": 12, "Associate GC": 11,
    "Head of Litigation": 10, "Head of Legal Operations": 9,
    "Head of Employment": 8, "Head of IP": 7, "Head of Privacy": 6,
    "Head of Compliance": 5, "Head of Regulatory": 4, "Head of Corporate": 3,
    "CEO": 13, "CFO": 12, "COO": 11, "CISO": 10,
    "Litigator": 2, "Other Legal": 1
}

for c in amd.get("contacts", []):
    name_key = c.get("name", "").lower().strip()
    if not name_key:
        continue
    if name_key not in seen_names:
        seen_names[name_key] = c
    else:
        existing = seen_names[name_key]
        if role_rank.get(c.get("tag",""), 0) > role_rank.get(existing.get("tag",""), 0):
            seen_names[name_key] = c

amd["contacts"] = list(seen_names.values())

db["research"]["amd"] = amd

with open(db_path, 'w') as f:
    json.dump(db, f)

print("Done — AMD updated directly in database")
print("")
print("Contacts:", len(amd["contacts"]))
for c in amd["contacts"]:
    print(f"  {c['name']} | {c['tag']} | {c['confidence']}")
print("")
print("Immediate triggers:", len(amd["immediate_triggers"]))
for t in amd["immediate_triggers"]:
    print(f"  [{t['urgency']}] [{t['date']}] {t['trigger'][:80]}")
print("")
print("Strategic triggers:", len(amd["strategic_triggers"]))
for t in amd["strategic_triggers"]:
    print(f"  [{t['timeframe']}] {t['trigger'][:80]}")
print("")
print("Refresh http://localhost:3000 and check AMD Sales Triggers tab")
