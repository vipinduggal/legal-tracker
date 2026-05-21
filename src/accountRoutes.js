// accountRoutes.js — Account management API routes
import { getAllResearch, db } from './db.js';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { createRequire } from 'module';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ACCOUNTS_PATH = path.join(__dirname, '..', 'config', 'accounts.js');

// Load accounts fresh each time by reading file and using dynamic import with cache bust
async function getAccounts() {
  const mod = await import('../config/accounts.js?t=' + Date.now());
  return mod.ACCOUNTS;
}

export function registerAccountRoutes(app) {

  // GET all accounts with research status
  app.get('/api/config/accounts', async (req, res) => {
    try {
      const ACCOUNTS = await getAccounts();
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
      console.error('GET /api/config/accounts error:', e.message);
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
        .replace(/[^a-z0-9\s]/g, '')
        .trim()
        .replace(/\s+/g, '_');

      let fileContent = fs.readFileSync(ACCOUNTS_PATH, 'utf8');

      if (fileContent.includes('"' + id + '"')) {
        return res.status(409).json({ error: 'Account already exists: ' + name });
      }

      const newLine = '  { id: "' + id + '", name: "' + name + '", industry: "' + industry + '", location: "' + location + '" },';
      const pos = fileContent.lastIndexOf('];');
      if (pos === -1) return res.status(500).json({ error: 'Could not find insertion point' });
      fileContent = fileContent.slice(0, pos) + newLine + '\n' + fileContent.slice(pos);
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

      const lines = fileContent.split('\n');
      const filtered = lines.filter(line => !line.includes('"' + id + '"'));
      if (filtered.length === lines.length) {
        return res.status(404).json({ error: 'Account not found: ' + id });
      }
      fs.writeFileSync(ACCOUNTS_PATH, filtered.join('\n'));

      await db.read();
      if (db.data.research) delete db.data.research[id];
      if (db.data.lastUpdated) delete db.data.lastUpdated[id];
      await db.write();

      res.json({ success: true, removed: id });
    } catch(e) {
      res.status(500).json({ error: e.message });
    }
  });

  // POST trigger research for one account
  app.post('/api/research/:id', async (req, res) => {
    try {
      const id = req.params.id;
      const ACCOUNTS = await getAccounts();
      const account = ACCOUNTS.find(a => a.id === id);
      if (!account) return res.status(404).json({ error: 'Account not found: ' + id });

      res.json({ success: true, message: 'Research started for ' + account.name });

      setImmediate(async () => {
        try {
          const { researchAccount, detectChanges } = await import('./researcher.js');
          const { getResearch, setResearch, logRun } = await import('./db.js');
          const { sendAccountUpdateEmail } = await import('./emailer.js');
          const { postAccountUpdateToTeams } = await import('./teams.js');
          const oldData = await getResearch(id);
          const newData = await researchAccount(account);
          if (newData) {
            const changes = detectChanges(oldData, newData);
            await setResearch(id, newData);
            const hasChanges = !oldData || changes.some(c => !c.includes('No significant'));
            if (hasChanges) {
              await Promise.allSettled([
                sendAccountUpdateEmail(account, changes, newData),
                postAccountUpdateToTeams(account, changes, newData),
              ]);
            }
            await logRun({ job: 'manual_research', account: account.name, success: true });
          }
        } catch(err) {
          console.error('Background research failed:', err.message);
        }
      });

    } catch(e) {
      res.status(500).json({ error: e.message });
    }
  });

  // GET research status
  app.get('/api/research/:id/status', async (req, res) => {
    try {
      const id = req.params.id;
      await db.read();
      res.json({
        id,
        hasData: !!db.data.research?.[id],
        lastUpdated: db.data.lastUpdated?.[id] || null,
      });
    } catch(e) {
      res.status(500).json({ error: e.message });
    }
  });

  // GET manage page — serve directly from file

  // GET readable digest page
  app.get('/digest', (req, res) => {
    res.sendFile(path.join(__dirname, 'digest.html'));
  });

  // POST generate new digest (queues it)
  app.post('/api/digest/generate', async (req, res) => {
    res.json({ queued: true, message: 'Digest generation started' });
    setImmediate(async () => {
      try {
        const { runWeeklyDigest } = await import('../jobs/weeklyDigest.js');
        await runWeeklyDigest();
      } catch(e) {
        console.error('Digest generation failed:', e.message);
      }
    });
  });

  app.get('/manage', (req, res) => {
    res.sendFile(path.join(__dirname, 'manager.html'));
  });

}
