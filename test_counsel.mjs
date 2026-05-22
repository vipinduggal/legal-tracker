import "dotenv/config";
import axios from "axios";

const token = process.env.COURTLISTENER_TOKEN;
const r = await axios.get("https://www.courtlistener.com/api/rest/v4/search/", {
  headers: { Authorization: `Token ${token}` },
  params: { q: '"Microsoft"', type: "d", order_by: "score desc", page_size: 5, filed_after: "2026-01-01" },
  timeout: 15000,
});

r.data.results.forEach(d => {
  const caseName = d.caseName || "";
  const vIndex = caseName.toLowerCase().indexOf(" v. ");
  const afterV = vIndex > -1 ? caseName.slice(vIndex + 4).toLowerCase() : "";
  const beforeV = vIndex > -1 ? caseName.slice(0, vIndex).toLowerCase() : "";
  const isDefendant = afterV.includes("microsoft");
  
  console.log("Case:", caseName);
  console.log("  After v.:", afterV);
  console.log("  isDefendant:", isDefendant);
  console.log("  Firms:", d.firm);
  console.log();
});
