// cleanupDb.js — Remove database entries for accounts no longer in config
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
