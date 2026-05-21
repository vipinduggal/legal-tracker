import os

home = os.path.expanduser("~")
base = os.path.join(home, "legal-tracker")
server_path = os.path.join(base, "src", "server.js")

content = """import express from 'express';
import { ACCOUNTS } from '../config/accounts.js';
import { getAllResearch, getLatestDigest, db } from './db.js';
import { logger } from './logger.js';
import { registerAccountRoutes } from './accountRoutes.js';

const app = express();
app.use(express.json());

app.get('/api/accounts', async (req, res) => {
  const allResearch = await getAllResearch();
  const data = ACCOUNTS.map(a => ({
    ...a,
    hasData: !!allResearch[a.id],
    lastUpdated: db.data.lastUpdated?.[a.id] || null,
    contactCount: allResearch[a.id]?.contacts?.length || 0,
    activeIssues: [
      ...(allResearch[a.id]?.litigation || []).filter(l => !['Resolved','Settled','Dismissed'].includes(l.status)),
      ...(allResearch[a.id]?.regulatory || []).filter(r => !['Resolved','Closed'].includes(r.status)),
    ].length,
  }));
  res.json(data);
});

app.get('/api/accounts/:id', async (req, res) => {
  const account = ACCOUNTS.find(a => a.id === req.params.id);
  if (!account) return res.status(404).json({ error: 'Not found' });
  const allResearch = await getAllResearch();
  res.json({ ...account, lastUpdated: db.data.lastUpdated?.[account.id] || null, research: allResearch[account.id] || null });
});

app.get('/api/digest', async (req, res) => {
  const digest = await getLatestDigest();
  res.json(digest || { message: 'No digest yet' });
});

app.get('/api/status', async (req, res) => {
  await db.read();
  const allResearch = await getAllResearch();
  const researched = Object.keys(allResearch).length;
  res.json({ status: 'ok', accounts: ACCOUNTS.length, researched, pending: ACCOUNTS.length - researched, recentRuns: (db.data.runs || []).slice(0, 5) });
});

registerAccountRoutes(app);

app.get('/', (req, res) => res.send(getDash()));

export function startServer() {
  const port = process.env.PORT || 3000;
  app.listen(port, () => logger.info('Dashboard at http://localhost:' + port));
  return app;
}

"""

# Build the HTML dashboard as a Python string, then write it as a JS const
# Using repr() to safely encode everything

html_parts = []
html_parts.append("<!DOCTYPE html>")
html_parts.append("<html lang='en'>")
html_parts.append("<head>")
html_parts.append("<meta charset='utf-8'>")
html_parts.append("<meta name='viewport' content='width=device-width,initial-scale=1'>")
html_parts.append("<title>Legal Account Tracker</title>")
html_parts.append("<link href='https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&family=DM+Mono&display=swap' rel='stylesheet'>")
html_parts.append("""<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{--navy:#0F2240;--blue:#1E56A0;--bl:#EBF2FC;--teal:#0A7C6E;--tl:#E6F5F2;--amber:#B45309;--al:#FEF3C7;--red:#991B1B;--rl:#FEE2E2;--green:#166534;--gl:#DCFCE7;--g0:#F9FAFB;--g1:#F3F4F6;--g2:#E5E7EB;--g4:#9CA3AF;--g5:#6B7280;--g6:#4B5563;--g7:#374151;--g9:#111827;--f:"DM Sans",sans-serif;--mono:"DM Mono",monospace;--r:10px;--rl:14px}
body{font-family:var(--f);font-size:14px;color:var(--g9);background:var(--g0);height:100vh;overflow:hidden;display:flex;flex-direction:column}
.topbar{height:52px;background:var(--navy);display:flex;align-items:center;padding:0 20px;gap:12px;flex-shrink:0}
.topbar .title{font-size:15px;font-weight:600;color:#fff}
.topbar .sub{font-size:12px;color:rgba(255,255,255,.4)}
.topbar .right{margin-left:auto;display:flex;align-items:center;gap:8px}
.tstat{font-size:12px;color:rgba(255,255,255,.55);display:flex;align-items:center;gap:5px}
.tstat strong{color:rgba(255,255,255,.9)}
.tdiv{width:1px;height:16px;background:rgba(255,255,255,.12)}
.live-dot{width:7px;height:7px;border-radius:50%;background:#34D399}
.tnav{font-size:12px;color:rgba(255,255,255,.8);text-decoration:none;padding:5px 11px;border:1px solid rgba(255,255,255,.25);border-radius:6px;font-weight:500;transition:all .12s}
.tnav:hover{background:rgba(255,255,255,.1);color:#fff}
.tnav-dim{font-size:11px;color:rgba(255,255,255,.5);text-decoration:none;padding:4px 8px;border:1px solid rgba(255,255,255,.12);border-radius:5px}
.tnav-dim:hover{color:rgba(255,255,255,.8)}
.layout{display:flex;flex:1;overflow:hidden}
.sidebar{width:240px;background:#fff;border-right:1px solid var(--g2);display:flex;flex-direction:column;overflow:hidden}
.sb-search{padding:10px}
.sb-box{display:flex;align-items:center;gap:7px;background:var(--g0);border:1px solid var(--g2);border-radius:var(--r);padding:6px 10px}
.sb-box input{border:none;background:none;outline:none;font-size:12px;color:var(--g7);font-family:var(--f);width:100%}
.sb-box input::placeholder{color:var(--g4)}
.acct-list{flex:1;overflow-y:auto;padding:4px 8px 8px}
.ai{display:flex;align-items:center;gap:8px;padding:7px 9px;border-radius:var(--r);cursor:pointer;border:1px solid transparent;margin-bottom:1px;transition:all .12s}
.ai:hover{background:var(--g0);border-color:var(--g2)}
.ai.active{background:var(--bl);border-color:#BFCFE8}
.aav{width:27px;height:27px;border-radius:6px;display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:600;flex-shrink:0}
.an{font-size:12px;font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:var(--g7)}
.ai.active .an{color:var(--blue)}
.as{font-size:10px;color:var(--g4);margin-top:1px}
.main{flex:1;display:flex;flex-direction:column;overflow:hidden;min-width:0}
.no-acct{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:8px;color:var(--g4)}
.ah{padding:14px 20px 0;border-bottom:1px solid var(--g2);flex-shrink:0}
.ah-top{display:flex;align-items:flex-start;margin-bottom:12px}
.ah-left{display:flex;align-items:center;gap:11px}
.hav{width:38px;height:38px;border-radius:9px;display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:600;flex-shrink:0}
.hn{font-size:17px;font-weight:600;color:var(--g9);letter-spacing:-.02em}
.hm{font-size:11px;color:var(--g5);margin-top:2px;display:flex;align-items:center;gap:6px;flex-wrap:wrap}
.badge{display:inline-flex;align-items:center;font-size:10px;font-weight:500;padding:2px 7px;border-radius:20px}
.bg{background:var(--gl);color:var(--green)}
.ba{background:var(--al);color:var(--amber)}
.br{background:var(--rl);color:var(--red)}
.bb{background:var(--bl);color:var(--blue)}
.tabs{display:flex;overflow-x:auto;scrollbar-width:none;margin-top:2px}
.tabs::-webkit-scrollbar{display:none}
.tab{padding:8px 13px;font-size:12px;font-weight:500;cursor:pointer;border-bottom:2px solid transparent;color:var(--g5);white-space:nowrap;transition:all .12s;display:flex;align-items:center;gap:4px}
.tab:hover{color:var(--g7)}
.tab.active{color:var(--blue);border-bottom-color:var(--blue)}
.tc{font-size:10px;padding:1px 5px;border-radius:10px;background:var(--g1);color:var(--g5)}
.tab.active .tc{background:var(--bl);color:var(--blue)}
.ct{flex:1;overflow-y:auto;padding:18px}
.sl{font-size:11px;font-weight:600;color:var(--g4);text-transform:uppercase;letter-spacing:.06em;margin-bottom:9px;display:flex;align-items:center;gap:6px}
.sl::after{content:"";flex:1;height:1px;background:var(--g1)}
.card{background:#fff;border:1px solid var(--g2);border-radius:var(--rl);padding:13px;margin-bottom:9px}
.cg{display:grid;grid-template-columns:repeat(auto-fill,minmax(195px,1fr));gap:9px;margin-bottom:12px}
.cc{background:#fff;border:1px solid var(--g2);border-radius:var(--rl);padding:12px;transition:all .12s}
.cc:hover{box-shadow:0 4px 6px rgba(0,0,0,.07);transform:translateY(-1px)}
.cc-t{display:flex;align-items:center;gap:8px;margin-bottom:7px}
.cav{width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:600;flex-shrink:0}
.cn{font-size:12px;font-weight:600;color:var(--g9);line-height:1.3}
.ct2{font-size:10px;color:var(--g5)}
.cd{font-size:10px;color:var(--g5);display:flex;align-items:center;gap:3px;margin-top:3px}
.cd a{color:var(--blue);text-decoration:none}
.tag{display:inline-block;font-size:10px;font-weight:500;padding:2px 7px;border-radius:20px;margin-bottom:5px}
.t-clo{background:#F0EEFE;color:#5B45C7}
.t-gc{background:var(--bl);color:var(--blue)}
.t-lit{background:var(--al);color:var(--amber)}
.t-ops{background:var(--tl);color:var(--teal)}
.t-def{background:var(--g1);color:var(--g6)}
.conf-h{font-size:10px;color:var(--green);font-weight:500}
.conf-m{font-size:10px;color:var(--amber);font-weight:500}
.conf-l{font-size:10px;color:var(--red);font-weight:500}
.pr{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:14px}
.pill{font-size:12px;padding:4px 10px;border-radius:20px;border:1px solid var(--g2);color:var(--g6);background:#fff}
.p-bl{background:var(--bl);color:var(--blue);border-color:#BFCFE8}
.p-tl{background:var(--tl);color:var(--teal);border-color:#A7D7D0}
.p-pu{background:#F0EEFE;color:#5B45C7;border-color:#C4BAF5}
.ir{background:#fff;border:1px solid var(--g2);border-radius:var(--rl);padding:12px;margin-bottom:8px}
.ir-tp{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:3px;gap:8px}
.ir-ti{font-size:13px;font-weight:600;color:var(--g9)}
.ir-pe{font-size:10px;color:var(--g4);margin-bottom:4px}
.ir-su{font-size:12px;color:var(--g6);line-height:1.6;margin-bottom:5px}
.ir-co{font-size:11px;color:var(--g5)}
.new-tag{font-size:10px;background:var(--rl);color:var(--red);padding:1px 6px;border-radius:10px;font-weight:600;margin-left:6px}
.intel{background:linear-gradient(135deg,#FFF8E7,#FFFBF0);border:1px solid #FDE68A;border-radius:var(--rl);padding:13px;margin-bottom:15px}
.il{font-size:10px;font-weight:700;color:var(--amber);text-transform:uppercase;letter-spacing:.08em;margin-bottom:4px}
.it{font-size:13px;color:var(--g7);line-height:1.65}
.trig{background:var(--g0);border:1px solid var(--g2);border-radius:var(--r);padding:9px 11px;margin-bottom:6px;font-size:12px;color:var(--g6);line-height:1.5}
.emp{padding:32px 16px;text-align:center;color:var(--g4)}
code{font-family:var(--mono);background:var(--g1);padding:2px 6px;border-radius:4px;font-size:11px}
@keyframes fi{from{opacity:0;transform:translateY(3px)}to{opacity:1;transform:translateY(0)}}
.ct > *{animation:fi .15s ease}
</style>""")
html_parts.append("</head>")
html_parts.append("<body>")
html_parts.append("""<div class='topbar'>
  <span style='font-size:18px'>&#9878;</span>
  <span class='title'>Legal Account Tracker</span>
  <span class='sub'>Intelligence Dashboard</span>
  <div class='right'>
    <div class='tstat'><strong id='sr'>-</strong>&nbsp;researched</div>
    <div class='tdiv'></div>
    <div class='tstat'><strong id='si'>-</strong>&nbsp;active issues</div>
    <div class='tdiv'></div>
    <div class='tstat'><div class='live-dot'></div>&nbsp;Live</div>
    <div class='tdiv'></div>
    <a href='/manage' class='tnav'>&#9881; Manage accounts</a>
    <a href='/api/status' target='_blank' class='tnav-dim'>Status</a>
    <a href='/api/digest' target='_blank' class='tnav-dim'>Digest</a>
  </div>
</div>""")
html_parts.append("""<div class='layout'>
  <div class='sidebar'>
    <div class='sb-search'><div class='sb-box'>
      <svg width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2.5'><circle cx='11' cy='11' r='8'/><path d='m21 21-4.35-4.35'/></svg>
      <input id='srch' placeholder='Search accounts...' oninput='filt()'>
    </div></div>
    <div class='acct-list' id='list'></div>
  </div>
  <div class='main'>
    <div class='no-acct' id='na'>
      <svg width='44' height='44' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='1.2' opacity='.2'><path d='M3 21h18M9 8h1M9 12h1M9 16h1M14 8h1M14 12h1M14 16h1M5 21V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16'/></svg>
      <p>Select an account to view intelligence</p>
    </div>
    <div id='vw' style='display:none;flex-direction:column;height:100%;overflow:hidden'>
      <div class='ah'>
        <div class='ah-top'><div class='ah-left'>
          <div class='hav' id='hav'></div>
          <div><div class='hn' id='hn'></div><div class='hm' id='hm'></div></div>
        </div></div>
        <div class='tabs' id='tabs'></div>
      </div>
      <div class='ct' id='cnt'></div>
    </div>
  </div>
</div>""")

js = """
var COLS=[['#EBF2FC','#1E56A0'],['#E6F5F2','#0A7C6E'],['#F0EEFE','#5B45C7'],['#FEF3C7','#B45309'],['#FEE2E2','#991B1B'],['#DCFCE7','#166534'],['#FFF0F3','#9D174D']];
var all=[],aid=null,atab='contacts';
function ini(n){return n.split(/[\\s\\/\\-]+/).map(function(w){return w[0];}).join('').slice(0,2).toUpperCase();}
function col(i){return COLS[i%COLS.length];}
function sbdg(s){var m={Pending:'ba',Ongoing:'ba','Under investigation':'ba',Resolved:'bg',Settled:'bg',Dismissed:'bg',Closed:'bg'};return '<span class="badge '+(m[s]||'bb')+'">'+s+'</span>';}
function itl(t){return '<div class="intel"><div class="il">Sales Intel</div><div class="it">'+t+'</div></div>';}
function emp(m,c){return '<div class="emp"><p>'+m+'</p>'+(c?'<p style="font-size:11px;margin-top:4px">Run: <code>'+c+'</code></p>':'')+'</div>';}
function tcls(t){var x=(t||'').toLowerCase().replace(/[^a-z]/g,'');return{clo:'t-clo',gc:'t-gc',litigation:'t-lit',litigator:'t-lit',headoflitigation:'t-lit',headoflegaloperations:'t-ops',legalops:'t-ops'}[x]||'t-def';}
function ccls(c){return c==='High'?'conf-h':c==='Medium'?'conf-m':'conf-l';}
async function init(){
  var res=await Promise.all([fetch('/api/accounts').then(function(r){return r.json();}),fetch('/api/status').then(function(r){return r.json();})]);
  all=res[0];
  document.getElementById('sr').textContent=res[1].researched+'/'+res[1].accounts;
  document.getElementById('si').textContent=all.reduce(function(s,a){return s+a.activeIssues;},0);
  rlist();
  var f=all.find(function(a){return a.hasData;})||all[0];
  if(f)sel(f.id);
}
function filt(){rlist(document.getElementById('srch').value.toLowerCase());}
function rlist(q){
  q=q||'';
  var f=all.filter(function(a){return !q||a.name.toLowerCase().includes(q)||a.industry.toLowerCase().includes(q);});
  var el=document.getElementById('list');
  if(!f.length){el.innerHTML='<div style="padding:14px;text-align:center;color:#9CA3AF;font-size:12px">No matches</div>';return;}
  el.innerHTML=f.map(function(a,i){
    var c=col(i);
    var sub=a.activeIssues>0?('! '+a.activeIssues+' issue'+(a.activeIssues>1?'s':'')):(a.hasData?a.contactCount+' contacts':'needs research');
    return '<div class="ai'+(a.id===aid?' active':'')+'" onclick="sel(\''+a.id+'\')">'+'<div class="aav" style="background:'+c[0]+';color:'+c[1]+'">'+ini(a.name)+'</div>'+'<div style="min-width:0"><div class="an">'+a.name+'</div><div class="as">'+sub+'</div></div></div>';
  }).join('');
}
async function sel(id){aid=id;rlist();var a=await fetch('/api/accounts/'+id).then(function(r){return r.json();});show(a);}
function show(a){
  document.getElementById('na').style.display='none';
  document.getElementById('vw').style.display='flex';
  var i=all.findIndex(function(x){return x.id===a.id;});var c=col(i);
  var av=document.getElementById('hav');av.style.background=c[0];av.style.color=c[1];av.textContent=ini(a.name);
  document.getElementById('hn').textContent=a.name;
  var upd=a.lastUpdated?new Date(a.lastUpdated).toLocaleDateString('en-US',{month:'short',day:'numeric',hour:'numeric',minute:'2-digit'}):'Never';
  var ai=[].concat((a.research?a.research.litigation||[]:[]).filter(function(l){return!['Resolved','Settled','Dismissed'].includes(l.status);}),(a.research?a.research.regulatory||[]:[]).filter(function(r){return!['Resolved','Closed'].includes(r.status);})).length;
  document.getElementById('hm').innerHTML=a.industry+' <span style="color:#D1D5DB">·</span> '+a.location+' <span style="color:#D1D5DB">·</span> '+(a.research?'<span class="badge bg">Updated '+upd+'</span>':'<span class="badge ba">Needs research</span>')+(ai>0?' <span style="color:#D1D5DB">·</span> <span class="badge br">'+ai+' active issue'+(ai>1?'s':'')+'</span>':'');
  var r=a.research||{};
  var tabs=[{id:'contacts',l:'Contacts',n:(r.contacts||[]).length},{id:'tech',l:'Technology',n:(r.tech||[]).length},{id:'counsel',l:'Counsel',n:(r.counsel||[]).length},{id:'alsp',l:'ALSPs',n:(r.alsp||[]).length+(r.flex||[]).length},{id:'litigation',l:'Litigation',n:(r.litigation||[]).length},{id:'regulatory',l:'Regulatory',n:(r.regulatory||[]).length},{id:'financial',l:'Financial Intel',n:null},{id:'triggers',l:'Sales Triggers',n:(r.sales_triggers||[]).length},{id:'outreach',l:'Outreach',n:null}];
  document.getElementById('tabs').innerHTML=tabs.map(function(t){return '<div class="tab'+(t.id===atab?' active':'')+'" onclick="stab(\''+t.id+'\',this)">'+t.l+(t.n!==null?'<span class="tc">'+t.n+'</span>':'')+'</div>';}).join('');
  rtab(atab,a);
}
function stab(t,el){atab=t;document.querySelectorAll('.tab').forEach(function(x){x.classList.remove('active');});if(el)el.classList.add('active');fetch('/api/accounts/'+aid).then(function(r){return r.json();}).then(function(a){rtab(t,a);});}
function rtab(tab,a){
  var c=document.getElementById('cnt');var r=a.research;
  var i=all.findIndex(function(x){return x.id===a.id;});var cv=col(i);
  if(!r){c.innerHTML=emp('No research data yet','npm run research:account "'+a.name+'"');return;}
  if(tab==='contacts'){
    if(!r.contacts||!r.contacts.length){c.innerHTML=emp('No contacts found');return;}
    var h=(r.intel_summary?itl(r.intel_summary):'')+
      '<div class="sl">Key legal contacts ('+r.contacts.length+')</div>'+
      '<div class="cg">';
    r.contacts.forEach(function(ct){
      h+='<div class="cc"><div class="cc-t"><div class="cav" style="background:'+cv[0]+';color:'+cv[1]+'">'+ini(ct.name)+'</div>';
      h+='<div><div class="cn">'+ct.name+'</div><div class="ct2">'+ct.title+'</div></div></div>';
      h+='<span class="tag '+tcls(ct.tag)+'">'+ct.tag+'</span>';
      if(ct.confidence)h+=' <span class="'+ccls(ct.confidence)+'">'+ct.confidence+'</span>';
      if(ct.email)h+='<div class="cd">@ '+ct.email+'</div>';
      if(ct.linkedin)h+='<div class="cd"><a href="https://'+ct.linkedin+'" target="_blank">LinkedIn</a></div>';
      if(ct.notes)h+='<div class="cd" style="font-style:italic;color:#9CA3AF">'+ct.notes+'</div>';
      if(ct.confidence_reason)h+='<div class="cd" style="color:#9CA3AF">'+ct.confidence_reason+'</div>';
      h+='</div>';
    });
    h+='</div>';
    c.innerHTML=h;
  }else if(tab==='tech'){
    c.innerHTML=(r.intel_summary?itl(r.intel_summary):'')+
      '<div class="sl">Legal technology stack</div>'+
      '<div class="pr">'+(r.tech||[]).map(function(t){return '<span class="pill p-bl">'+t+'</span>';}).join('')+'</div>';
  }else if(tab==='counsel'){
    if(!r.counsel||!r.counsel.length){c.innerHTML=emp('No outside counsel data');return;}
    c.innerHTML='<div class="sl">Outside counsel</div>'+(r.counsel||[]).map(function(f){return '<div class="card" style="font-size:13px">'+f+'</div>';}).join('');
  }else if(tab==='alsp'){
    var ha=r.alsp&&r.alsp.length,hf=r.flex&&r.flex.length;
    if(!ha&&!hf){c.innerHTML=emp('No ALSP or flex talent data');return;}
    c.innerHTML=(ha?'<div class="sl">ALSP relationships</div><div class="pr">'+r.alsp.map(function(x){return '<span class="pill p-tl">'+x+'</span>';}).join('')+'</div>':'')+
      (hf?'<div class="sl">Flex talent</div><div class="pr">'+r.flex.map(function(x){return '<span class="pill p-pu">'+x+'</span>';}).join('')+'</div>':'');
  }else if(tab==='litigation'){
    if(!r.litigation||!r.litigation.length){c.innerHTML=emp('No litigation data');return;}
    var h='<div class="sl">Litigation ('+r.litigation.length+')</div>';
    r.litigation.forEach(function(l){
      h+='<div class="ir"><div class="ir-tp"><span class="ir-ti">'+l.type+(l.is_new?'<span class="new-tag">NEW</span>':'')+'</span>'+sbdg(l.status)+'</div>';
      h+='<div class="ir-pe">'+l.period+'</div><div class="ir-su">'+l.summary+'</div>';
      h+='<div class="ir-co">Outside counsel: <strong>'+(l.counsel||'Unknown')+'</strong></div></div>';
    });
    c.innerHTML=h;
  }else if(tab==='regulatory'){
    if(!r.regulatory||!r.regulatory.length){c.innerHTML=emp('No regulatory data');return;}
    var h='<div class="sl">Regulatory ('+r.regulatory.length+')</div>';
    r.regulatory.forEach(function(x){
      h+='<div class="ir"><div class="ir-tp"><span class="ir-ti">'+x.type+(x.is_new?'<span class="new-tag">NEW</span>':'')+'</span>'+sbdg(x.status)+'</div>';
      h+='<div class="ir-pe">'+x.period+'</div><div class="ir-su">'+x.summary+'</div>';
      h+='<div class="ir-co">Outside counsel: <strong>'+(x.counsel||'Unknown')+'</strong></div></div>';
    });
    c.innerHTML=h;
  }else if(tab==='financial'){
    var fi=r.financial_intel;
    if(!fi){c.innerHTML=emp('No financial intel yet');return;}
    var h='<div class="sl">Financial and strategic intelligence</div>';
    if(fi.latest_filing)h+='<div class="card"><div style="font-size:11px;font-weight:600;color:#9CA3AF;text-transform:uppercase;margin-bottom:4px">Latest filing</div><div style="font-size:13px">'+fi.latest_filing+'</div></div>';
    if(fi.cost_initiatives)h+='<div class="card" style="border-left:3px solid #B45309"><div style="font-size:11px;font-weight:600;color:#B45309;text-transform:uppercase;margin-bottom:4px">Cost initiatives</div><div style="font-size:13px">'+fi.cost_initiatives+'</div></div>';
    if(fi.earnings_signals)h+='<div class="card"><div style="font-size:11px;font-weight:600;color:#9CA3AF;text-transform:uppercase;margin-bottom:4px">Earnings signals</div><div style="font-size:13px">'+fi.earnings_signals+'</div></div>';
    if(fi.legal_risk_factors)h+='<div class="card"><div style="font-size:11px;font-weight:600;color:#9CA3AF;text-transform:uppercase;margin-bottom:4px">Legal risk factors</div><div style="font-size:13px">'+fi.legal_risk_factors+'</div></div>';
    if(fi.ma_activity)h+='<div class="card" style="border-left:3px solid #1E56A0"><div style="font-size:11px;font-weight:600;color:#1E56A0;text-transform:uppercase;margin-bottom:4px">M&A activity</div><div style="font-size:13px">'+fi.ma_activity+'</div></div>';
    c.innerHTML=h;
  }else if(tab==='triggers'){
    var tr=r.sales_triggers||[];var pc=r.personnel_changes||[];
    if(!tr.length&&!pc.length){c.innerHTML=emp('No sales triggers yet');return;}
    var h='';
    if(tr.length){h+='<div class="sl">Sales triggers ('+tr.length+')</div>';tr.forEach(function(t){h+='<div class="trig">'+t+'</div>';});}
    if(pc.length){h+='<div class="sl" style="margin-top:12px">Personnel changes</div>';pc.forEach(function(p){h+='<div class="card"><div style="font-size:13px;font-weight:600;margin-bottom:3px">'+p.name+'</div><div style="font-size:12px;color:#6B7280;margin-bottom:5px">'+p.change+'</div><div style="font-size:12px;color:#0A7C6E">'+p.significance+'</div></div>';});}
    c.innerHTML=h;
  }else if(tab==='outreach'){
    c.innerHTML='<div style="padding:20px;color:#9CA3AF;font-size:13px">Loading digest...</div>';
    fetch('/api/digest').then(function(r){return r.json();}).then(function(d){
      if(d.message){c.innerHTML=emp('No weekly digest yet','npm run digest:weekly');return;}
      var p=(d.priority_accounts||[]).find(function(x){return x.account_name&&x.account_name.toLowerCase().includes(a.name.toLowerCase());});
      var q=(d.quick_touches||[]).find(function(x){return x.account_name&&x.account_name.toLowerCase().includes(a.name.toLowerCase());});
      var nf=(d.new_filings_alert||[]).find(function(x){return x.account_name&&x.account_name.toLowerCase().includes(a.name.toLowerCase());});
      var pw=(d.personnel_watch||[]).find(function(x){return x.account_name&&x.account_name.toLowerCase().includes(a.name.toLowerCase());});
      var h='';
      if(d.week_summary)h+='<div class="intel"><div class="il">This week</div><div class="it">'+d.week_summary+'</div></div>';
      if(nf)h+='<div class="card" style="border-left:3px solid #991B1B;margin-bottom:12px"><div style="font-size:11px;font-weight:700;color:#991B1B;text-transform:uppercase;margin-bottom:4px">New Filing Alert</div><div style="font-size:13px;font-weight:600;margin-bottom:3px">'+nf.filing_type+'</div><div style="font-size:12px;color:#6B7280;margin-bottom:6px">'+nf.summary+'</div><div style="font-size:12px;color:#B45309">'+nf.suggested_action+'</div></div>';
      if(pw)h+='<div class="card" style="border-left:3px solid #0A7C6E;margin-bottom:12px"><div style="font-size:11px;font-weight:700;color:#0A7C6E;text-transform:uppercase;margin-bottom:4px">Personnel Watch</div><div style="font-size:13px;font-weight:600;margin-bottom:3px">'+pw.person+'</div><div style="font-size:12px;color:#6B7280;margin-bottom:4px">'+pw.change+'</div><div style="font-size:12px;color:#0A7C6E">Window: '+pw.window+'</div></div>';
      if(p){
        var uc=p.urgency==='Critical'?'br':p.urgency==='High'?'ba':'bb';
        h+='<div class="sl">Priority outreach</div><div class="card">';
        h+='<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px"><span style="width:22px;height:22px;border-radius:50%;background:#0F2240;color:#fff;font-size:10px;font-weight:700;display:inline-flex;align-items:center;justify-content:center">'+p.priority_rank+'</span><strong>'+p.account_name+'</strong><span class="badge '+uc+'">'+(p.urgency||'')+'</span></div>';
        h+='<p style="font-size:12px;color:#6B7280;margin-bottom:8px">'+p.trigger+'</p>';
        if(p.email)h+='<div style="background:#F9FAFB;border:1px solid #E5E7EB;border-radius:8px;padding:10px;font-size:12px;line-height:1.7"><strong>Subject: '+p.email.subject+'</strong><br><br>'+p.email.body.replace(/\\n/g,'<br>')+'</div>';
        h+='</div>';
      }else{
        h+='<div class="emp"><p>'+a.name+' is not in this week\'s top priorities</p></div>';
      }
      if(q)h+='<div class="sl" style="margin-top:12px">Quick touch</div><div class="card" style="font-size:13px">'+q.action+'</div>';
      c.innerHTML=h;
    });
  }
}
init();
"""

html_parts.append("<script>" + js + "</script>")
html_parts.append("</body>")
html_parts.append("</html>")

html = "\n".join(html_parts)

# Write the complete server.js using Python repr for the HTML
with open(server_path, 'w') as f:
    f.write(content)
    f.write("\nfunction getDash() {\n  return " + repr(html) + ";\n}\n")

print("Done — server.js restored cleanly")
print("File size: " + str(os.path.getsize(server_path)) + " bytes")
print("")
print("Now run:")
print("  pkill -f 'node src/index.js' && npm start")
print("  Open http://localhost:3000")
print("  You should see: Manage accounts | Status | Digest in the top bar")
