import axios from "axios";
import "dotenv/config";

const token = process.env.COURTLISTENER_TOKEN;
const headers = { "Authorization": `Token ${token}` };

// Check OPTIONS to see valid parameters
console.log("Checking valid docket parameters...");
try {
  const r = await axios.options("https://www.courtlistener.com/api/rest/v4/dockets/", {
    headers, timeout: 10000,
  });
  const filters = r.data?.filters || r.data?.actions?.GET || {};
  console.log("Available filters:", JSON.stringify(Object.keys(filters), null, 2));
} catch(e) {
  console.log("OPTIONS error:", e.message);
}

// Try the search endpoint instead
console.log("\nTrying search endpoint...");
try {
  const r = await axios.get("https://www.courtlistener.com/api/rest/v4/search/", {
    headers,
    params: { q: "Microsoft", type: "d", order_by: "score desc", page_size: 3 },
    timeout: 15000,
  });
  console.log("Status:", r.status);
  console.log("Count:", r.data.count);
  const results = r.data.results || [];
  results.forEach(d => console.log(" ", d.caseName || d.case_name, d.docketNumber || d.docket_number));
} catch(e) {
  console.log("Search error:", e.response?.status, JSON.stringify(e.response?.data)?.slice(0,200) || e.message);
}
