import axios from "axios";
const HEADERS = { "User-Agent": "Consilio Legal Tracker vipin.duggal@consilio.com" };
const url = "https://www.sec.gov/Archives/edgar/data/789019/000119312526191507/msft-20260331.htm";
const r = await axios.get(url, { headers: HEADERS, timeout: 60000, maxContentLength: 20*1024*1024, responseType: 'text' });
const text = r.data.replace(/<[^>]+>/g, " ").replace(/&nbsp;/g, " ").replace(/&#160;/g, " ").replace(/\s+/g, " ");
const keywords = ["antitrust", "class action", "patent infringement", "FTC", "DOJ", "lawsuit", "litigation", "plaintiff", "defendant", "court", "damages"];
keywords.forEach(k => {
  const idx = text.toLowerCase().indexOf(k.toLowerCase());
  if (idx > -1) console.log(k + " at " + idx + ":", text.slice(Math.max(0,idx-50), idx+200));
  else console.log(k + ": NOT FOUND");
});
