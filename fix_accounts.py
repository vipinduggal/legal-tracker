import os, json

home = os.path.expanduser("~")
base = os.path.join(home, "legal-tracker")

# ── Fix 1: cleanup script to remove stale db entries ──────
cleanup_path = os.path.join(base, "scripts", "cleanupDb.js")

cleanup = '''// cleanupDb.js — Remove database entries for accounts no longer in config
import "dotenv/config";
import { initDb, db } from "../src/db.js";
import { ACCOUNTS } from "../config/accounts.js";

await initDb();

const configIds = new Set(ACCOUNTS.map(a => a.id));
const dbIds = Object.keys(db.data.research || {});

const toRemove = dbIds.filter(id => !configIds.has(id));

if (!toRemove.length) {
  console.log("Database is already clean — no stale accounts found");
  process.exit(0);
}

console.log("Removing " + toRemove.length + " stale accounts from database:");
toRemove.forEach(id => {
  console.log("  - " + id);
  delete db.data.research[id];
  delete db.data.lastUpdated[id];
});

await db.write();
console.log("");
console.log("Done — database now has " + Object.keys(db.data.research).length + " accounts matching your config");
''';

with open(cleanup_path, 'w') as f:
    f.write(cleanup)
print("Done — cleanupDb.js written")

# ── Fix 2: update package.json with cleanup script ────────
pkg_path = os.path.join(base, "package.json")
with open(pkg_path, 'r') as f:
    pkg = json.load(f)

pkg["scripts"]["cleanup:db"] = "node scripts/cleanupDb.js"

with open(pkg_path, 'w') as f:
    json.dump(pkg, f, indent=2)
print("Done — package.json updated with cleanup:db script")

# ── Fix 3: patch server.js to filter dashboard by config ──
server_path = os.path.join(base, "src", "server.js")
with open(server_path, 'r') as f:
    server_content = f.read()

# The dashboard already reads from ACCOUNTS (config) for the sidebar
# The issue is the API /api/accounts returns config accounts
# but the db may have extra — this is fine, config is already the filter
# The real fix is just to run cleanupDb so db matches config

print("Dashboard API already filters by config/accounts.js — no server change needed")
print("")
print("=" * 50)
print("NEXT STEPS — run these in order:")
print("=" * 50)
print("")
print("1. Clean up the database:")
print("   npm run cleanup:db")
print("")
print("2. Verify counts match:")
print('   node -e "import(\'./src/db.js\').then(async m=>{await m.initDb();const r=await m.getAllResearch();console.log(\'DB accounts:\',Object.keys(r).length);})"')
print("")
print("3. Run full research on your 32 accounts:")
print("   npm run research:all -- --force")
print("")
print("4. Restart:")
print("   npm start")
