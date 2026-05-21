// researchOne.js — Research a single account by name or ID
// Usage: node src/jobs/researchOne.js "Microsoft"
//        node src/jobs/researchOne.js microsoft

import 'dotenv/config';
import { ACCOUNTS } from '../config/accounts.js';
import { researchAccount, detectChanges } from '../researcher.js';
import { getResearch, setResearch } from '../db.js';
import { sendAccountUpdateEmail } from '../emailer.js';
import { logger } from '../logger.js';

const query = process.argv[2]?.toLowerCase();

if (!query) {
  console.error('Usage: node src/jobs/researchOne.js "Account Name"');
  process.exit(1);
}

const account = ACCOUNTS.find(a =>
  a.id === query ||
  a.id.includes(query) ||
  a.name.toLowerCase() === query ||
  a.name.toLowerCase().includes(query) ||
  a.name.toLowerCase().replace(/[^a-z0-9]/g, '').includes(query.replace(/[^a-z0-9]/g, ''))
);

if (!account) {
  console.error(`No account found matching "${query}"`);
  console.log('Available accounts:', ACCOUNTS.map(a => a.name).join(', '));
  process.exit(1);
}

logger.info(`Manual research triggered for: ${account.name}`);

const oldData = await getResearch(account.id);
const newData = await researchAccount(account);

if (!newData) {
  logger.error('Research failed');
  process.exit(1);
}

const changes = detectChanges(oldData, newData);
await setResearch(account.id, newData);

logger.info(`Research complete for ${account.name}`, { changes });
logger.info('Contacts found:', newData.contacts.map(c => `${c.name} (${c.tag})`));

await sendAccountUpdateEmail(account, changes, newData);
