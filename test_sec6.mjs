import axios from "axios";
const HEADERS = { "User-Agent": "Consilio Legal Tracker vipin.duggal@consilio.com" };
const url = "https://www.sec.gov/Archives/edgar/data/789019/000119312526191507/msft-20260331.htm";
const r = await axios.get(url, { headers: HEADERS, timeout: 60000, maxContentLength: 20*1024*1024, responseType: 'text' });
const text = r.data.replace(/<[^>]+>/g, " ").replace(/&nbsp;/g, " ").replace(/&#160;/g, " ").replace(/\s+/g, " ");

// Extract around the LinkedIn/court mention and the antitrust section
console.log("=== LINKEDIN/COURT SECTION ===");
console.log(text.slice(85200, 86500));
console.log("\n=== ANTITRUST SECTION ===");
console.log(text.slice(209500, 211000));
console.log("\n=== CONTINGENCIES SECTION ===");
const contIdx = text.indexOf("Other Contingencies");
if (contIdx > -1) console.log(text.slice(contIdx, contIdx + 2000));
