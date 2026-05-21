import os, json

home = os.path.expanduser("~")
base = os.path.join(home, "legal-tracker")

# Read the accounts config
accounts_path = os.path.join(base, "config", "accounts.js")
with open(accounts_path, 'r') as f:
    content = f.read()

# Extract IDs from accounts.js
import re
ids = re.findall(r'id:\s*"([^"]+)"', content)
print("Accounts in config: " + str(len(ids)))
print("IDs: " + ", ".join(ids[:5]) + "...")

# Read the database
db_path = os.path.join(base, "data", "db.json")
with open(db_path, 'r') as f:
    db = json.load(f)

research = db.get("research", {})
last_updated = db.get("lastUpdated", {})

print("Accounts in database: " + str(len(research)))

keep = set(ids)
to_remove = [k for k in research.keys() if k not in keep]
print("Accounts to remove: " + str(len(to_remove)))

for k in to_remove:
    del research[k]
    if k in last_updated:
        del last_updated[k]

db["research"] = research
db["lastUpdated"] = last_updated

with open(db_path, 'w') as f:
    json.dump(db, f)

print("Done — database now has " + str(len(research)) + " accounts")
