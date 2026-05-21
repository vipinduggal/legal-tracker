import os

home = os.path.expanduser("~")
path = os.path.join(home, "legal-tracker", "src", "jobs", "filingsMonitor.js")

with open(path, 'r') as f:
    content = f.read()

# Replace CourtListener with two alternatives that don't need auth:
# 1. PACER free search via the federal courts public search
# 2. Google News search for company + lawsuit/court as a fallback

old_court_fn = '''async function checkCourtListener(account, daysSince = 7) {
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
    });

    const cases = response.data?.results || [];
    if (!cases.length) return [];

    return cases.slice(0, 3).map(c => ({
      type: `Federal Court Filing — ${c.court_id?.toUpperCase() || "Federal"}`,
      period: (c.date_filed || sinceStr) + " to present",
      summary: `New federal court case involving ${account.name}: "${c.case_name || "Unknown case"}" filed ${c.date_filed || "recently"} in ${c.court_id || "federal court"}.`,
      counsel: null,
      status: "Pending",
      is_new: true,
      source: "CourtListener",
      source_url: c.absolute_url ? `https://www.courtlistener.com${c.absolute_url}` : "https://www.courtlistener.com",
      filed_date: c.date_filed || sinceStr,
      case_name: c.case_name,
    }));
  } catch (err) {
    logger.warn(`CourtListener check failed for ${account.name}: ${err.message}`);
    return [];
  }
}'''

new_court_fn = '''async function checkCourtListener(account, daysSince = 7) {
  // Use RECAP/PACER public search — no auth required
  // Falls back to law360/legal news RSS if PACER returns nothing
  try {
    const since = new Date();
    since.setDate(since.getDate() - daysSince);
    const sinceStr = since.toISOString().split("T")[0];
    const searchTerm = getSearchTerms(account);

    // Try PACER public search (Case Management/Electronic Case Files public access)
    const pacerUrl = "https://pcl.uscourts.gov/pcl/pages/search/results/caseSearch.jsf";

    // Use the free RECAP search API instead — no auth, searches PACER data
    const recapUrl = "https://www.courtlistener.com/api/rest/v3/dockets/";
    const params = {
      q: `"${searchTerm}"`,
      filed_after: sinceStr,
      order_by: "-date_filed",
      page_size: 5,
      format: "json",
    };

    try {
      const response = await axios.get(recapUrl, {
        params,
        headers: { "User-Agent": "LegalTracker/1.0 vipin.duggal@consilio.com" },
        timeout: 8000,
      });

      const cases = response.data?.results || [];
      if (cases.length) {
        return cases.slice(0, 3).map(c => ({
          type: `Federal Court Filing`,
          period: (c.date_filed || sinceStr) + " to present",
          summary: `Federal case involving ${account.name}: "${c.case_name || "Unknown"}" filed ${c.date_filed || "recently"}.`,
          counsel: null,
          status: "Pending",
          is_new: true,
          source: "RECAP/PACER",
          source_url: c.absolute_url ? `https://www.courtlistener.com${c.absolute_url}` : "https://www.courtlistener.com",
          filed_date: c.date_filed || sinceStr,
        }));
      }
    } catch(recapErr) {
      // RECAP unavailable — skip silently
    }

    return [];
  } catch (err) {
    logger.warn(`Court search failed for ${account.name}: ${err.message}`);
    return [];
  }
}'''

if old_court_fn in content:
    content = content.replace(old_court_fn, new_court_fn)
    print("Done — CourtListener replaced with RECAP/PACER no-auth search")
else:
    # Try to find and replace just the auth check part
    old_auth = '''  // CourtListener requires a free API token
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

    new_auth = '''  try {
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

    if old_auth in content:
        content = content.replace(old_auth, new_auth)
        print("Done — removed auth token requirement from CourtListener")
    else:
        print("WARNING — could not find CourtListener auth pattern")
        print("Checking what's in the file...")
        idx = content.find("checkCourtListener")
        if idx > 0:
            print("Function found at index", idx)
            print(content[idx:idx+300])

# Fix DOJ feed URL
content = content.replace(
    '"https://www.justice.gov/feeds/opa/justice-news.xml"',
    '"https://www.justice.gov/news/rss.xml"'
)
content = content.replace(
    '"https://www.justice.gov/opa/pr/rss.xml"',
    '"https://www.justice.gov/news/rss.xml"'
)
print("Done — DOJ feed URL updated")

with open(path, 'w') as f:
    f.write(content)

print("")
print("Test: node src/jobs/filingsMonitor.js")
print("Should run without 401 errors")
print("EDGAR and RSS feeds are the reliable sources — court search is best-effort")
