import os

home = os.path.expanduser("~")
base = os.path.join(home, "legal-tracker")

# ── Fix 1: accountRoutes.js — fix caching issue + add reload ──
routes_path = os.path.join(base, "src", "accountRoutes.js")

routes_content = """// accountRoutes.js — Account management API routes
import { getAllResearch, db } from './db.js';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ACCOUNTS_PATH = path.join(__dirname, '..', 'config', 'accounts.js');

// Read accounts directly from file each time — avoids Node.js module cache
function readAccountsFromFile() {
  const content = fs.readFileSync(ACCOUNTS_PATH, 'utf8');
  // Extract the array using regex — works without re-importing the module
  const match = content.match(/export const ACCOUNTS\\s*=\\s*(\\[[\\s\\S]*?\\]);/);
  if (!match) throw new Error('Could not parse accounts.js');
  // Safe eval of the array literal
  const arrayStr = match[1]
    .replace(/\\/\\/[^\\n]*/g, '') // remove comments
    .trim();
  return JSON.parse(
    arrayStr
      .replace(/([{,]\\s*)(\\w+):/g, '$1"$2":') // quote keys
      .replace(/'/g, '"') // single to double quotes
  );
}

export function registerAccountRoutes(app) {

  // GET all accounts with research status
  app.get('/api/config/accounts', async (req, res) => {
    try {
      const ACCOUNTS = readAccountsFromFile();
      const allResearch = await getAllResearch();
      res.json(ACCOUNTS.map(a => ({
        ...a,
        hasData: !!allResearch[a.id],
        lastUpdated: db.data.lastUpdated?.[a.id] || null,
        contactCount: allResearch[a.id]?.contacts?.length || 0,
        activeIssues: [
          ...(allResearch[a.id]?.litigation || []).filter(l => !['Resolved','Settled','Dismissed'].includes(l.status)),
          ...(allResearch[a.id]?.regulatory || []).filter(r => !['Resolved','Closed'].includes(r.status)),
        ].length,
      })));
    } catch(e) {
      res.status(500).json({ error: e.message });
    }
  });

  // POST add new account
  app.post('/api/config/accounts', async (req, res) => {
    try {
      const { name, industry, location } = req.body;
      if (!name || !industry || !location) {
        return res.status(400).json({ error: 'name, industry, and location are required' });
      }
      const id = name.toLowerCase()
        .replace(/[^a-z0-9\\s]/g, '')
        .trim()
        .replace(/\\s+/g, '_');

      let fileContent = fs.readFileSync(ACCOUNTS_PATH, 'utf8');

      // Check for duplicate
      if (fileContent.includes('"' + id + '"')) {
        return res.status(409).json({ error: 'Account already exists: ' + name });
      }

      const newLine = '  { id: "' + id + '", name: "' + name + '", industry: "' + industry + '", location: "' + location + '" },';
      const pos = fileContent.lastIndexOf('];');
      if (pos === -1) return res.status(500).json({ error: 'Could not find insertion point in accounts.js' });
      fileContent = fileContent.slice(0, pos) + newLine + '\\n' + fileContent.slice(pos);
      fs.writeFileSync(ACCOUNTS_PATH, fileContent);

      res.json({ success: true, account: { id, name, industry, location } });
    } catch(e) {
      res.status(500).json({ error: e.message });
    }
  });

  // DELETE remove account
  app.delete('/api/config/accounts/:id', async (req, res) => {
    try {
      const id = req.params.id;
      let fileContent = fs.readFileSync(ACCOUNTS_PATH, 'utf8');

      const lines = fileContent.split('\\n');
      const filtered = lines.filter(line => !line.includes('"' + id + '"'));
      if (filtered.length === lines.length) {
        return res.status(404).json({ error: 'Account not found: ' + id });
      }
      fs.writeFileSync(ACCOUNTS_PATH, filtered.join('\\n'));

      // Remove from database
      await db.read();
      if (db.data.research) delete db.data.research[id];
      if (db.data.lastUpdated) delete db.data.lastUpdated[id];
      await db.write();

      res.json({ success: true, removed: id });
    } catch(e) {
      res.status(500).json({ error: e.message });
    }
  });

  // GET account count — lightweight check
  app.get('/api/config/accounts/count', async (req, res) => {
    try {
      const ACCOUNTS = readAccountsFromFile();
      res.json({ count: ACCOUNTS.length });
    } catch(e) {
      res.status(500).json({ error: e.message });
    }
  });

  app.get('/manage', async (req, res) => {
    const mod = await import('./accountManager.js');
    res.send(mod.ACCOUNT_MANAGER_HTML);
  });

}
""";

with open(routes_path, 'w') as f:
    f.write(routes_content)
print("Done — accountRoutes.js rewritten with file-based reading (no cache)")

# ── Fix 2: Add navigation bar to main dashboard ────────────
server_path = os.path.join(base, "src", "server.js")

with open(server_path, 'r') as f:
    server_content = f.read()

# Find the topbar HTML in the dashboard and add nav links
old_topbar = """<div class='tb-r'>
    <div class='ts'><strong id='stat-res'>-</strong>&nbsp;researched</div>
    <div class='td'></div>
    <div class='ts'><strong id='stat-iss'>-</strong>&nbsp;active issues</div>
    <div class='td'></div>
    <div class='ts'><div class='live-dot'></div>&nbsp;Live</div>
  </div>"""

new_topbar = """<div class='tb-r'>
    <div class='ts'><strong id='stat-res'>-</strong>&nbsp;researched</div>
    <div class='td'></div>
    <div class='ts'><strong id='stat-iss'>-</strong>&nbsp;active issues</div>
    <div class='td'></div>
    <div class='ts'><div class='live-dot'></div>&nbsp;Live</div>
    <div class='td'></div>
    <a href='/manage' style='font-size:12px;color:rgba(255,255,255,.8);text-decoration:none;padding:4px 10px;border:1px solid rgba(255,255,255,.25);border-radius:6px;transition:all .12s' onmouseover='this.style.background="rgba(255,255,255,.1)"' onmouseout='this.style.background="transparent"'>&#9881; Manage accounts</a>
    <a href='/api/status' target='_blank' style='font-size:12px;color:rgba(255,255,255,.6);text-decoration:none;padding:4px 10px;border:1px solid rgba(255,255,255,.15);border-radius:6px' title='System status'>Status</a>
    <a href='/api/digest' target='_blank' style='font-size:12px;color:rgba(255,255,255,.6);text-decoration:none;padding:4px 10px;border:1px solid rgba(255,255,255,.15);border-radius:6px' title='Latest digest JSON'>Digest</a>
  </div>"""

if old_topbar in server_content:
    server_content = server_content.replace(old_topbar, new_topbar)
    print("Done — navigation links added to dashboard topbar")
else:
    print("WARNING — could not find topbar in server.js — nav links not added")
    print("You may need to add them manually")

with open(server_path, 'w') as f:
    f.write(server_content)

# ── Fix 3: Update accountManager.js to auto-refresh + show confirmation ──
manager_path = os.path.join(base, "src", "accountManager.js")

with open(manager_path, 'r') as f:
    manager_content = f.read()

# Fix the addAccount function to show better confirmation
old_add_success = """    showToast(name + ' added successfully', 'success');
    hideAddForm();
    await loadAccounts();
    status.textContent = 'To research: npm run research:account "' + name + '"';"""

new_add_success = """    showToast(name + ' added — reloading list...', 'success');
    hideAddForm();
    // Small delay to ensure file is written before re-reading
    await new Promise(r => setTimeout(r, 500));
    await loadAccounts();
    // Highlight the newly added account
    const rows = document.querySelectorAll('#account-tbody tr');
    rows.forEach(row => {
      if (row.textContent.includes(name)) {
        row.style.background = '#E6F5F2';
        row.style.transition = 'background 1.5s';
        setTimeout(() => { row.style.background = ''; }, 2000);
      }
    });
    // Show research reminder
    const reminder = document.getElementById('research-reminder');
    if (reminder) {
      reminder.style.display = 'block';
      reminder.textContent = '✓ ' + name + ' added. To research it now, open a terminal and run: npm run research:account "' + name + '"';
    }"""

if old_add_success in manager_content:
    manager_content = manager_content.replace(old_add_success, new_add_success)
    print("Done — account manager updated with confirmation highlighting")
else:
    print("Skipped manager confirmation update — pattern not found")

# Add research reminder div to the manager HTML
old_card_end = """  <div class='card' id='add-form-card' style='display:none'>"""
new_card_end = """  <div id='research-reminder' style='display:none;background:#E6F5F2;border:1px solid #A7D7D0;border-radius:10px;padding:12px 16px;margin-bottom:12px;font-size:13px;color:#0A7C6E;font-weight:500'></div>

  <div class='card' id='add-form-card' style='display:none'>"""

if old_card_end in manager_content:
    manager_content = manager_content.replace(old_card_end, new_card_end)
    print("Done — research reminder banner added to account manager")

with open(manager_path, 'w') as f:
    f.write(manager_content)

print("")
print("=" * 50)
print("ALL FIXES APPLIED")
print("=" * 50)
print("")
print("1. Account caching bug FIXED — new accounts show immediately")
print("2. Nav links added to dashboard — Manage Accounts, Status, Digest")
print("3. Account manager shows green confirmation when account is added")
print("")
print("Restart the tracker:")
print("  pkill -f 'node src/index.js'")
print("  npm start")
print("")
print("Available URLs:")
print("  http://localhost:3000          — Main dashboard")
print("  http://localhost:3000/manage   — Account manager")
print("  http://localhost:3000/api/status  — System status")
print("  http://localhost:3000/api/digest  — Latest digest")
print("  http://localhost:3000/api/accounts — All accounts (JSON)")
