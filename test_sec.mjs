import axios from "axios";
const HEADERS = { "User-Agent": "Consilio Legal Tracker vipin.duggal@consilio.com" };
const r = await axios.get("https://www.sec.gov/Archives/edgar/data/789019/000119312526191507/0001193125-26-191507-index.json", { headers: HEADERS, timeout: 10000 });
const files = r.data.directory?.item || [];
files.forEach(f => console.log(f.name, "-", f.size));
