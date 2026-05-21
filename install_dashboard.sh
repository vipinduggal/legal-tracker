node -e "
const fs = require('fs');
const content = \`import express from 'express';
import { ACCOUNTS } from '../config/accounts.js';
import { getAllResearch, getLatestDigest, db } from './db.js';
import { logger } from './logger.js';

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
      ...(allResearch[a.id]?.litigation || []).filter(l => l.status !== 'Resolved' && l.status !== 'Settled' && l.status !== 'Dismissed'),
      ...(allResearch[a.id]?.regulatory || []).filter(r => r.status !== 'Resolved' && r.status !== 'Closed'),
    ].length,
    intelSummary: allResearch[a.id]?.intel_summary || null,
  }));
  res.json(data);
});

app.get('/api/accounts/:id', async (req, res) => {
  const account = ACCOUNTS.find(a => a.id === req.params.id);
  if (!account) return res.status(404).json({ error: 'Account not found' });
  const allResearch = await getAllResearch();
  res.json({ ...account, lastUpdated: db.data.lastUpdated?.[account.id] || null, research: allResearch[account.id] || null });
});

app.get('/api/digest', async (req, res) => {
  const digest = await getLatestDigest();
  res.json(digest || { message: 'No digest generated yet' });
});

app.get('/api/status', async (req, res) => {
  await db.read();
  const allResearch = await getAllResearch();
  const researched = Object.keys(allResearch).length;
  res.json({ status: 'ok', accounts: ACCOUNTS.length, researched, pending: ACCOUNTS.length - researched, recentRuns: (db.data.runs || []).slice(0, 5) });
});

app.get('/', (req, res) => res.send(DASH));

export function startServer() {
  const port = process.env.PORT || 3000;
  app.listen(port, () => logger.info('Dashboard running at http://localhost:' + port));
  return app;
}

const DASH = \\\`<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Legal Account Tracker</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{--navy:#0F2240;--blue:#1E56A0;--blue-light:#EBF2FC;--teal:#0A7C6E;--teal-light:#E6F5F2;--amber:#B45309;--amber-light:#FEF3C7;--red:#991B1B;--red-light:#FEE2E2;--green:#166534;--green-light:#DCFCE7;--gray-50:#F9FAFB;--gray-100:#F3F4F6;--gray-200:#E5E7EB;--gray-300:#D1D5DB;--gray-400:#9CA3AF;--gray-500:#6B7280;--gray-600:#4B5563;--gray-700:#374151;--gray-900:#111827;--font:'DM Sans',sans-serif;--mono:'DM Mono',monospace;--sidebar:240px;--radius:10px;--radius-lg:14px}
body{font-family:var(--font);font-size:14px;color:var(--gray-900);background:var(--gray-50);height:100vh;overflow:hidden;display:flex;flex-direction:column}
.topbar{height:52px;background:var(--navy);display:flex;align-items:center;padding:0 20px;gap:16px;flex-shrink:0}
.topbar-title{font-size:15px;font-weight:600;color:#fff}
.topbar-sub{font-size:12px;color:rgba(255,255,255,.4)}
.topbar-right{margin-left:auto;display:flex;align-items:center;gap:10px}
.topbar-stat{font-size:12px;color:rgba(255,255,255,.55);display:flex;align-items:center;gap:5px}
.topbar-stat strong{color:rgba(255,255,255,.9);font-weight:500}
.topbar-div{width:1px;height:16px;background:rgba(255,255,255,.12)}
.dot{width:7px;height:7px;border-radius:50%;background:#34D399}
.layout{display:flex;flex:1;overflow:hidden}
.sidebar{width:var(--sidebar);background:#fff;border-right:1px solid var(--gray-200);display:flex;flex-direction:column;overflow:hidden}
.sb-search{padding:10px}
.sb-input{display:flex;align-items:center;gap:7px;background:var(--gray-50);border:1px solid var(--gray-200);border-radius:var(--radius);padding:6px 10px}
.sb-input input{border:none;background:none;outline:none;font-size:12px;color:var(--gray-700);font-family:var(--font);width:100%}
.sb-input input::placeholder{color:var(--gray-400)}
.acct-list{flex:1;overflow-y:auto;padding:4px 8px 8px}
.acct-item{display:flex;align-items:center;gap:8px;padding:7px 9px;border-radius:var(--radius);cursor:pointer;border:1px solid transparent;margin-bottom:1px;transition:all .12s}
.acct-item:hover{background:var(--gray-50);border-color:var(--gray-200)}
.acct-item.active{background:var(--blue-light);border-color:#BFCFE8}
.acct-av{width:27px;height:27px;border-radius:6px;display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:600;flex-shrink:0}
.acct-name{font-size:12px;font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:var(--gray-800)}
.acct-item.active .acct-name{color:var(--blue)}
.acct-sub{font-size:10px;color:var(--gray-400);margin-top:1px}
.main{flex:1;display:flex;flex-direction:column;overflow:hidden;min-width:0}
.no-acct{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:8px;color:var(--gray-400)}
.acct-hdr{padding:14px 20px 0;border-bottom:1px solid var(--gray-200);flex-shrink:0}
.acct-hdr-top{display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:12px}
.acct-hdr-left{display:flex;align-items:center;gap:11px}
.hdr-av{width:38px;height:38px;border-radius:9px;display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:600;flex-shrink:0}
.hdr-name{font-size:17px;font-weight:600;color:var(--gray-900);letter-spacing:-.02em}
.hdr-meta{font-size:11px;color:var(--gray-500);margin-top:2px;display:flex;align-items:center;gap:6px;flex-wrap:wrap}
.badge{display:inline-flex;align-items:center;font-size:10px;font-weight:500;padding:2px 7px;border-radius:20px}
.badge-green{background:var(--green-light);color:var(--green)}
.badge-amber{background:var(--amber-light);color:var(--amber)}
.badge-red{background:var(--red-light);color:var(--red)}
.badge-blue{background:var(--blue-light);color:var(--blue)}
.tabs{display:flex;overflow-x:auto;scrollbar-width:none;margin-top:2px}
.tabs::-webkit-scrollbar{display:none}
.tab{padding:8px 13px;font-size:12px;font-weight:500;cursor:pointer;border-bottom:2px solid transparent;color:var(--gray-500);white-space:nowrap;transition:all .12s;display:flex;align-items:center;gap:4px}
.tab:hover{color:var(--gray-700)}
.tab.active{color:var(--blue);border-bottom-color:var(--blue)}
.tab-ct{font-size:10px;padding:1px 5px;border-radius:10px;background:var(--gray-100);color:var(--gray-500)}
.tab.active .tab-ct{background:var(--blue-light);color:var(--blue)}
.content{flex:1;overflow-y:auto;padding:18px}
.sec-lbl{font-size:11px;font-weight:600;color:var(--gray-400);text-transform:uppercase;letter-spacing:.06em;margin-bottom:9px;display:flex;align-items:center;gap:6px}
.sec-lbl::after{content:'';flex:1;height:1px;background:var(--gray-100)}
.card{background:#fff;border:1px solid var(--gray-200);border-radius:var(--radius-lg);padding:13px;margin-bottom:9px;transition:box-shadow .12s}
.card:hover{box-shadow:0 4px 6px rgba(0,0,0,.07)}
.cgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(195px,1fr));gap:9px;margin-bottom:12px}
.ccard{background:#fff;border:1px solid var(--gray-200);border-radius:var(--radius-lg);padding:12px;transition:all .12s}
.ccard:hover{box-shadow:0 4px 6px rgba(0,0,0,.07);transform:translateY(-1px)}
.ccard-top{display:flex;align-items:center;gap:8px;margin-bottom:7px}
.cav{width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:600;flex-shrink:0}
.cname{font-size:12px;font-weight:600;color:var(--gray-900);line-height:1.3}
.ctitle{font-size:10px;color:var(--gray-500)}
.cdetail{font-size:10px;color:var(--gray-500);display:flex;align-items:center;gap:3px;margin-top:3px}
.cdetail a{color:var(--blue);text-decoration:none}
.tag{display:inline-block;font-size:10px;font-weight:500;padding:2px 7px;border-radius:20px;margin-bottom:5px}
.tag-clo,.tag-clO{background:#F0EEFE;color:#5B45C7}
.tag-gc{background:var(--blue-light);color:var(--blue)}
.tag-litigation,.tag-litigator{background:var(--amber-light);color:var(--amber)}
.tag-legalops{background:var(--teal-light);color:var(--teal)}
.tag-default{background:var(--gray-100);color:var(--gray-600)}
.pill-row{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:14px}
.pill{font-size:12px;padding:4px 10px;border-radius:20px;border:1px solid var(--gray-200);color:var(--gray-600);background:#fff}
.pill-blue{background:var(--blue-light);color:var(--blue);border-color:#BFCFE8}
.pill-teal{background:var(--teal-light);color:var(--teal);border-color:#A7D7D0}
.pill-purple{background:#F0EEFE;color:#5B45C7;border-color:#C4BAF5}
.irow{background:#fff;border:1px solid var(--gray-200);border-radius:var(--radius-lg);padding:12px;margin-bottom:8px}
.irow-top{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:3px;gap:8px}
.irow-title{font-size:13px;font-weight:600;color:var(--gray-900)}
.irow-period{font-size:10px;color:var(--gray-400);margin-bottom:4px}
.irow-summary{font-size:12px;color:var(--gray-600);line-height:1.6;margin-bottom:5px}
.irow-counsel{font-size:11px;color:var(--gray-500);display:flex;align-items:center;gap:3px}
.intel{background:linear-gradient(135deg,#FFF8E7,#FFFBF0);border:1px solid #FDE68A;border-radius:var(--radius-lg);padding:13px;margin-bottom:15px}
.intel-lbl{font-size:10px;font-weight:700;color:var(--amber);text-transform:uppercase;letter-spacing:.08em;margin-bottom:4px}
.intel-txt{font-size:13px;color:var(--gray-800);line-height:1.65}
.empty{padding:32px 16px;text-align:center;color:var(--gray-400)}
.empty p{font-size:13px;margin-bottom:8px}
code{font-family:var(--mono);background:var(--gray-100);padding:2px 6px;border-radius:4px;font-size:11px}
@keyframes fi{from{opacity:0;transform:translateY(3px)}to{opacity:1;transform:translateY(0)}}
.content>*{animation:fi .15s ease}
</style>
</head>
<body>
<div class="topbar">
  <span style="font-size:18px">⚖️</span>
  <span class="topbar-title">Legal Account Tracker</span>
  <span class="topbar-sub">Intelligence Dashboard</span>
  <div class="topbar-right">
    <div class="topbar-stat"><strong id="s-res">—</strong> researched</div>
    <div class="topbar-div"></div>
    <div class="topbar-stat"><strong id="s-iss">—</strong> active issues</div>
    <div class="topbar-div"></div>
    <div class="topbar-stat"><div class="dot"></div> Live</div>
  </div>
</div>
<div class="layout">
  <div class="sidebar">
    <div class="sb-search">
      <div class="sb-input">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
        <input id="srch" placeholder="Search accounts…" oninput="filter()">
      </div>
    </div>
    <div class="acct-list" id="list"></div>
  </div>
  <div class="main" id="main">
    <div class="no-acct" id="noAcct">
      <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2" opacity=".25"><path d="M3 21h18M9 8h1M9 12h1M9 16h1M14 8h1M14 12h1M14 16h1M5 21V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16"/></svg>
      <p>Select an account to view intelligence</p>
    </div>
    <div id="view" style="display:none;flex-direction:column;height:100%;overflow:hidden">
      <div class="acct-hdr">
        <div class="acct-hdr-top">
          <div class="acct-hdr-left">
            <div class="hdr-av" id="hAv"></div>
            <div><div class="hdr-name" id="hName"></div><div class="hdr-meta" id="hMeta"></div></div>
          </div>
        </div>
        <div class="tabs" id="tabs"></div>
      </div>
      <div class="content" id="cnt"></div>
    </div>
  </div>
</div>
<script>
const COLORS=[['#EBF2FC','#1E56A0'],['#E6F5F2','#0A7C6E'],['#F0EEFE','#5B45C7'],['#FEF3C7','#B45309'],['#FEE2E2','#991B1B'],['#DCFCE7','#166534'],['#FFF0F3','#9D174D']];
let all=[],aid=null,atab='contacts';
const ini=n=>n.split(/[\\s\\/\\-]+/).map(w=>w[0]).join('').slice(0,2).toUpperCase();
const col=i=>COLORS[i%COLORS.length];

async function init(){
  const [accts,st]=await Promise.all([fetch('/api/accounts').then(r=>r.json()),fetch('/api/status').then(r=>r.json())]);
  all=accts;
  document.getElementById('s-res').textContent=st.researched+'/'+st.accounts;
  document.getElementById('s-iss').textContent=accts.reduce((s,a)=>s+a.activeIssues,0);
  render();
  const first=accts.find(a=>a.hasData)||accts[0];
  if(first)sel(first.id);
}

function filter(){
  const q=document.getElementById('srch').value.toLowerCase();
  render(q);
}

function render(q=''){
  const f=all.filter(a=>!q||a.name.toLowerCase().includes(q)||a.industry.toLowerCase().includes(q));
  const list=document.getElementById('list');
  if(!f.length){list.innerHTML='<div style="padding:14px;text-align:center;color:var(--gray-400);font-size:12px">No accounts match</div>';return;}
  list.innerHTML=f.map((a,i)=>{
    const[bg,txt]=col(i);
    return \\\`<div class="acct-item\\\${a.id===aid?' active':''}" onclick="sel('\\\${a.id}')">
      <div class="acct-av" style="background:\\\${bg};color:\\\${txt}">\\\${ini(a.name)}</div>
      <div style="min-width:0">
        <div class="acct-name">\\\${a.name}</div>
        <div class="acct-sub">\\\${a.activeIssues>0?'⚠ '+a.activeIssues+' issue'+(a.activeIssues>1?'s':''):a.hasData?a.contactCount+' contacts':'needs research'}</div>
      </div>
    </div>\\\`;
  }).join('');
}

async function sel(id){
  aid=id;render();
  const a=await fetch('/api/accounts/'+id).then(r=>r.json());
  show(a);
}

function show(a){
  document.getElementById('noAcct').style.display='none';
  const v=document.getElementById('view');v.style.display='flex';
  const i=all.findIndex(x=>x.id===a.id);
  const[bg,txt]=col(i);
  const av=document.getElementById('hAv');av.style.background=bg;av.style.color=txt;av.textContent=ini(a.name);
  document.getElementById('hName').textContent=a.name;
  const upd=a.lastUpdated?new Date(a.lastUpdated).toLocaleDateString('en-US',{month:'short',day:'numeric',hour:'numeric',minute:'2-digit'}):'Never';
  const ai=[...(a.research?.litigation||[]).filter(l=>!['Resolved','Settled','Dismissed'].includes(l.status)),...(a.research?.regulatory||[]).filter(r=>!['Resolved','Closed'].includes(r.status))].length;
  document.getElementById('hMeta').innerHTML=
    a.industry+'<span style="color:var(--gray-300)">·</span>'+a.location+
    '<span style="color:var(--gray-300)">·</span>'+
    (a.research?'<span class="badge badge-green">Updated '+upd+'</span>':'<span class="badge badge-amber">Needs research</span>')+
    (ai>0?'<span style="color:var(--gray-300)">·</span><span class="badge badge-red">'+ai+' active issue'+(ai>1?'s':'')+'</span>':'');
  const r=a.research||{};
  const tabs=[{id:'contacts',l:'Contacts',n:(r.contacts||[]).length},{id:'tech',l:'Technology',n:(r.tech||[]).length},{id:'counsel',l:'Counsel',n:(r.counsel||[]).length},{id:'alsp',l:'ALSPs',n:(r.alsp||[]).length+(r.flex||[]).length},{id:'litigation',l:'Litigation',n:(r.litigation||[]).length},{id:'regulatory',l:'Regulatory',n:(r.regulatory||[]).length},{id:'outreach',l:'Outreach',n:null}];
  document.getElementById('tabs').innerHTML=tabs.map(t=>\\\`<div class="tab\\\${t.id===atab?' active':''}" onclick="stab('\\\${t.id}',this)">\\\${t.l}\\\${t.n!==null?'<span class="tab-ct">'+t.n+'</span>':''}</div>\\\`).join('');
  rtab(atab,a);
}

function stab(t,el){atab=t;document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));if(el)el.classList.add('active');fetch('/api/accounts/'+aid).then(r=>r.json()).then(a=>rtab(t,a));}

function tagcls(tag){const t=(tag||'').toLowerCase().replace(/[^a-z]/g,'');return{clo:'tag-clo',gc:'tag-gc',litigation:'tag-litigation',litigator:'tag-litigator',headoflitigation:'tag-litigation',headoflegaloperations:'tag-legalops',legalops:'tag-legalops'}[t]||'tag-default';}

function sbadge(s){return'<span class="badge '+({'Pending':'badge-amber','Ongoing':'badge-amber','Under investigation':'badge-amber','Resolved':'badge-green','Settled':'badge-green','Dismissed':'badge-green','Closed':'badge-green'}[s]||'badge-blue')+'">'+s+'</span>';}

function intel(txt){return'<div class="intel"><div class="intel-lbl">💡 Sales Intel</div><div class="intel-txt">'+txt+'</div></div>';}

function empty(msg,cmd){return'<div class="empty"><p>'+msg+'</p>'+(cmd?'<p style="font-size:11px;color:var(--gray-400)">Run: <code>'+cmd+'</code></p>':'')+'</div>';}

function rtab(tab,a){
  const c=document.getElementById('cnt');
  const r=a.research;
  if(!r){c.innerHTML=empty('No research data yet for '+a.name,'npm run research:account "'+a.name+'"');return;}
  const i=all.findIndex(x=>x.id===a.id);
  const[bg,txt]=col(i);
  if(tab==='contacts'){
    if(!r.contacts?.length){c.innerHTML=empty('No contacts found');return;}
    c.innerHTML=(r.intel_summary?intel(r.intel_summary):'')+
      '<div class="sec-lbl">Key legal contacts ('+r.contacts.length+')</div>'+
      '<div class="cgrid">'+r.contacts.map(ct=>'<div class="ccard"><div class="ccard-top"><div class="cav" style="background:'+bg+';color:'+txt+'">'+ini(ct.name)+'</div><div><div class="cname">'+ct.name+'</div><div class="ctitle">'+ct.title+'</div></div></div><span class="tag '+tagcls(ct.tag)+'">'+ct.tag+'</span>'+(ct.email?'<div class="cdetail">✉ '+ct.email+'</div>':'')+(ct.linkedin?'<div class="cdetail">🔗 <a href="https://'+ct.linkedin+'" target="_blank">LinkedIn</a></div>':'')+(ct.notes?'<div class="cdetail" style="font-style:italic;color:var(--gray-400)">'+ct.notes+'</div>':'')+'</div>').join('')+'</div>';
  } else if(tab==='tech'){
    c.innerHTML=(r.intel_summary?intel(r.intel_summary):'')+
      '<div class="sec-lbl">Legal technology stack</div>'+
      '<div class="pill-row">'+(r.tech||[]).map(t=>'<span class="pill pill-blue">'+t+'</span>').join('')+'</div>';
  } else if(tab==='counsel'){
    if(!r.counsel?.length){c.innerHTML=empty('No outside counsel data');return;}
    c.innerHTML='<div class="sec-lbl">Primary outside counsel</div>'+(r.counsel||[]).map(f=>'<div class="card" style="font-size:13px">🏛 '+f+'</div>').join('');
  } else if(tab==='alsp'){
    const ha=r.alsp?.length,hf=r.flex?.length;
    if(!ha&&!hf){c.innerHTML=empty('No ALSP or flex talent data');return;}
    c.innerHTML=(ha?'<div class="sec-lbl">ALSP relationships</div><div class="pill-row">'+r.alsp.map(x=>'<span class="pill pill-teal">'+x+'</span>').join('')+'</div>':'')+(hf?'<div class="sec-lbl">Flex talent</div><div class="pill-row">'+r.flex.map(x=>'<span class="pill pill-purple">'+x+'</span>').join('')+'</div>':'');
  } else if(tab==='litigation'){
    if(!r.litigation?.length){c.innerHTML=empty('No litigation data');return;}
    c.innerHTML='<div class="sec-lbl">Litigation — last 24 months ('+r.litigation.length+')</div>'+(r.litigation||[]).map(l=>'<div class="irow"><div class="irow-top"><span class="irow-title">'+l.type+'</span>'+sbadge(l.status)+'</div><div class="irow-period">'+l.period+'</div><div class="irow-summary">'+l.summary+'</div><div class="irow-counsel">🏛 Outside counsel: <strong>'+(l.counsel||'Unknown')+'</strong></div></div>').join('');
  } else if(tab==='regulatory'){
    if(!r.regulatory?.length){c.innerHTML=empty('No regulatory data');return;}
    c.innerHTML='<div class="sec-lbl">Regulatory issues — last 24 months ('+r.regulatory.length+')</div>'+(r.regulatory||[]).map(x=>'<div class="irow"><div class="irow-top"><span class="irow-title">'+x.type+'</span>'+sbadge(x.status)+'</div><div class="irow-period">'+x.period+'</div><div class="irow-summary">'+x.summary+'</div><div class="irow-counsel">🏛 Outside counsel: <strong>'+(x.counsel||'Unknown')+'</strong></div></div>').join('');
  } else if(tab==='outreach'){
    c.innerHTML='<div style="padding:20px;color:var(--gray-400);font-size:13px">Loading digest…</div>';
    fetch('/api/digest').then(r=>r.json()).then(d=>{
      if(d.message){c.innerHTML=empty('No weekly digest yet','npm run digest:weekly');return;}
      const p=(d.priority_accounts||[]).find(x=>x.account_name?.toLowerCase().includes(a.name.toLowerCase()));
      const q=(d.quick_touches||[]).find(x=>x.account_name?.toLowerCase().includes(a.name.toLowerCase()));
      c.innerHTML=(d.week_summary?'<div class="intel"><div class="intel-lbl">📬 This week</div><div class="intel-txt">'+d.week_summary+'</div></div>':'')+
        (p?'<div class="sec-lbl">'+a.name+' — priority outreach</div><div class="card"><div style="display:flex;align-items:center;gap:8px;margin-bottom:6px"><span style="width:22px;height:22px;border-radius:50%;background:var(--navy);color:#fff;font-size:10px;font-weight:700;display:inline-flex;align-items:center;justify-content:center">'+p.priority_rank+'</span><strong>'+p.account_name+'</strong></div><p style="font-size:12px;color:var(--gray-600);margin-bottom:10px">'+p.reason+'</p>'+(p.email?'<div style="background:var(--gray-50);border:1px solid var(--gray-200);border-radius:8px;padding:10px;font-size:12px;line-height:1.7"><strong>Subject: '+p.email.subject+'</strong><br><br>'+p.email.body.replace(/\\n/g,'<br>')+'</div>':'')+'</div>':'<div class="empty"><p>'+a.name+' is not in this week\'s top priorities</p></div>')+
        (q?'<div class="sec-lbl">Quick touch</div><div class="card" style="font-size:13px">'+q.action+'</div>':'');
    });
  }
}
init();
</script>
</body>
</html>\\\`;
\`;
fs.writeFileSync(process.env.HOME + '/legal-tracker/src/server.js', content);
console.log('Done — server.js written successfully');
"