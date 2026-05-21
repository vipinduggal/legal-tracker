import os

home = os.path.expanduser("~")
path = os.path.join(home, "legal-tracker", "src", "jobs", "filingsMonitor.js")

with open(path, 'r') as f:
    content = f.read()

# Replace all DOJ feed entries with correct current URLs
# DOJ moved to a new system after Jan 2025 — old /feeds/ paths no longer work
# New RSS feeds are at /news with format=xml parameter

old_feeds = '''const AGENCY_FEEDS = [
  { name: "FTC", url: "https://www.ftc.gov/feeds/press-release.xml", type: "FTC Enforcement Action" },
  { name: "DOJ", url: "https://www.justice.gov/news/rss.xml", type: "DOJ Action" },
  { name: "DOJ2", url: "https://www.justice.gov/opa/pr/rss.xml", type: "DOJ Action" },
  { name: "CFPB", url: "https://www.consumerfinance.gov/about-us/newsroom/feed/", type: "CFPB Action" },
  { name: "SEC", url: "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=8-K&dateb=&owner=include&count=40&search_text=&output=atom", type: "SEC 8-K Filing" },
];'''

new_feeds = '''const AGENCY_FEEDS = [
  { name: "FTC", url: "https://www.ftc.gov/feeds/press-release.xml", type: "FTC Enforcement Action" },
  { name: "DOJ Antitrust", url: "https://www.justice.gov/feeds/justice-news.xml?type=All&component%5B292%5D=292", type: "DOJ Antitrust Action" },
  { name: "DOJ News", url: "https://www.justice.gov/feeds/justice-news.xml", type: "DOJ Action" },
  { name: "CFPB", url: "https://www.consumerfinance.gov/about-us/newsroom/feed/", type: "CFPB Action" },
];'''

# Try to find and replace regardless of exact whitespace
import re
# Match the AGENCY_FEEDS const regardless of content
pattern = r'const AGENCY_FEEDS = \[[\s\S]*?\];'
if re.search(pattern, content):
    content = re.sub(pattern, new_feeds, content, count=1)
    print("Done — AGENCY_FEEDS replaced with correct URLs")
elif old_feeds in content:
    content = content.replace(old_feeds, new_feeds)
    print("Done — AGENCY_FEEDS replaced (exact match)")
else:
    print("WARNING — AGENCY_FEEDS not found")
    # Try to find it
    idx = content.find("AGENCY_FEEDS")
    if idx > 0:
        print("Found at index", idx, "— context:")
        print(content[idx:idx+300])

with open(path, 'w') as f:
    f.write(content)

print("")
print("Test: node src/jobs/filingsMonitor.js")
print("Should see DOJ Antitrust and DOJ News instead of 404 errors")
