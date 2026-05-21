// teams.js — Posts updates to Microsoft Teams via Incoming Webhook

import axios from 'axios';
import { logger } from './logger.js';
import { format } from 'date-fns';

/**
 * Post an account update card to Teams.
 */
export async function postAccountUpdateToTeams(account, changes, researchData) {
  const url = process.env.TEAMS_WEBHOOK_URL;
  if (!url) return false;

  const activeIssues = [
    ...(researchData.litigation || []).filter(l => l.status !== 'Resolved' && l.status !== 'Settled'),
    ...(researchData.regulatory || []).filter(r => r.status !== 'Resolved' && r.status !== 'Closed'),
  ];

  const card = {
    '@type': 'MessageCard',
    '@context': 'http://schema.org/extensions',
    themeColor: '0078D4',
    summary: `${account.name} research updated`,
    sections: [
      {
        activityTitle: `📋 **${account.name}** — Research Updated`,
        activitySubtitle: `${account.industry} · ${format(new Date(), 'MMM d, yyyy h:mm a')}`,
        activityText: changes.join(' · '),
        facts: [
          { name: 'Contacts', value: String((researchData.contacts || []).length) },
          { name: 'Active issues', value: String(activeIssues.length) },
          { name: 'Outside counsel', value: (researchData.counsel || []).slice(0, 2).join(', ') || 'Unknown' },
        ],
      },
      ...(researchData.intel_summary ? [{
        text: `💡 **Sales intel:** ${researchData.intel_summary}`,
      }] : []),
    ],
  };

  try {
    await axios.post(url, card);
    logger.info(`Teams notification sent for ${account.name}`);
    return true;
  } catch (err) {
    logger.error(`Teams notification failed for ${account.name}`, { error: err.message });
    return false;
  }
}

/**
 * Post the weekly digest to Teams.
 */
export async function postWeeklyDigestToTeams(digest) {
  const url = process.env.TEAMS_WEBHOOK_URL;
  if (!url) return false;

  const priorities = digest.priority_accounts || [];
  const date = format(new Date(), 'MMMM d, yyyy');

  const card = {
    '@type': 'MessageCard',
    '@context': 'http://schema.org/extensions',
    themeColor: '107C10',
    summary: `Weekly outreach digest — ${date}`,
    sections: [
      {
        activityTitle: `📬 **Weekly Outreach Digest** — ${date}`,
        activitySubtitle: digest.week_summary || '',
        facts: priorities.slice(0, 5).map((p, i) => ({
          name: `#${i + 1} ${p.account_name}`,
          value: p.reason,
        })),
      },
    ],
    potentialAction: [],
  };

  try {
    await axios.post(url, card);
    logger.info('Teams weekly digest posted');
    return true;
  } catch (err) {
    logger.error('Teams weekly digest failed', { error: err.message });
    return false;
  }
}
