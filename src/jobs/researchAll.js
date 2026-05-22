// researchAll.js — Daily job: research all accounts, notify on changes

import 'dotenv/config';
import pLimit from 'p-limit';
import { ACCOUNTS } from '../config/accounts.js';
import { researchAccount, detectChanges } from '../researcher.js';
import { getResearch, setResearch, isStale, logRun } from '../db.js';
import { sendAccountNotification } from '../emailer.js';
import { postAccountUpdateToTeams } from '../teams.js';
import { logger } from '../logger.js';

const CONCURRENCY = parseInt(process.env.RESEARCH_CONCURRENCY) || 3;
const STALE_DAYS = parseFloat(process.env.RESEARCH_STALE_DAYS) || 1;

export async function runDailyResearch(forceAll = false) {
  const startTime = Date.now();
  logger.info(`=== Daily research job started — ${ACCOUNTS.length} accounts, concurrency ${CONCURRENCY} ===`);

  const limit = pLimit(CONCURRENCY);
  const results = { success: 0, skipped: 0, failed: 0, notified: 0 };

  const tasks = ACCOUNTS.map(account =>
    limit(async () => {
      try {
        // Skip if recently researched (unless forced)
        if (!forceAll && !(await isStale(account.id, STALE_DAYS))) {
          logger.debug(`Skipping (fresh): ${account.name}`);
          results.skipped++;
          return;
        }

        const oldData = await getResearch(account.id);
        const newData = await researchAccount(account);

        if (!newData) {
          results.failed++;
          return;
        }

        const changes = detectChanges(oldData, newData);
        await setResearch(account.id, newData);
        results.success++;

        // Only notify if there are meaningful changes (or it's first research)
        const hasRealChanges = !oldData || changes.some(c => !c.includes('No significant changes'));

        if (hasRealChanges) {
          results.notified++;
          await Promise.allSettled([
            sendAccountNotification(account, changes, newData),
            postAccountUpdateToTeams(account, changes, newData),
          ]);
        }

        // Small delay between accounts to be respectful of rate limits
        await sleep(500);

      } catch (err) {
        logger.error(`Unexpected error for ${account.name}`, { error: err.message });
        results.failed++;
      }
    })
  );

  await Promise.allSettled(tasks);

  const duration = Math.round((Date.now() - startTime) / 1000);
  logger.info(`=== Daily research complete in ${duration}s ===`, results);

  await logRun({
    job: 'daily_research',
    duration,
    ...results,
  });

  return results;
}

// Allow direct execution: node src/jobs/researchAll.js [--force]
if (process.argv[1].endsWith('researchAll.js')) {
  const force = process.argv.includes('--force');
  runDailyResearch(force).catch(err => {
    logger.error('Fatal error in daily research', { error: err.message });
    process.exit(1);
  });
}

function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}
