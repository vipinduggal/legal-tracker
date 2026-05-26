import express from 'express';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { ACCOUNTS as ACCOUNTS_STATIC } from '../config/accounts.js';
import { getAllResearch, getLatestDigest, db } from './db.js';
import { logger } from './logger.js';
import { registerAccountRoutes } from './accountRoutes.js';
import quickResearchRouter from './routes/quickResearch.js';

const __dirname = dirname(fileURLToPath(import.meta.url));

// Read accounts fresh each time — bypasses Node.js module cache
// so newly added accounts appear immediately without restart
function getAccounts() {
  try {
    const raw = readFileSync(join(__dirname, '..', 'config', 'accounts.js'), 'utf8');
    const match = raw.match(/export const ACCOUNTS\s*=\s*(\[[\s\S]*?\]);/);
    if (!match) return ACCOUNTS_STATIC;
    const cleaned = match[1]
      .replace(/\/\/[^\n]*/g, '')
      .replace(/([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:/g, '$1"$2":')
      .replace(/'/g, '"')
      .trim();
    const parsed = JSON.parse(cleaned);
    return parsed.length ? parsed : ACCOUNTS_STATIC;
  } catch(e) {
    return ACCOUNTS_STATIC;
  }
}

const app = express();
app.use(express.json());

// Health check
app.get('/research', (req, res) => res.sendFile(join(dirname(new URL(import.meta.url).pathname), 'research.html')));
app.use('/api/quick-research', quickResearchRouter);

app.get('/health', (req, res) => res.status(200).json({ status: 'ok' }));
app.get('/healthz', (req, res) => res.status(200).json({ status: 'ok' }));

// Account count — single source of truth used by all pages
app.get('/api/account-count', (req, res) => {
  const accounts = getAccounts();
  res.json({ count: accounts.length });
});

app.get('/api/accounts', async (req, res) => {
  try {
    const allResearch = await getAllResearch();
    const ACCOUNTS = getAccounts();
    const data = ACCOUNTS.map(a => ({
      ...a,
      hasData: !!allResearch[a.id],
      lastUpdated: db.data.lastUpdated?.[a.id] || null,
      contactCount: allResearch[a.id]?.contacts?.length || 0,
      activeIssues: [
        ...(allResearch[a.id]?.litigation || []).filter(l => !['Resolved','Settled','Dismissed'].includes(l.status)),
        ...(allResearch[a.id]?.regulatory || []).filter(r => !['Resolved','Closed'].includes(r.status)),
      ].length,
    }));
    res.json(data);
  } catch(e) {
    res.status(500).json({ error: e.message });
  }
});

app.get('/api/accounts/:id', async (req, res) => {
  try {
    const account = getAccounts().find(a => a.id === req.params.id);
    if (!account) return res.status(404).json({ error: 'Not found' });
    const allResearch = await getAllResearch();
    res.json({ ...account, lastUpdated: db.data.lastUpdated?.[account.id] || null, research: allResearch[account.id] || null });
  } catch(e) {
    res.status(500).json({ error: e.message });
  }
});

app.get('/api/digest', async (req, res) => {
  try {
    const digest = await getLatestDigest();
    res.json(digest || { message: 'No digest yet' });
  } catch(e) {
    res.status(500).json({ error: e.message });
  }
});

app.get('/api/status', async (req, res) => {
  try {
    await db.read();
    const allResearch = await getAllResearch();
    const researched = Object.keys(allResearch).length;
    const ACCOUNTS = getAccounts();
    res.json({ status: 'ok', accounts: ACCOUNTS.length, researched, pending: ACCOUNTS.length - researched, recentRuns: (db.data.runs || []).slice(0, 5) });
  } catch(e) {
    res.status(500).json({ error: e.message });
  }
});

registerAccountRoutes(app);

app.get('/', (req, res) => {
  try {
    res.send(readFileSync(join(__dirname, 'dashboard.html'), 'utf8'));
  } catch(e) {
    res.status(500).send('Dashboard not found: ' + e.message);
  }
});

export function startServer() {
  const port = parseInt(process.env.PORT) || 3000;
  console.log('RAILWAY PORT ENV:', process.env.PORT, 'USING PORT:', port);
  app.listen(port, '0.0.0.0', () => logger.info('Dashboard at http://localhost:' + port));
  return app;
}
