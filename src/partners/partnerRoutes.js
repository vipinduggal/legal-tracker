// partnerRoutes.js — /partners site + API. Registered like registerAccountRoutes(app).
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { getAllPartners, pdb, addPartner, getCounters, consumeImmediateSearch, getAddedPartners, ADDS_PER_DAY, IMMEDIATE_SEARCHES_PER_DAY } from './partnersDb.js';
import { runPartnerMonitor } from './partnerMonitor.js';
import { PARTNERS } from '../../config/partners.js';
import { partnerAuth } from './partnerAuth.js';

const __dirname = dirname(fileURLToPath(import.meta.url));

export function registerPartnerRoutes(app) {
  // Gate the page and all API routes with basic auth (write + search surface).
  app.use('/partners', partnerAuth);
  app.use('/api/partners', partnerAuth);

  // Dashboard page
  app.get('/partners', (req, res) => {
    try {
      res.send(readFileSync(join(__dirname, 'partners.html'), 'utf8'));
    } catch (e) {
      res.status(500).send('Partner dashboard not found: ' + e.message);
    }
  });

  // All tracked partners (seed + manually added) with their cases + triggers
  app.get('/api/partners', async (req, res) => {
    try {
      const stored = await getAllPartners();
      const added = await getAddedPartners();
      const universe = [...PARTNERS];
      for (const a of added) if (!universe.some(p => p.id === a.id)) universe.push(a);
      const data = universe.map(p => {
        const rec = stored[p.id] || {};
        const cases = Object.values(rec.cases || {});
        return {
          ...p,
          defenseCases: cases.length,
          triggers: (rec.triggers || []).length,
          lastChecked: pdb.data.lastChecked?.[p.id] || null,
          leavingFederal: cases.filter(c => c.jurisdiction === 'LEAVING_FEDERAL').length,
        };
      });
      res.json(data);
    } catch (e) {
      res.status(500).json({ error: e.message });
    }
  });

  // Daily limits + remaining counts (for the add form UI)
  app.get('/api/partners/limits', async (req, res) => {
    try {
      const c = await getCounters();
      res.json({
        addsPerDay: ADDS_PER_DAY,
        immediatePerDay: IMMEDIATE_SEARCHES_PER_DAY,
        addsUsed: c.adds, immediateUsed: c.immediateSearches,
        addsRemaining: Math.max(0, ADDS_PER_DAY - c.adds),
        immediateRemaining: Math.max(0, IMMEDIATE_SEARCHES_PER_DAY - c.immediateSearches),
      });
    } catch (e) { res.status(500).json({ error: e.message }); }
  });

  // Add a partner. Body: { name, firm, city, tier, searchNow }
  // searchNow runs an immediate detection pass (capped at 2/day) — otherwise the
  // partner is queued for the next scheduled/manual run (zero API calls now).
  app.post('/api/partners/add', async (req, res) => {
    try {
      const { name, firm, city, tier, searchNow } = req.body || {};
      const result = await addPartner({ name, firm, city, tier });
      if (!result.ok) return res.status(400).json(result);

      let searched = false, searchMsg = 'Queued for next scheduled run.';
      if (searchNow) {
        if (await consumeImmediateSearch()) {
          // Fire-and-forget: respond immediately, search runs in background.
          runPartnerMonitor(result.id).catch(() => {});
          searched = true;
          searchMsg = 'Immediate search started — results will appear shortly.';
        } else {
          searchMsg = `Immediate-search limit reached (${IMMEDIATE_SEARCHES_PER_DAY}/day). Queued instead.`;
        }
      }
      res.json({ ...result, searched, searchMsg });
    } catch (e) { res.status(500).json({ error: e.message }); }
  });

  // Check-now for a single existing partner (also counts against immediate cap).
  app.post('/api/partners/:id/check', async (req, res) => {
    try {
      if (!(await consumeImmediateSearch()))
        return res.status(429).json({ error: `Immediate-search limit reached (${IMMEDIATE_SEARCHES_PER_DAY}/day).` });
      runPartnerMonitor(req.params.id).catch(() => {});
      res.json({ ok: true, message: 'Search started — refresh in a minute.' });
    } catch (e) { res.status(500).json({ error: e.message }); }
  });

  // One partner detail (cases + triggers)
  app.get('/api/partners/:id', async (req, res) => {
    try {
      const stored = await getAllPartners();
      const profile = PARTNERS.find(p => p.id === req.params.id);
      if (!profile) return res.status(404).json({ error: 'Not found' });
      const rec = stored[req.params.id] || { cases: {}, triggers: [] };
      res.json({ ...profile, cases: Object.values(rec.cases || {}), triggers: rec.triggers || [], lastChecked: pdb.data.lastChecked?.[req.params.id] || null });
    } catch (e) {
      res.status(500).json({ error: e.message });
    }
  });

  // Flat trigger feed across all partners, newest first
  app.get('/api/partners/triggers/all', async (req, res) => {
    try {
      const stored = await getAllPartners();
      const all = [];
      for (const [id, rec] of Object.entries(stored)) {
        const name = PARTNERS.find(p => p.id === id)?.name || id;
        for (const t of (rec.triggers || [])) all.push({ partner: name, partnerId: id, ...t });
      }
      all.sort((a, b) => new Date(b.detectedAt) - new Date(a.detectedAt));
      res.json(all);
    } catch (e) {
      res.status(500).json({ error: e.message });
    }
  });
}
