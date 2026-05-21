import express from 'express';
import { ACCOUNTS } from '../config/accounts.js';
import { getAllResearch, getLatestDigest, db } from './db.js';
import { logger } from './logger.js';
import { registerAccountRoutes } from './accountRoutes.js';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const app = express();
app.use(express.json());

app.get('/api/accounts', async (req, res) => {
  const allResearch = await getAllResearch();
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
  const account = ACCOUNTS.find(a => a.id === req.params.id);
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
  res.json({ status: 'ok', accounts: ACCOUNTS.length, researched, pending: ACCOUNTS.length - researched, recentRuns: (db.data.runs || []).slice(0, 5) });
});

registerAccountRoutes(app);

app.get('/', (req, res) => {
  const html = readFileSync(join(__dirname, 'dashboard.html'), 'utf8');
  res.send(html);
});

export function startServer() {
  const port = process.env.PORT || 3000;
  app.listen(port, () => logger.info('Dashboard at http://localhost:' + port));
  return app;
}
