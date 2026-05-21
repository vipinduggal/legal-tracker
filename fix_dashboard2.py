import os

home = os.path.expanduser("~")
path = os.path.join(home, "legal-tracker", "src", "server.js")

# Write the complete server.js using only double quotes in JS
# and avoiding ALL escaped quote sequences

api = """import express from 'express';
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

app.get('/', (req, res) => res.send(HTML));

export function startServer() {
  const port = process.env.PORT || 3000;
  app.listen(port, () => logger.info('Dashboard at http://localhost:' + port));
  return app;
}

"""

# Build HTML as a raw string stored in a JS const
# Key: use single quotes ONLY inside the HTML string (backtick template literal)
# and avoid any JS inside the HTML that uses backticks

html = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Legal Account Tracker</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&family=DM+Mono&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{
  --navy:#0F2240;--blue:#1E56A0;--bl:#EBF2FC;
  --teal:#0A7C6E;--tl:#E6F5F2;
  --amber:#B45309;--al:#FEF3C7;
  --red:#991B1B;--rl:#FEE2E2;
  --green:#166534;--gl:#DCFCE7;
  --g0:#F9FAFB;--g1:#F3F4F6;--g2:#E5E7EB;
  --g4:#9CA3AF;--g5:#6B7280;--g6:#4B5563;--g7:#374151;--g9:#111827;
  --f:"DM Sans",sans-serif;--mono:"DM Mono",monospace;
  --r:10px;--rl:14px
}
body{font-family:var(--f);font-size:14px;color:var(--g9);background:var(--g0);height:100vh;overflow:hidden;display:flex;flex-direction:column}
.topbar{height:52px;background:var(--navy);display:flex;align-items:center;padding:0 20px;gap:12px;flex-shrink:0}
.topbar .title{font-size:15px;font-weight:600;color:#fff}
.topbar .sub{font-size:12px;color:rgba(255,255,255,.4)}
.topbar .right{margin-left:auto;display:flex;align-items:center;gap:10px}
.stat{font-size:12px;color:rgba(255,255,255,.55);display:flex;align-items:center;gap:5px}
.stat strong{color:rgba(255,255,255,.9)}
.divider{width:1px;height:16px;background:rgba(255,255,255,.12)}
.live-dot{width:7px;height:7px;border-radius:50%;background:#34D399}
.layout{display:flex;flex:1;overflow:hidden}
.sidebar{width:240px;background:#fff;border-right:1px solid var(--g2);display:flex;flex-direction:column;overflow:hidden}
.search-wrap{padding:10px}
.search-box{display:flex;align-items:center;gap:7px;background:var(--g0);border:1px solid var(--g2);border-radius:var(--r);padding:6px 10px}
.search-box input{border:none;background:none;outline:none;font-size:12px;color:var(--g7);font-family:var(--f);width:100%}
.search-box input::placeholder{color:var(--g4)}
.acct-list{flex:1;overflow-y:auto;padding:4px 8px 8px}
.acct-item{display:flex;align-items:center;gap:8px;padding:7px 9px;border-radius:var(--r);cursor:pointer;border:1px solid transparent;margin-bottom:1px;transition:all .12s}
.acct-item:hover{background:var(--g0);border-color:var(--g2)}
.acct-item.active{background:var(--bl);border-color:#BFCFE8}
.acct-avatar{width:27px;height:27px;border-radius:6px;display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:600;flex-shrink:0}
.acct-name{font-size:12px;font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:var(--g7)}
.acct-item.active .acct-name{color:var(--blue)}
.acct-sub{font-size:10px;color:var(--g4);margin-top:1px}
.main{flex:1;display:flex;flex-direction:column;overflow:hidden;min-width:0}
.empty-main{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:8px;color:var(--g4)}
.acct-header{padding:14px 20px 0;border-bottom:1px solid var(--g2);flex-shrink:0}
.acct-header-top{display:flex;align-items:flex-start;margin-bottom:12px}
.acct-header-left{display:flex;align-items:center;gap:11px}
.header-avatar{width:38px;height:38px;border-radius:9px;display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:600;flex-shrink:0}
.header-name{font-size:17px;font-weight:600;color:var(--g9);letter-spacing:-.02em}
.header-meta{font-size:11px;color:var(--g5);margin-top:2px;display:flex;align-items:center;gap:6px;flex-wrap:wrap}
.badge{display:inline-flex;align-items:center;font-size:10px;font-weight:500;padding:2px 7px;border-radius:20px}
.badge.green{background:var(--gl);color:var(--green)}
.badge.amber{background:var(--al);color:var(--amber)}
.badge.red{background:var(--rl);color:var(--red)}
.badge.blue{background:var(--bl);color:var(--blue)}
.tabs{display:flex;overflow-x:auto;scrollbar-width:none;margin-top:2px}
.tabs::-webkit-scrollbar{display:none}
.tab{padding:8px 13px;font-size:12px;font-weight:500;cursor:pointer;border-bottom:2px solid transparent;color:var(--g5);white-space:nowrap;transition:all .12s;display:flex;align-items:center;gap:4px}
.tab:hover{color:var(--g7)}
.tab.active{color:var(--blue);border-bottom-color:var(--blue)}
.tab-count{font-size:10px;padding:1px 5px;border-radius:10px;background:var(--g1);color:var(--g5)}
.tab.active .tab-count{background:var(--bl);color:var(--blue)}
.content{flex:1;overflow-y:auto;padding:18px}
.section-label{font-size:11px;font-weight:600;color:var(--g4);text-transform:uppercase;letter-spacing:.06em;margin-bottom:9px;display:flex;align-items:center;gap:6px}
.section-label::after{content:"";flex:1;height:1px;background:var(--g1)}
.card{background:#fff;border:1px solid var(--g2);border-radius:var(--rl);padding:13px;margin-bottom:9px}
.contact-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(195px,1fr));gap:9px;margin-bottom:12px}
.contact-card{background:#fff;border:1px solid var(--g2);border-radius:var(--rl);padding:12px;transition:all .12s}
.contact-card:hover{box-shadow:0 4px 6px rgba(0,0,0,.07);transform:translateY(-1px)}
.contact-top{display:flex;align-items:center;gap:8px;margin-bottom:7px}
.contact-av{width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:600;flex-shrink:0}
.contact-name{font-size:12px;font-weight:600;color:var(--g9);line-height:1.3}
.contact-title{font-size:10px;color:var(--g5)}
.contact-detail{font-size:10px;color:var(--g5);display:flex;align-items:center;gap:3px;margin-top:3px}
.contact-detail a{color:var(--blue);text-decoration:none}
.role-tag{display:inline-block;font-size:10px;font-weight:500;padding:2px 7px;border-radius:20px;margin-bottom:5px}
.role-clo{background:#F0EEFE;color:#5B45C7}
.role-gc{background:var(--bl);color:var(--blue)}
.role-lit{background:var(--al);color:var(--amber)}
.role-ops{background:var(--tl);color:var(--teal)}
.role-def{background:var(--g1);color:var(--g6)}
.conf-high{font-size:10px;color:var(--green);font-weight:500}
.conf-med{font-size:10px;color:var(--amber);font-weight:500}
.conf-low{font-size:10px;color:var(--red);font-weight:500}
.pill-row{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:14px}
.pill{font-size:12px;padding:4px 10px;border-radius:20px;border:1px solid var(--g2);color:var(--g6);background:#fff}
.pill.blue{background:var(--bl);color:var(--blue);border-color:#BFCFE8}
.pill.teal{background:var(--tl);color:var(--teal);border-color:#A7D7D0}
.pill.purple{background:#F0EEFE;color:#5B45C7;border-color:#C4BAF5}
.issue-row{background:#fff;border:1px solid var(--g2);border-radius:var(--rl);padding:12px;margin-bottom:8px}
.issue-top{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:3px;gap:8px}
.issue-title{font-size:13px;font-weight:600;color:var(--g9)}
.issue-period{font-size:10px;color:var(--g4);margin-bottom:4px}
.issue-summary{font-size:12px;color:var(--g6);line-height:1.6;margin-bottom:5px}
.issue-counsel{font-size:11px;color:var(--g5)}
.new-badge{font-size:10px;background:var(--rl);color:var(--red);padding:1px 6px;border-radius:10px;font-weight:600;margin-left:6px}
.intel-box{background:linear-gradient(135deg,#FFF8E7,#FFFBF0);border:1px solid #FDE68A;border-radius:var(--rl);padding:13px;margin-bottom:15px}
.intel-label{font-size:10px;font-weight:700;color:var(--amber);text-transform:uppercase;letter-spacing:.08em;margin-bottom:4px}
.intel-text{font-size:13px;color:var(--g7);line-height:1.65}
.trigger-row{background:var(--g0);border:1px solid var(--g2);border-radius:var(--r);padding:9px 11px;margin-bottom:6px;font-size:12px;color:var(--g6);line-height:1.5}
.empty-panel{padding:32px 16px;text-align:center;color:var(--g4)}
.empty-panel p{font-size:13px;margin-bottom:6px}
code{font-family:var(--mono);background:var(--g1);padding:2px 6px;border-radius:4px;font-size:11px}
@keyframes fadeIn{from{opacity:0;transform:translateY(3px)}to{opacity:1;transform:translateY(0)}}
.content > *{animation:fadeIn .15s ease}
</style>
</head>
<body>
<div class="topbar">
  <span style="font-size:18px">&#9878;</span>
  <span class="title">Legal Account Tracker</span>
  <span class="sub">Intelligence Dashboard</span>
  <div class="right">
    <div class="stat"><strong id="stat-res">-</strong>&nbsp;researched</div>
    <div class="divider"></div>
    <div class="stat"><strong id="stat-iss">-</strong>&nbsp;active issues</div>
    <div class="divider"></div>
    <div class="stat"><div class="live-dot"></div>&nbsp;Live</div>
  </div>
</div>
<div class="layout">
  <div class="sidebar">
    <div class="search-wrap">
      <div class="search-box">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
        <input id="search-input" placeholder="Search accounts..." oninput="filterList()">
      </div>
    </div>
    <div class="acct-list" id="acct-list"></div>
  </div>
  <div class="main">
    <div class="empty-main" id="empty-main">
      <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2" opacity=".2"><path d="M3 21h18M9 8h1M9 12h1M9 16h1M14 8h1M14 12h1M14 16h1M5 21V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16"/></svg>
      <p>Select an account to view intelligence</p>
    </div>
    <div id="acct-view" style="display:none;flex-direction:column;height:100%;overflow:hidden">
      <div class="acct-header">
        <div class="acct-header-top">
          <div class="acct-header-left">
            <div class="header-avatar" id="header-avatar"></div>
            <div>
              <div class="header-name" id="header-name"></div>
              <div class="header-meta" id="header-meta"></div>
            </div>
          </div>
        </div>
        <div class="tabs" id="tabs"></div>
      </div>
      <div class="content" id="tab-content"></div>
    </div>
  </div>
</div>
<script>
var COLORS = [
  ['#EBF2FC','#1E56A0'],['#E6F5F2','#0A7C6E'],['#F0EEFE','#5B45C7'],
  ['#FEF3C7','#B45309'],['#FEE2E2','#991B1B'],['#DCFCE7','#166534'],['#FFF0F3','#9D174D']
];
var allAccounts = [];
var activeId = null;
var activeTab = 'contacts';

function initials(name) {
  return name.split(/[\\s\\/\\-]+/).map(function(w){return w[0];}).join('').slice(0,2).toUpperCase();
}
function colorFor(i) { return COLORS[i % COLORS.length]; }

function statusBadge(s) {
  var cls = {Pending:'amber',Ongoing:'amber','Under investigation':'amber',Resolved:'green',Settled:'green',Dismissed:'green',Closed:'green'}[s] || 'blue';
  return '<span class="badge ' + cls + '">' + s + '</span>';
}

function roleClass(tag) {
  var t = (tag || '').toLowerCase().replace(/[^a-z]/g,'');
  var m = {clo:'role-clo',gc:'role-gc',litigation:'role-lit',litigator:'role-lit',headoflitigation:'role-lit',headoflegaloperations:'role-ops',legalops:'role-ops'};
  return m[t] || 'role-def';
}

function confClass(c) {
  return c === 'High' ? 'conf-high' : c === 'Medium' ? 'conf-med' : 'conf-low';
}

function intelBox(text) {
  return '<div class="intel-box"><div class="intel-label">Sales Intel</div><div class="intel-text">' + text + '</div></div>';
}

function emptyPanel(msg, cmd) {
  return '<div class="empty-panel"><p>' + msg + '</p>' + (cmd ? '<p>Run: <code>' + cmd + '</code></p>' : '') + '</div>';
}

async function init() {
  var results = await Promise.all([
    fetch('/api/accounts').then(function(r){return r.json();}),
    fetch('/api/status').then(function(r){return r.json();})
  ]);
  allAccounts = results[0];
  var status = results[1];
  document.getElementById('stat-res').textContent = status.researched + '/' + status.accounts;
  var totalIssues = allAccounts.reduce(function(s,a){return s + a.activeIssues;}, 0);
  document.getElementById('stat-iss').textContent = totalIssues;
  renderList();
  var first = allAccounts.find(function(a){return a.hasData;}) || allAccounts[0];
  if (first) selectAccount(first.id);
}

function filterList() {
  var q = document.getElementById('search-input').value.toLowerCase();
  renderList(q);
}

function renderList(q) {
  q = q || '';
  var filtered = allAccounts.filter(function(a) {
    return !q || a.name.toLowerCase().includes(q) || a.industry.toLowerCase().includes(q);
  });
  var el = document.getElementById('acct-list');
  if (!filtered.length) { el.innerHTML = '<div style="padding:14px;text-align:center;color:#9CA3AF;font-size:12px">No matches</div>'; return; }
  el.innerHTML = filtered.map(function(a, i) {
    var c = colorFor(i);
    var isActive = a.id === activeId;
    var sub = a.activeIssues > 0 ? ('! ' + a.activeIssues + ' issue' + (a.activeIssues > 1 ? 's' : '')) : (a.hasData ? a.contactCount + ' contacts' : 'needs research');
    return '<div class="acct-item' + (isActive ? ' active' : '') + '" onclick="selectAccount(' + "'" + a.id + "'" + ')">' +
      '<div class="acct-avatar" style="background:' + c[0] + ';color:' + c[1] + '">' + initials(a.name) + '</div>' +
      '<div style="min-width:0"><div class="acct-name">' + a.name + '</div><div class="acct-sub">' + sub + '</div></div>' +
      '</div>';
  }).join('');
}

async function selectAccount(id) {
  activeId = id;
  renderList();
  var a = await fetch('/api/accounts/' + id).then(function(r){return r.json();});
  showAccount(a);
}

function showAccount(a) {
  document.getElementById('empty-main').style.display = 'none';
  var view = document.getElementById('acct-view');
  view.style.display = 'flex';

  var idx = allAccounts.findIndex(function(x){return x.id === a.id;});
  var c = colorFor(idx);
  var av = document.getElementById('header-avatar');
  av.style.background = c[0]; av.style.color = c[1];
  av.textContent = initials(a.name);
  document.getElementById('header-name').textContent = a.name;

  var upd = a.lastUpdated ? new Date(a.lastUpdated).toLocaleDateString('en-US',{month:'short',day:'numeric',hour:'numeric',minute:'2-digit'}) : 'Never';
  var ai = [].concat(
    (a.research ? a.research.litigation || [] : []).filter(function(l){return !['Resolved','Settled','Dismissed'].includes(l.status);}),
    (a.research ? a.research.regulatory || [] : []).filter(function(r){return !['Resolved','Closed'].includes(r.status);})
  ).length;

  var meta = a.industry + ' <span style="color:#D1D5DB">·</span> ' + a.location + ' <span style="color:#D1D5DB">·</span> ';
  meta += a.research ? '<span class="badge green">Updated ' + upd + '</span>' : '<span class="badge amber">Needs research</span>';
  if (ai > 0) meta += ' <span style="color:#D1D5DB">·</span> <span class="badge red">' + ai + ' active issue' + (ai > 1 ? 's' : '') + '</span>';
  document.getElementById('header-meta').innerHTML = meta;

  var r = a.research || {};
  var tabDefs = [
    {id:'contacts', label:'Contacts', count:(r.contacts||[]).length},
    {id:'tech', label:'Technology', count:(r.tech||[]).length},
    {id:'counsel', label:'Counsel', count:(r.counsel||[]).length},
    {id:'alsp', label:'ALSPs', count:(r.alsp||[]).length + (r.flex||[]).length},
    {id:'litigation', label:'Litigation', count:(r.litigation||[]).length},
    {id:'regulatory', label:'Regulatory', count:(r.regulatory||[]).length},
    {id:'financial', label:'Financial Intel', count:null},
    {id:'triggers', label:'Sales Triggers', count:(r.sales_triggers||[]).length},
    {id:'outreach', label:'Outreach', count:null}
  ];

  document.getElementById('tabs').innerHTML = tabDefs.map(function(t) {
    return '<div class="tab' + (t.id === activeTab ? ' active' : '') + '" onclick="switchTab(' + "'" + t.id + "'" + ', this)">' +
      t.label + (t.count !== null ? '<span class="tab-count">' + t.count + '</span>' : '') + '</div>';
  }).join('');

  renderTab(activeTab, a);
}

function switchTab(tab, el) {
  activeTab = tab;
  document.querySelectorAll('.tab').forEach(function(t){t.classList.remove('active');});
  if (el) el.classList.add('active');
  fetch('/api/accounts/' + activeId).then(function(r){return r.json();}).then(function(a){renderTab(tab, a);});
}

function renderTab(tab, a) {
  var c = document.getElementById('tab-content');
  var r = a.research;
  var idx = allAccounts.findIndex(function(x){return x.id === a.id;});
  var col = colorFor(idx);

  if (!r) { c.innerHTML = emptyPanel('No research data yet', 'npm run research:account "' + a.name + '"'); return; }

  if (tab === 'contacts') {
    if (!r.contacts || !r.contacts.length) { c.innerHTML = emptyPanel('No contacts found'); return; }
    var html = (r.intel_summary ? intelBox(r.intel_summary) : '') + '<div class="section-label">Key legal contacts (' + r.contacts.length + ')</div><div class="contact-grid">';
    r.contacts.forEach(function(ct) {
      html += '<div class="contact-card">';
      html += '<div class="contact-top"><div class="contact-av" style="background:' + col[0] + ';color:' + col[1] + '">' + initials(ct.name) + '</div>';
      html += '<div><div class="contact-name">' + ct.name + '</div><div class="contact-title">' + ct.title + '</div></div></div>';
      html += '<span class="role-tag ' + roleClass(ct.tag) + '">' + ct.tag + '</span>';
      if (ct.confidence) html += ' <span class="' + confClass(ct.confidence) + '">' + ct.confidence + '</span>';
      if (ct.email) html += '<div class="contact-detail">@ ' + ct.email + '</div>';
      if (ct.linkedin) html += '<div class="contact-detail"><a href="https://' + ct.linkedin + '" target="_blank">LinkedIn</a></div>';
      if (ct.notes) html += '<div class="contact-detail" style="font-style:italic;color:#9CA3AF">' + ct.notes + '</div>';
      if (ct.confidence_reason) html += '<div class="contact-detail" style="color:#9CA3AF">' + ct.confidence_reason + '</div>';
      html += '</div>';
    });
    html += '</div>';
    c.innerHTML = html;

  } else if (tab === 'tech') {
    var html = (r.intel_summary ? intelBox(r.intel_summary) : '') + '<div class="section-label">Legal technology stack</div><div class="pill-row">';
    (r.tech || []).forEach(function(t){ html += '<span class="pill blue">' + t + '</span>'; });
    html += '</div>';
    c.innerHTML = html;

  } else if (tab === 'counsel') {
    if (!r.counsel || !r.counsel.length) { c.innerHTML = emptyPanel('No outside counsel data'); return; }
    var html = '<div class="section-label">Primary outside counsel</div>';
    (r.counsel || []).forEach(function(f){ html += '<div class="card" style="font-size:13px">' + f + '</div>'; });
    c.innerHTML = html;

  } else if (tab === 'alsp') {
    var ha = r.alsp && r.alsp.length, hf = r.flex && r.flex.length;
    if (!ha && !hf) { c.innerHTML = emptyPanel('No ALSP or flex talent data'); return; }
    var html = '';
    if (ha) { html += '<div class="section-label">ALSP relationships</div><div class="pill-row">'; r.alsp.forEach(function(x){ html += '<span class="pill teal">' + x + '</span>'; }); html += '</div>'; }
    if (hf) { html += '<div class="section-label">Flex talent</div><div class="pill-row">'; r.flex.forEach(function(x){ html += '<span class="pill purple">' + x + '</span>'; }); html += '</div>'; }
    c.innerHTML = html;

  } else if (tab === 'litigation') {
    if (!r.litigation || !r.litigation.length) { c.innerHTML = emptyPanel('No litigation data'); return; }
    var html = '<div class="section-label">Litigation (' + r.litigation.length + ')</div>';
    r.litigation.forEach(function(l) {
      html += '<div class="issue-row"><div class="issue-top"><span class="issue-title">' + l.type + (l.is_new ? '<span class="new-badge">NEW</span>' : '') + '</span>' + statusBadge(l.status) + '</div>';
      html += '<div class="issue-period">' + l.period + '</div><div class="issue-summary">' + l.summary + '</div>';
      html += '<div class="issue-counsel">Outside counsel: <strong>' + (l.counsel || 'Unknown') + '</strong></div></div>';
    });
    c.innerHTML = html;

  } else if (tab === 'regulatory') {
    if (!r.regulatory || !r.regulatory.length) { c.innerHTML = emptyPanel('No regulatory data'); return; }
    var html = '<div class="section-label">Regulatory issues (' + r.regulatory.length + ')</div>';
    r.regulatory.forEach(function(x) {
      html += '<div class="issue-row"><div class="issue-top"><span class="issue-title">' + x.type + (x.is_new ? '<span class="new-badge">NEW</span>' : '') + '</span>' + statusBadge(x.status) + '</div>';
      html += '<div class="issue-period">' + x.period + '</div><div class="issue-summary">' + x.summary + '</div>';
      html += '<div class="issue-counsel">Outside counsel: <strong>' + (x.counsel || 'Unknown') + '</strong></div></div>';
    });
    c.innerHTML = html;

  } else if (tab === 'financial') {
    var fi = r.financial_intel;
    if (!fi) { c.innerHTML = emptyPanel('No financial intel yet', 'npm run research:account "' + a.name + '"'); return; }
    var html = '<div class="section-label">Financial and strategic intelligence</div>';
    if (fi.latest_filing) html += '<div class="card"><div style="font-size:11px;font-weight:600;color:#9CA3AF;text-transform:uppercase;margin-bottom:4px">Latest filing</div><div style="font-size:13px">' + fi.latest_filing + '</div></div>';
    if (fi.cost_initiatives) html += '<div class="card" style="border-left:3px solid #B45309"><div style="font-size:11px;font-weight:600;color:#B45309;text-transform:uppercase;margin-bottom:4px">Cost initiatives</div><div style="font-size:13px">' + fi.cost_initiatives + '</div></div>';
    if (fi.earnings_signals) html += '<div class="card"><div style="font-size:11px;font-weight:600;color:#9CA3AF;text-transform:uppercase;margin-bottom:4px">Earnings signals</div><div style="font-size:13px">' + fi.earnings_signals + '</div></div>';
    if (fi.legal_risk_factors) html += '<div class="card"><div style="font-size:11px;font-weight:600;color:#9CA3AF;text-transform:uppercase;margin-bottom:4px">Legal risk factors (10-K)</div><div style="font-size:13px">' + fi.legal_risk_factors + '</div></div>';
    if (fi.ma_activity) html += '<div class="card" style="border-left:3px solid #1E56A0"><div style="font-size:11px;font-weight:600;color:#1E56A0;text-transform:uppercase;margin-bottom:4px">M&A activity</div><div style="font-size:13px">' + fi.ma_activity + '</div></div>';
    c.innerHTML = html;

  } else if (tab === 'triggers') {
    var tr = r.sales_triggers || [];
    var pc = r.personnel_changes || [];
    if (!tr.length && !pc.length) { c.innerHTML = emptyPanel('No sales triggers yet', 'npm run research:account "' + a.name + '"'); return; }
    var html = '';
    if (tr.length) {
      html += '<div class="section-label">Sales triggers (' + tr.length + ')</div>';
      tr.forEach(function(t){ html += '<div class="trigger-row">' + t + '</div>'; });
    }
    if (pc.length) {
      html += '<div class="section-label" style="margin-top:12px">Personnel changes</div>';
      pc.forEach(function(p){ html += '<div class="card"><div style="font-size:13px;font-weight:600;margin-bottom:3px">' + p.name + '</div><div style="font-size:12px;color:#6B7280;margin-bottom:5px">' + p.change + '</div><div style="font-size:12px;color:#0A7C6E">' + p.significance + '</div></div>'; });
    }
    c.innerHTML = html;

  } else if (tab === 'outreach') {
    c.innerHTML = '<div style="padding:20px;color:#9CA3AF;font-size:13px">Loading digest...</div>';
    fetch('/api/digest').then(function(r){return r.json();}).then(function(d) {
      if (d.message) { c.innerHTML = emptyPanel('No weekly digest yet', 'npm run digest:weekly'); return; }
      var p = (d.priority_accounts || []).find(function(x){return x.account_name && x.account_name.toLowerCase().includes(a.name.toLowerCase());});
      var q = (d.quick_touches || []).find(function(x){return x.account_name && x.account_name.toLowerCase().includes(a.name.toLowerCase());});
      var nf = (d.new_filings_alert || []).find(function(x){return x.account_name && x.account_name.toLowerCase().includes(a.name.toLowerCase());});
      var pw = (d.personnel_watch || []).find(function(x){return x.account_name && x.account_name.toLowerCase().includes(a.name.toLowerCase());});
      var html = '';
      if (d.week_summary) html += '<div class="intel-box"><div class="intel-label">This week</div><div class="intel-text">' + d.week_summary + '</div></div>';
      if (nf) html += '<div class="card" style="border-left:3px solid #991B1B;margin-bottom:12px"><div style="font-size:11px;font-weight:700;color:#991B1B;text-transform:uppercase;margin-bottom:4px">New Filing Alert</div><div style="font-size:13px;font-weight:600;margin-bottom:3px">' + nf.filing_type + '</div><div style="font-size:12px;color:#6B7280;margin-bottom:6px">' + nf.summary + '</div><div style="font-size:12px;color:#B45309">' + nf.suggested_action + '</div></div>';
      if (pw) html += '<div class="card" style="border-left:3px solid #0A7C6E;margin-bottom:12px"><div style="font-size:11px;font-weight:700;color:#0A7C6E;text-transform:uppercase;margin-bottom:4px">Personnel Watch</div><div style="font-size:13px;font-weight:600;margin-bottom:3px">' + pw.person + '</div><div style="font-size:12px;color:#6B7280;margin-bottom:4px">' + pw.change + '</div><div style="font-size:12px;color:#0A7C6E">Window: ' + pw.window + '</div></div>';
      if (p) {
        var urgCls = p.urgency === 'Critical' ? 'red' : p.urgency === 'High' ? 'amber' : 'blue';
        html += '<div class="section-label">Priority outreach</div><div class="card">';
        html += '<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px"><span style="width:22px;height:22px;border-radius:50%;background:#0F2240;color:#fff;font-size:10px;font-weight:700;display:inline-flex;align-items:center;justify-content:center">' + p.priority_rank + '</span>';
        html += '<strong>' + p.account_name + '</strong><span class="badge ' + urgCls + '">' + (p.urgency || '') + '</span></div>';
        html += '<p style="font-size:12px;color:#6B7280;margin-bottom:8px">' + p.trigger + '</p>';
        if (p.email) html += '<div style="background:#F9FAFB;border:1px solid #E5E7EB;border-radius:8px;padding:10px;font-size:12px;line-height:1.7"><strong>Subject: ' + p.email.subject + '</strong><br><br>' + p.email.body.replace(/\\n/g,'<br>') + '</div>';
        html += '</div>';
      } else {
        html += '<div class="empty-panel"><p>' + a.name + ' is not in this week top priorities</p></div>';
      }
      if (q) html += '<div class="section-label" style="margin-top:12px">Quick touch</div><div class="card" style="font-size:13px">' + q.action + '</div>';
      c.innerHTML = html;
    });
  }
}

init();
</script>
</body>
</html>
"""

# Write the complete file
with open(path, 'w') as f:
    f.write(api)
    f.write("\nconst HTML = " + repr(html) + ";\n")

print("Done — server.js written to " + path)
print("File size: " + str(os.path.getsize(path)) + " bytes")
print("")
print("Next steps:")
print("  pkill -f 'node src/index.js'")
print("  npm start")
print("  Open http://localhost:3000")
