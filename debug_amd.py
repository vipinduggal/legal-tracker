import os, json

home = os.path.expanduser("~")
db_path = os.path.join(home, "legal-tracker", "data", "db.json")

with open(db_path, 'r') as f:
    db = json.load(f)

amd = db.get("research", {}).get("amd", {})

print("=== CONTACTS ===")
contacts = amd.get("contacts", [])
print("Total:", len(contacts))
for c in contacts:
    print(f"  {c.get('name')} | {c.get('tag')} | {c.get('confidence')}")

print("")
print("=== TRIGGERS ===")
print("sales_triggers:", amd.get("sales_triggers", []))
print("immediate_triggers:", amd.get("immediate_triggers", []))
print("strategic_triggers:", amd.get("strategic_triggers", []))
print("intelligence_quality:", amd.get("intelligence_quality"))
print("live_intel_retrieved:", amd.get("live_intel_retrieved"))

print("")
print("=== PERSONNEL CHANGES ===")
for p in amd.get("personnel_changes", []):
    print(f"  {p.get('name')} | {p.get('change')}")
