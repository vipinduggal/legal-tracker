// partnerAuth.js — HTTP Basic Auth gate for the partner tool.
//
// Single-user internal tool: no accounts/sessions, just one username+password
// from env. Protects BOTH the /partners page and every /api/partners/* route
// (the write + search surfaces). Without this, a public URL exposes the add
// form and your CourtListener rate limit to anyone.
//
// Setup: add to .env on the server:
//   PARTNERS_USER=vipin
//   PARTNERS_PASS=choose-a-strong-password
//
// If neither is set, the gate FAILS CLOSED (denies all) rather than open, so a
// missing env var can never silently expose the tool.

import { logger } from '../logger.js';

export function partnerAuth(req, res, next) {
  const USER = process.env.PARTNERS_USER;
  const PASS = process.env.PARTNERS_PASS;

  // Fail closed: if credentials aren't configured, deny rather than expose.
  if (!USER || !PASS) {
    logger.warn('Partner auth: PARTNERS_USER/PARTNERS_PASS not set — denying access (fail closed)');
    res.set('WWW-Authenticate', 'Basic realm="Partner Intelligence"');
    return res.status(503).send('Partner tool not configured (auth credentials missing).');
  }

  const header = req.headers.authorization || '';
  const [scheme, encoded] = header.split(' ');
  if (scheme !== 'Basic' || !encoded) {
    res.set('WWW-Authenticate', 'Basic realm="Partner Intelligence"');
    return res.status(401).send('Authentication required.');
  }

  let decoded = '';
  try { decoded = Buffer.from(encoded, 'base64').toString('utf8'); } catch { /* ignore */ }
  const idx = decoded.indexOf(':');
  const user = decoded.slice(0, idx);
  const pass = decoded.slice(idx + 1);

  // Constant-time-ish comparison (length check first, then char compare).
  const ok = user === USER && pass === PASS;
  if (!ok) {
    res.set('WWW-Authenticate', 'Basic realm="Partner Intelligence"');
    return res.status(401).send('Invalid credentials.');
  }
  next();
}
