# Legal Account Tracker — Automation Backend

Lightweight Node.js backend that automatically researches 63 corporate legal departments every day, sends Outlook email notifications when accounts update, and delivers a weekly outreach digest with suggested contacts and ready-to-send emails every Monday morning.

---

## What it does

| Job | Schedule | Output |
|-----|----------|--------|
| Daily research | 7 AM every day | Researches all accounts via Claude API, emails you when an account updates |
| Weekly digest | Monday 8 AM | Prioritized outreach list with full emails for top 5 accounts |
| Web dashboard | Always on | `http://localhost:3000` — read-only view of all accounts |

---

## Requirements

- **Node.js 18+** — Download from [nodejs.org](https://nodejs.org)
- **Anthropic API key** — Get one at [console.anthropic.com](https://console.anthropic.com) (~$5–15/month for 63 accounts daily)
- **Outlook app password** — Generate at [account.microsoft.com/security](https://account.microsoft.com/security) under App passwords

---

## Quick start (5 minutes)

```bash
# 1. Install dependencies
npm install

# 2. Run the setup wizard — creates your .env file
npm run setup

# 3. Kick off the first research run (takes ~20-30 min for all 63 accounts)
npm run research:all

# 4. Start the scheduler + dashboard
npm start
```

---

## Running on your desktop (always-on)

### Option A — Windows Task Scheduler (recommended, no extra software)

1. Open Task Scheduler → Create Basic Task
2. Name: "Legal Tracker"
3. Trigger: At startup
4. Action: Start a program
   - Program: `C:\Program Files\nodejs\node.exe`
   - Arguments: `C:\path\to\legal-tracker\src\index.js`
   - Start in: `C:\path\to\legal-tracker`
5. Conditions: Uncheck "Start only if AC power"
6. Settings: Check "Restart if task fails"

The dashboard will be at `http://localhost:3000` whenever your computer is on.

### Option B — PM2 (keeps it running, auto-restarts on crash)

```bash
npm install -g pm2
pm2 start src/index.js --name legal-tracker
pm2 startup   # auto-start on Windows boot
pm2 save
```

### Option C — Windows Service (most reliable, runs even when not logged in)

```bash
npm install -g node-windows
# Then run the included install-service script:
node scripts/install-service.js
```

---

## Manual commands

```bash
# Research all accounts now (ignores staleness check)
npm run research:all -- --force

# Research a single account
npm run research:account "Microsoft"
npm run research:account "pge"

# Send weekly digest now (useful for testing)
npm run digest:weekly

# View logs
cat logs/combined.log
cat logs/error.log
```

---

## Configuration (.env)

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Your Claude API key | required |
| `EMAIL_HOST` | SMTP host | `smtp.office365.com` |
| `EMAIL_USER` | Your Outlook address | required |
| `EMAIL_PASS` | App password (not your login password) | required |
| `EMAIL_TO` | Who receives notifications | same as EMAIL_USER |
| `TEAMS_WEBHOOK_URL` | Teams Incoming Webhook URL | optional |
| `RESEARCH_CRON` | Daily research schedule | `0 7 * * *` (7 AM) |
| `DIGEST_CRON` | Weekly digest schedule | `0 8 * * 1` (Mon 8 AM) |
| `RESEARCH_CONCURRENCY` | Parallel API calls | `3` |
| `RESEARCH_STALE_DAYS` | Days before re-researching | `1` |

---

## Adding accounts

Edit `config/accounts.js` and add a new entry:

```js
{ id: "new_company", name: "New Company", industry: "Technology", location: "Austin, TX" },
```

The next research run will pick it up automatically.

---

## Data storage

All research data is stored locally in `data/db.json`. This file is your entire database — back it up or commit it to git. It contains:

- All research data for all accounts
- Last-updated timestamps
- Weekly digest history (last 52 weeks)
- Run audit log

---

## Cost estimate

| Scenario | Daily cost | Monthly cost |
|----------|-----------|--------------|
| 63 accounts, light research | ~$0.25 | ~$7.50 |
| 63 accounts, deep research | ~$0.50 | ~$15 |
| Weekly digest only | ~$0.10 | ~$0.40 |

---

## Troubleshooting

**Email not sending:**
- Make sure you're using an app password, not your regular Outlook password
- Check that 2FA is enabled on your Microsoft account (required for app passwords)
- Test with: `node -e "import('./src/emailer.js').then(m => console.log('loaded'))"`

**API errors:**
- Check your API key at console.anthropic.com
- Check rate limits — if you see 429 errors, increase `RESEARCH_CONCURRENCY` wait time or reduce `RESEARCH_CONCURRENCY`
- Check logs: `tail -f logs/combined.log`

**Research looks wrong:**
- Claude's research is based on publicly available information and may occasionally be imprecise
- Use the "Research [account]" buttons in the Claude.ai tracker to spot-check
- You can always manually edit `data/db.json`

---

## Architecture

```
src/
  index.js          ← entry point, starts cron + server
  researcher.js     ← calls Anthropic API, parses research
  emailer.js        ← sends Outlook notifications
  teams.js          ← posts to Teams webhook
  db.js             ← JSON file database (lowdb)
  logger.js         ← Winston logging
  prompts.js        ← research + digest prompt templates
  server.js         ← Express API + web dashboard
  jobs/
    researchAll.js  ← daily job: research all accounts
    researchOne.js  ← manual: research one account
    weeklyDigest.js ← Monday job: outreach digest
config/
  accounts.js       ← all 63 accounts
data/
  db.json           ← all research data (auto-created)
logs/
  combined.log      ← all logs
  error.log         ← errors only
```
