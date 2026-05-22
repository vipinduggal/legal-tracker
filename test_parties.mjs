import axios from "axios";
import "dotenv/config";
const token = process.env.COURTLISTENER_TOKEN;

// Get Beaulier v Microsoft docket details to see party roles
const r = await axios.get("https://www.courtlistener.com/api/rest/v4/dockets/72509053/", {
  headers: { Authorization: `Token ${token}` },
  params: { fields: "case_name,parties" },
  timeout: 10000,
});

console.log("Case:", r.data.case_name);
const parties = r.data.parties || [];
parties.forEach(p => {
  console.log("\nParty:", p.name);
  console.log("  Type:", p.party_types?.map(pt => pt.name).join(", "));
  console.log("  Attorneys:", p.attorneys?.map(a => `${a.name} (${a.contact_raw?.split("\n")[0]})`).join(", "));
});
