import express from 'express';
import { ACCOUNTS as ACCOUNTS_STATIC } from '../config/accounts.js';
function getAccounts() {
  try {
    const content = readFileSync(join(__dir, '..', 'config', 'accounts.js'), 'utf8');
    const match = content.match(/export const ACCOUNTS\s*=\s*(\[[\s\S]*?\]);/);
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
import { getAllResearch, getLatestDigest, db } from './db.js';
import { logger } from './logger.js';
import { registerAccountRoutes } from './accountRoutes.js';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const app = express();
app.use(express.json());

// Health check for Railway — must respond immediately
app.get('/health', (req, res) => res.status(200).json({ status: 'ok' }));
app.get('/healthz', (req, res) => res.status(200).json({ status: 'ok' }));

app.get('/api/accounts', async (req, res) => {
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
});

app.get('/api/accounts/:id', async (req, res) => {
  const account = getAccounts().find(a => a.id === req.params.id);
  if (!account) return res.status(404).json({ error: 'Not found' });
  const allResearch = await getAllResearch();
  res.json({ ...account, lastUpdated: db.data.lastUpdated?.[account.id] || null, research: allResearch[account.id] || null });
});

app.get('/api/digest', async (req, res) => {
  const digest = await getLatestDigest();
  res.json(digest || { message: 'No digest yet' });
});

app.get('/api/status', async (req, res) => {
  await db.read();
  const allResearch = await getAllResearch();
  const researched = Object.keys(allResearch).length;
  const ACCOUNTS_NOW = getAccounts();
  res.json({ status: 'ok', accounts: ACCOUNTS_NOW.length, researched, pending: ACCOUNTS.length - researched, recentRuns: (db.data.runs || []).slice(0, 5) });
});

registerAccountRoutes(app);

app.get('/', (req, res) => {
  const html = readFileSync(join(__dirname, 'dashboard.html'), 'utf8');
  res.send(html);
});

export function startServer() {
  const port = parseInt(process.env.PORT) || 3000;
  console.log('RAILWAY PORT ENV:', process.env.PORT, 'USING PORT:', port);
  app.listen(port, "0.0.0.0", () => logger.info('Dashboard at http://localhost:' + port));
  return app;
}
