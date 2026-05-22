import axios from "axios";
import "dotenv/config";
const token = process.env.COURTLISTENER_TOKEN;
const r = await axios.get("https://www.courtlistener.com/api/rest/v4/search/", {
  headers: { Authorization: `Token ${token}` },
  params: { q: '"Microsoft"', type: "d", order_by: "score desc", page_size: 3, filed_after: "2025-01-01" },
  timeout: 15000,
});
const results = r.data.results || [];
results.forEach(d => {
  console.log("Case:", d.caseName, d.docketNumber);
  console.log("  attorney:", d.attorney);
  console.log("  firm:", d.firm);
  console.log("  party:", d.party);
  console.log("  suitNature:", d.suitNature);
  console.log("  cause:", d.cause);
  console.log();
});
