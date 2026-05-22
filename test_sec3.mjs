import axios from "axios";
const HEADERS = { "User-Agent": "Consilio Legal Tracker vipin.duggal@consilio.com" };

// Search specifically for Microsoft's recent filings with legal proceedings text
const url = "https://efts.sec.gov/LATEST/search-index?q=%22legal+proceedings%22&dateRange=custom&startdt=2026-01-01&enddt=2026-05-22&forms=10-Q&entity=microsoft";
console.log("URL:", url);
const r = await axios.get(url, { headers: HEADERS, timeout: 15000 });
const hits = r.data?.hits?.hits || [];
console.log("Hits:", hits.length);
hits.slice(0,3).forEach(h => {
  console.log("  File date:", h._source?.file_date);
  console.log("  Entity:", h._source?.display_names);
  console.log("  ID:", h._id);
  if (h.highlight) console.log("  Snippet:", JSON.stringify(h.highlight).slice(0,200));
});
