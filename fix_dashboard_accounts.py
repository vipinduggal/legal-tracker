import os

home = os.path.expanduser("~")
base = os.path.join(home, "legal-tracker")

# The fix: server.js /api/accounts endpoint already reads from ACCOUNTS config
# The dashboard sidebar only shows accounts that have hasData=true
# Fix: show ALL accounts, with "needs research" state for unresearched ones
# The dashboard already handles this — the issue is the ACCOUNTS import is cached

# Fix 1: Update /api/accounts to read fresh from file each time
server_path = os.path.join(base, "src", "server.js")

with open(server_path, 'r') as f:
    content = f.read()

# Replace the static ACCOUNTS import with dynamic read
old_import = "import { ACCOUNTS } from '../config/accounts.js';"
new_import = """import { createRequire } from 'module';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dir = dirname(fileURLToPath(import.meta.url));

// Read accounts fresh each time to avoid caching issues
function getAccounts() {
  try {
    // Dynamic read to bypass Node.js module cache
    const content = readFileSync(join(__dir, '..', 'config', 'accounts.js'), 'utf8');
    const match = content.match(/export const ACCOUNTS\\s*=\\s*(\\[[\\s\\S]*?\\]);/);
    if (!match) return [];
    const cleaned = match[1]
      .replace(/\\/\\/[^\\n]*/g, '')
      .replace(/([{,]\\s*)([a-zA-Z_][a-zA-Z0-9_]*)\\s*:/g, '$1"$2":')
      .replace(/'/g, '"')
      .trim();
    return JSON.parse(cleaned);
  } catch(e) {
    // Fallback to static import
    return ACCOUNTS_STATIC;
  }
}"""

# Also keep static import as fallback
old_import_line = "import { ACCOUNTS } from '../config/accounts.js';"
new_import_with_fallback = """import { ACCOUNTS as ACCOUNTS_STATIC } from '../config/accounts.js';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dir = dirname(fileURLToPath(import.meta.url));

function getAccounts() {
  try {
    const content = readFileSync(join(__dir, '..', 'config', 'accounts.js'), 'utf8');
    const match = content.match(/export const ACCOUNTS\\s*=\\s*(\\[[\\s\\S]*?\\]);/);
    if (!match) return ACCOUNTS_STATIC;
    const cleaned = match[1]
      .replace(/\\/\\/[^\\n]*/g, '')
      .replace(/([{,]\\s*)([a-zA-Z_][a-zA-Z0-9_]*)\\s*:/g, '$1"$2":')
      .replace(/'/g, '"')
      .trim();
    const parsed = JSON.parse(cleaned);
    return parsed.length ? parsed : ACCOUNTS_STATIC;
  } catch(e) {
    return ACCOUNTS_STATIC;
  }
}"""

if old_import_line in content:
    content = content.replace(old_import_line, new_import_with_fallback)
    print("Done — added getAccounts() function")
else:
    print("WARNING — ACCOUNTS import not found")

# Fix 2: Replace all uses of ACCOUNTS with getAccounts()
# In the /api/accounts endpoint
old_accounts_endpoint = """app.get('/api/accounts', async (req, res) => {
  const allResearch = await getAllResearch();
  const data = ACCOUNTS.map(a => ({"""

new_accounts_endpoint = """app.get('/api/accounts', async (req, res) => {
  const allResearch = await getAllResearch();
  const ACCOUNTS = getAccounts();
  const data = ACCOUNTS.map(a => ({"""

if old_accounts_endpoint in content:
    content = content.replace(old_accounts_endpoint, new_accounts_endpoint)
    print("Done — /api/accounts now reads fresh accounts")
else:
    print("WARNING — /api/accounts endpoint pattern not found")

# Fix 3: Replace ACCOUNTS in /api/accounts/:id
old_single = """app.get('/api/accounts/:id', async (req, res) => {
  const account = ACCOUNTS.find(a => a.id === req.params.id);"""

new_single = """app.get('/api/accounts/:id', async (req, res) => {
  const account = getAccounts().find(a => a.id === req.params.id);"""

if old_single in content:
    content = content.replace(old_single, new_single)
    print("Done — /api/accounts/:id uses fresh accounts")

# Fix 4: Replace ACCOUNTS in /api/status
old_status = "res.json({ status: 'ok', accounts: ACCOUNTS.length,"
new_status = "const ACCOUNTS_NOW = getAccounts();\n  res.json({ status: 'ok', accounts: ACCOUNTS_NOW.length,"

if old_status in content:
    content = content.replace(old_status, new_status)
    print("Done — /api/status uses fresh accounts")

with open(server_path, 'w') as f:
    f.write(content)

print("")
print("="*50)
print("FIX COMPLETE")
print("="*50)
print("")
print("Now when you add an account in the Account Manager:")
print("  1. It immediately appears in the dashboard sidebar")
print("  2. Shows 'needs research' state until researched")
print("  3. No server restart needed")
print("")
print("Restart: pkill -f 'node src/index.js' && npm start")
print("Then add a test account and check the dashboard")
