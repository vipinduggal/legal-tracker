// weeklyDigest.js — Monday job: generate outreach plan, email + Teams

import 'dotenv/config';
import Anthropic from '@anthropic-ai/sdk';
import { ACCOUNTS } from '../config/accounts.js';
import { getAllResearch, saveDigest, logRun } from '../db.js';
import { buildWeeklyDigestPrompt } from '../prompts.js';
import { sendWeeklyDigestEmail } from '../emailer.js';
import { postWeeklyDigestToTeams } from '../teams.js';
import { logger } from '../logger.js';

const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

export async function runWeeklyDigest() {
  const startTime = Date.now();
  logger.info('=== Weekly digest job started ===');

  // Load all research data
  const allResearch = await getAllResearch();
  const researchedAccounts = ACCOUNTS.filter(a => allResearch[a.id]);

  if (researchedAccounts.length === 0) {
    logger.warn('No researched accounts found — run daily research first');
    return null;
  }

  logger.info(`Generating digest from ${researchedAccounts.length} researched accounts`);

  const prompt = buildWeeklyDigestPrompt(researchedAccounts, allResearch);

  try {
    const response = await client.messages.create({
      model: 'claude-sonnet-4-5',
      max_tokens: 6000,
      messages: [{ role: 'user', content: prompt }],
    });

    const raw = response.content
      .filter(b => b.type === 'text')
      .map(b => b.text)
      .join('');

    const cleaned = raw
      .replace(/^```json\s*/i, '')
      .replace(/^```\s*/i, '')
      .replace(/```\s*$/i, '')
      .trim();

    const digest = JSON.parse(cleaned);

    // Save digest to DB
    await saveDigest(digest);

    logger.info('Digest generated', {
      priority_accounts: digest.priority_accounts?.length || 0,
      quick_touches: digest.quick_touches?.length || 0,
    });

    // Send notifications
    await Promise.allSettled([
      sendWeeklyDigestEmail(digest),
      postWeeklyDigestToTeams(digest),
    ]);

    const duration = Math.round((Date.now() - startTime) / 1000);
    await logRun({ job: 'weekly_digest', duration, accounts: researchedAccounts.length });

    return digest;

  } catch (err) {
    logger.error('Weekly digest failed', { error: err.message });
    await logRun({ job: 'weekly_digest', error: err.message });
    return null;
  }
}

// Allow direct execution
if (process.argv[1].endsWith('weeklyDigest.js')) {
  runWeeklyDigest().catch(err => {
    logger.error('Fatal error in weekly digest', { error: err.message });
    process.exit(1);
  });
}
