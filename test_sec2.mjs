import axios from "axios";
const HEADERS = { "User-Agent": "Consilio Legal Tracker vipin.duggal@consilio.com" };

// Use EDGAR full text search to find legal proceedings directly
const r = await axios.get(
  "https://efts.sec.gov/LATEST/search-index?q=%22legal+proceedings%22+%22microsoft%22&dateRange=custom&startdt=2026-01-01&forms=10-Q&hits.hits._source=period_of_report,file_date,display_names,form_type",
  { headers: HEADERS, timeout: 15000 }
);

const hits = r.data?.hits?.hits || [];
console.log("Hits:", hits.length);
hits.slice(0,3).forEach(h => {
  console.log("  ", h._source?.period_of_report, h._source?.file_date, h._source?.display_names);
  console.log("   ID:", h._id);
});
