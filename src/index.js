// index.js — Main entry point
// Starts the scheduler (cron jobs) and the web dashboard

import 'dotenv/config';
import cron from 'node-cron';
import { initDb } from './db.js';
import { startServer } from './server.js';
import { runDailyResearch } from './jobs/researchAll.js';
import { runFilingsMonitor } from './jobs/filingsMonitor.js';
import { runLitigationMonitor } from './jobs/litigationMonitor.js';
import { runCourtListenerMonitor } from './jobs/courtListenerMonitor.js';
import { runSECFilingsPuller } from './jobs/secFilingsPuller.js';
import { runWeeklyDigest } from './jobs/weeklyDigest.js';
import { logger } from './logger.js';

// Start web server FIRST before anything else
// Railway health check fires immediately — server must be ready
startServer();

async function main() {
  logger.info('Starting Legal Account Tracker...');

  // Initialize database
  await initDb();
  logger.info('Database initialized');

  // ── Cron: SEC filings deep pull (Sunday 5:00 AM weekly) ──
  const secCron = process.env.SEC_CRON || '0 5 * * 0';
  cron.schedule(secCron, async () => {
    logger.info('Cron: SEC filings puller triggered');
    try { await runSECFilingsPuller(); } catch(e) { logger.error('SEC puller failed', { error: e.message }); }
  }, { timezone: 'America/Los_Angeles' });
  logger.info(`SEC filings puller scheduled: ${secCron} (Sundays 5 AM)`);

  // ── Cron: CourtListener docket monitor (6:45 AM daily) ──
  const clCron = process.env.COURTLISTENER_CRON || '45 6 * * *';
  cron.schedule(clCron, async () => {
    logger.info('Cron: CourtListener monitor triggered');
    try { await runCourtListenerMonitor(); } catch(e) { logger.error('CourtListener monitor failed', { error: e.message }); }
  }, { timezone: 'America/Los_Angeles' });
  logger.info(`CourtListener monitor scheduled: ${clCron} (America/Los_Angeles)`);

  // ── Cron: Litigation intelligence monitor (6:30 AM daily) ──
  const litCron = process.env.LITIGATION_CRON || '30 6 * * *';
  cron.schedule(litCron, async () => {
    logger.info('Cron: litigation monitor triggered');
    try { await runLitigationMonitor(); } catch(e) { logger.error('Litigation monitor failed', { error: e.message }); }
  }, { timezone: process.env.TZ || 'America/Los_Angeles' });
  logger.info(`Litigation monitor scheduled: ${litCron} (America/Los_Angeles)`);

  // ── Cron: Daily research (default: 7:00 AM every day) ──
  const researchCron = process.env.RESEARCH_CRON || '0 7 * * *';
  cron.schedule(researchCron, async () => {
    logger.info('Cron: daily research triggered');
    try {
      await runDailyResearch();
    } catch (err) {
      logger.error('Cron: daily research failed', { error: err.message });
    }
  }, { timezone: 'America/Los_Angeles' });
  logger.info(`Daily research scheduled: ${researchCron} (America/Los_Angeles)`);

  // ── Cron: Filings monitor (default: 6:00 AM every day) ──
  const filingsCron = '0 6 * * *';
  cron.schedule(filingsCron, async () => {
    logger.info('Cron: filings monitor triggered');
    try {
      await runFilingsMonitor();
    } catch (err) {
      logger.error('Cron: filings monitor failed', { error: err.message });
    }
  }, { timezone: 'America/Los_Angeles' });
  logger.info(`Filings monitor scheduled: ${filingsCron} (America/Los_Angeles)`);

  // ── Cron: Weekly digest (default: Monday 8:00 AM) ──
  const digestCron = process.env.DIGEST_CRON || '0 8 * * 1';
  cron.schedule(digestCron, async () => {
    logger.info('Cron: weekly digest triggered');
    try {
      await runWeeklyDigest();
    } catch (err) {
      logger.error('Cron: weekly digest failed', { error: err.message });
    }
  }, { timezone: 'America/Los_Angeles' });
  logger.info(`Weekly digest scheduled: ${digestCron} (America/Los_Angeles)`);

  logger.info('✓ Legal Account Tracker running');
  logger.info('  Dashboard: http://localhost:' + (process.env.PORT || 3000));
  logger.info('  Run research now: npm run research:all');
  logger.info('  Run digest now: npm run digest:weekly');
}

// Graceful shutdown
process.on('SIGTERM', () => { logger.info('Shutting down...'); process.exit(0); });
process.on('SIGINT',  () => { logger.info('Shutting down...'); process.exit(0); });
process.on('uncaughtException', err => { logger.error('Uncaught exception', { error: err.message, stack: err.stack }); });
process.on('unhandledRejection', err => { logger.error('Unhandled rejection', { error: String(err) }); });

main().catch(err => {
  logger.error('Startup failed', { error: err.message });
  process.exit(1);
});
