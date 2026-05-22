import os

home = os.path.expanduser("~")
path = os.path.join(home, "legal-tracker", "src", "jobs", "secFilingsPuller.js")

with open(path, 'r') as f:
    content = f.read()

# Replace the extractLegalProceedings function entirely
old_fn = '''// Download and extract Legal Proceedings section from a filing
async function extractLegalProceedings(filing) {
  try {
    const accNo = filing.accessionNumber.replace(/-/g, "");
    const cikInt = parseInt(filing.cik).toString();

    // Build direct URL to primary document
    const docUrl = `https://www.sec.gov/Archives/edgar/data/${cikInt}/${accNo}/${filing.primaryDocument}`;

    const response = await axios.get(docUrl, {
      headers: HEADERS,
      timeout: 60000,
      maxContentLength: 20 * 1024 * 1024, // 20MB limit
      responseType: 'text',
    });

    const html = response.data || "";

    // Extract Legal Proceedings section
    // SEC filings use standardized section headers
    const legalSection = extractSection(html, [
      "LEGAL PROCEEDINGS",
      "Legal Proceedings",
      "ITEM 3",
      "Item 3.",
    ]);

    if (!legalSection) return null;

    return {
      form: filing.form,
      date: filing.date,
      content: legalSection.slice(0, 8000), // Limit size
      url: docUrl,
    };
  } catch(err) {
    logger.warn(`Failed to download filing: ${err.message}`);
    return null;
  }
}'''

new_fn = '''// Download and extract Legal Proceedings section from a filing
async function extractLegalProceedings(filing) {
  try {
    const accNo = filing.accessionNumber.replace(/-/g, "");
    const cikInt = parseInt(filing.cik).toString();
    const docUrl = `https://www.sec.gov/Archives/edgar/data/${cikInt}/${accNo}/${filing.primaryDocument}`;

    const response = await axios.get(docUrl, {
      headers: HEADERS,
      timeout: 60000,
      maxContentLength: 25 * 1024 * 1024,
      responseType: "text",
    });

    const html = response.data || "";

    // Clean HTML thoroughly
    const text = html
      .replace(/<style[^>]*>[\s\\S]*?<\\/style>/gi, "")
      .replace(/<script[^>]*>[\s\\S]*?<\\/script>/gi, "")
      .replace(/<[^>]+>/g, " ")
      .replace(/&nbsp;/g, " ")
      .replace(/&#160;/g, " ")
      .replace(/&amp;/g, "&")
      .replace(/&lt;/g, "<")
      .replace(/&gt;/g, ">")
      .replace(/&#8217;/g, "'")
      .replace(/&#8212;/g, "—")
      .replace(/&#[0-9]+;/g, " ")
      .replace(/\\s+/g, " ")
      .trim();

    // Strategy 1: Find "Other Contingencies" section which has dollar amounts
    const contingIdx = text.indexOf("Other Contingencies");
    if (contingIdx > -1) {
      const section = text.slice(Math.max(0, contingIdx - 500), contingIdx + 3000);
      if (section.includes("accrued") || section.includes("million") || section.includes("claims")) {
        logger.info("  Found contingencies section with financial data");
        return {
          form: filing.form,
          date: filing.date,
          content: section,
          url: docUrl,
          section_type: "contingencies",
        };
      }
    }

    // Strategy 2: Find legal proceedings by searching for multiple legal keywords
    // and extracting the surrounding context
    const legalKeywords = ["antitrust", "class action", "patent infringement", "GDPR",
      "regulatory action", "legal proceedings", "plaintiff", "defendant"];

    const hits = [];
    for (const kw of legalKeywords) {
      const idx = text.toLowerCase().indexOf(kw.toLowerCase());
      if (idx > -1) hits.push({ keyword: kw, position: idx });
    }

    if (hits.length > 0) {
      // Sort by position and extract a wide window around all hits
      hits.sort((a, b) => a.position - b.position);
      const firstHit = hits[0].position;
      const lastHit = hits[hits.length - 1].position;

      // Find the start of the section (look back for Item 3 header)
      const sectionStart = Math.max(0, firstHit - 1000);
      const sectionEnd = Math.min(text.length, lastHit + 3000);
      const section = text.slice(sectionStart, sectionEnd);

      if (section.length > 200) {
        return {
          form: filing.form,
          date: filing.date,
          content: section.slice(0, 8000),
          url: docUrl,
          section_type: "legal_proceedings",
        };
      }
    }

    logger.warn(`  No legal proceedings content found in ${filing.form} for ${docUrl}`);
    return null;

  } catch(err) {
    logger.warn(`Failed to download filing: ${err.message}`);
    return null;
  }
}'''

if old_fn in content:
    content = content.replace(old_fn, new_fn)
    print("Done — extractLegalProceedings rewritten")
else:
    print("Pattern not found")

with open(path, 'w') as f:
    f.write(content)
