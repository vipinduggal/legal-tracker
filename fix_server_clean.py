import os

home = os.path.expanduser("~")
base = os.path.join(home, "legal-tracker")
server_path = os.path.join(base, "src", "server.js")

# Read current server.js
with open(server_path, 'r') as f:
    content = f.read()

# Remove everything between the account management markers if they exist
# Strategy: find the new_endpoints block and remove it, then add clean version

# Find where the account management block starts
start_marker = '// ── Account Management API ──'
end_marker = "app.get('/manage'"

if start_marker in content:
    start_idx = content.index(start_marker)
    # Find the manage route and include it in removal
    if end_marker in content:
        end_idx = content.index(end_marker)
        # Find end of manage route
        manage_end = content.index('\n\n', end_idx + 100)
        content = content[:start_idx] + content[manage_end:]
        print("Removed old account management block")

# Now write a separate accountRoutes.js file with clean account management
routes_path = os.path.join(base, "src", "accountRoutes.js")

routes_content = """// accountRoutes.js — Account management API routes
import { getAllResearch, db } from './db.js';

export function registerAccountRoutes(app) {

  app.get('/api/config/accounts', async (req, res) => {
    try {
      const mod = await import('../config/accounts.js');
      const ACCOUNTS = mod.ACCOUNTS;
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

      const fs = await import('fs');
      const pathMod = await import('path');
      const { fileURLToPath } = await import('url');
      const dir = pathMod.default.dirname(fileURLToPath(import.meta.url));
      const accountsPath = pathMod.default.join(dir, '..', 'config', 'accounts.js');
      let fileContent = fs.default.readFileSync(accountsPath, 'utf8');

      if (fileContent.includes(id + '"')) {
        return res.status(409).json({ error: 'Account already exists: ' + name });
      }

      const newLine = '  { id: "' + id + '", name: "' + name + '", industry: "' + industry + '", location: "' + location + '" },';
      const insertBefore = '];';
      const pos = fileContent.lastIndexOf(insertBefore);
      if (pos === -1) return res.status(500).json({ error: 'Could not find insertion point' });
      fileContent = fileContent.slice(0, pos) + newLine + '\\n' + fileContent.slice(pos);
      fs.default.writeFileSync(accountsPath, fileContent);
      res.json({ success: true, account: { id, name, industry, location } });
    } catch(e) {
      res.status(500).json({ error: e.message });
    }
  });

  app.delete('/api/config/accounts/:id', async (req, res) => {
    try {
      const id = req.params.id;
      const fs = await import('fs');
      const pathMod = await import('path');
      const { fileURLToPath } = await import('url');
      const dir = pathMod.default.dirname(fileURLToPath(import.meta.url));
      const accountsPath = pathMod.default.join(dir, '..', 'config', 'accounts.js');
      let fileContent = fs.default.readFileSync(accountsPath, 'utf8');

      const lines = fileContent.split('\\n');
      const filtered = lines.filter(line => !line.includes('"' + id + '"'));
      if (filtered.length === lines.length) {
        return res.status(404).json({ error: 'Account not found: ' + id });
      }
      fs.default.writeFileSync(accountsPath, filtered.join('\\n'));

      await db.read();
      if (db.data.research) delete db.data.research[id];
      if (db.data.lastUpdated) delete db.data.lastUpdated[id];
      await db.write();

      res.json({ success: true, removed: id });
    } catch(e) {
      res.status(500).json({ error: e.message });
    }
  });

  app.get('/manage', async (req, res) => {
    const mod = await import('./accountManager.js');
    res.send(mod.ACCOUNT_MANAGER_HTML);
  });

}
"""

with open(routes_path, 'w') as f:
    f.write(routes_content)
print("Done — accountRoutes.js written cleanly")

# Now add a single clean import to server.js
import_line = "import { registerAccountRoutes } from './accountRoutes.js';\n"
register_line = "\nregisterAccountRoutes(app);\n"

if 'registerAccountRoutes' not in content:
    # Add import after other imports
    content = content.replace(
        "import { logger } from './logger.js';",
        "import { logger } from './logger.js';\n" + import_line
    )
    # Add registration before the dashboard route
    content = content.replace(
        "app.get('/', (req, res) => res.send(HTML));",
        register_line + "app.get('/', (req, res) => res.send(HTML));"
    )
    print("Done — server.js updated with clean import")
else:
    print("server.js already has registerAccountRoutes")

with open(server_path, 'w') as f:
    f.write(content)

print("Done — server.js saved")
print("")
print("Run: npm start")
print("Then open: http://localhost:3000/manage")
