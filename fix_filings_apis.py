import os, re

home = os.path.expanduser("~")
path = os.path.join(home, "legal-tracker", "src", "jobs", "filingsMonitor.js")

with open(path, 'r') as f:
    content = f.read()

# Fix 1: CourtListener — add API token support
# They require a free account token now
# Get one free at courtlistener.com/sign-in/
old_court = '''async function checkCourtListener(account, daysSince = 7) {
  try {
    const since = new Date();
    since.setDate(since.getDate() - daysSince);
    const sinceStr = since.toISOString().split("T")[0];

    const searchTerm = getSearchTerms(account);
    const url = "https://www.courtlistener.com/api/rest/v3/dockets/";
    const params = {
      q: `"${searchTerm}"`,
      filed_after: sinceStr,
      order_by: "-date_filed",
      page_size: 5,
      format: "json",
    };

    const response = await axios.get(url, {
      params,
      headers: { "User-Agent": "LegalTracker/1.0 vipin.duggal@consilio.com" },
      timeout: 10000,
    });'''

new_court = '''async function checkCourtListener(account, daysSince = 7) {
  // CourtListener requires a free API token
  // Sign up at courtlistener.com/sign-in/ and add COURTLISTENER_TOKEN to .env
  const token = process.env.COURTLISTENER_TOKEN;
  if (!token) {
    // Skip silently if no token — don't spam logs
    return [];
  }

  try {
    const since = new Date();
    since.setDate(since.getDate() - daysSince);
    const sinceStr = since.toISOString().split("T")[0];

    const searchTerm = getSearchTerms(account);
    const url = "https://www.courtlistener.com/api/rest/v3/dockets/";
    const params = {
      q: `"${searchTerm}"`,
      filed_after: sinceStr,
      order_by: "-date_filed",
      page_size: 5,
      format: "json",
    };

    const response = await axios.get(url, {
      params,
      headers: {
        "User-Agent": "LegalTracker/1.0 vipin.duggal@consilio.com",
        "Authorization": "Token " + token,
      },
      timeout: 10000,
    });'''

if old_court in content:
    content = content.replace(old_court, new_court)
    print("Done — CourtListener updated to use token")
else:
    print("WARNING — CourtListener pattern not found")

# Fix 2: Update agency feed URLs
old_feeds = '''const AGENCY_FEEDS = [
  { name: "FTC", url: "https://www.ftc.gov/feeds/press-release.xml", type: "FTC Enforcement Action" },
  { name: "DOJ", url: "https://www.justice.gov/feeds/opa/justice-news.xml", type: "DOJ Action" },
  { name: "CFPB", url: "https://www.consumerfinance.gov/about-us/newsroom/feed/", type: "CFPB Action" },
];'''

new_feeds = '''const AGENCY_FEEDS = [
  { name: "FTC", url: "https://www.ftc.gov/feeds/press-release.xml", type: "FTC Enforcement Action" },
  { name: "DOJ", url: "https://www.justice.gov/news/rss.xml", type: "DOJ Action" },
  { name: "DOJ2", url: "https://www.justice.gov/opa/pr/rss.xml", type: "DOJ Action" },
  { name: "CFPB", url: "https://www.consumerfinance.gov/about-us/newsroom/feed/", type: "CFPB Action" },
  { name: "SEC", url: "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=8-K&dateb=&owner=include&count=40&search_text=&output=atom", type: "SEC 8-K Filing" },
];'''

if old_feeds in content:
    content = content.replace(old_feeds, new_feeds)
    print("Done — DOJ feed URL updated, SEC feed added")
else:
    print("WARNING — feeds pattern not found")

with open(path, 'w') as f:
    f.write(content)

print("")
print("="*50)
print("CourtListener setup (one-time, free):")
print("  1. Go to courtlistener.com/sign-in/ and create free account")
print("  2. Go to courtlistener.com/profile/tokens/")
print("  3. Create a token and copy it")
print("  4. Add to .env: COURTLISTENER_TOKEN=your-token-here")
print("  5. Run: pm2 restart legal-tracker")
print("")
print("Without the token, EDGAR + FTC + DOJ + CFPB still run.")
print("CourtListener just skips silently instead of spamming errors.")
print("")
print("Test: node src/jobs/filingsMonitor.js")
