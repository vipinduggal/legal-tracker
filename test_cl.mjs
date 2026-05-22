import axios from "axios";
import "dotenv/config";

const token = process.env.COURTLISTENER_TOKEN;
const headers = { "Authorization": `Token ${token}` };

// Test 1: Basic docket search
console.log("Test 1: Basic search for Microsoft...");
try {
  const r = await axios.get("https://www.courtlistener.com/api/rest/v4/dockets/", {
    headers,
    params: { q: "Microsoft", order_by: "-date_filed", page_size: 3 },
    timeout: 15000,
  });
  console.log("Status:", r.status);
  console.log("Count:", r.data.count);
  const results = r.data.results || [];
  results.forEach(d => console.log(" ", d.case_name, d.docket_number, d.court_id));
} catch(e) {
  console.log("Error:", e.response?.status, e.response?.data || e.message);
}

// Test 2: Search without quotes
console.log("\nTest 2: Search without quotes...");
try {
  const r = await axios.get("https://www.courtlistener.com/api/rest/v4/dockets/", {
    headers,
    params: { case_name: "Microsoft", order_by: "-date_filed", page_size: 3 },
    timeout: 15000,
  });
  console.log("Status:", r.status);
  console.log("Count:", r.data.count);
} catch(e) {
  console.log("Error:", e.response?.status, e.response?.data || e.message);
}
