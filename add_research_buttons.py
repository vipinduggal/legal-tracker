import os

home = os.path.expanduser("~")
base = os.path.join(home, "legal-tracker")

# ── Step 1: Add research API endpoint to accountRoutes.js ──
routes_path = os.path.join(base, "src", "accountRoutes.js")

with open(routes_path, 'r') as f:
    content = f.read()

research_endpoint = """
  // POST — trigger research for one account in background
  app.post('/api/research/:id', async (req, res) => {
    try {
      const id = req.params.id;
      const ACCOUNTS = readAccountsFromFile();
      const account = ACCOUNTS.find(a => a.id === id);
      if (!account) return res.status(404).json({ error: 'Account not found: ' + id });

      // Respond immediately — research runs in background
      res.json({ success: true, message: 'Research started for ' + account.name });

      // Background research (non-blocking)
      setImmediate(async () => {
        try {
          const { researchAccount, detectChanges } = await import('../researcher.js');
          const { getResearch, setResearch, logRun } = await import('../db.js');
          const { sendAccountUpdateEmail } = await import('../emailer.js');
          const { postAccountUpdateToTeams } = await import('../teams.js');
          const oldData = await getResearch(id);
          const newData = await researchAccount(account);
          if (newData) {
            const changes = detectChanges(oldData, newData);
            await setResearch(id, newData);
            const hasChanges = !oldData || changes.some(c => !c.includes('No significant'));
            if (hasChanges) {
              await Promise.allSettled([
                sendAccountUpdateEmail(account, changes, newData),
                postAccountUpdateToTeams(account, changes, newData),
              ]);
            }
            await logRun({ job: 'manual_research', account: account.name, success: true });
          }
        } catch(err) {
          console.error('Background research failed for ' + account.name + ':', err.message);
        }
      });

    } catch(e) {
      res.status(500).json({ error: e.message });
    }
  });

  // GET — check research status for one account
  app.get('/api/research/:id/status', async (req, res) => {
    try {
      const id = req.params.id;
      await db.read();
      res.json({
        id,
        hasData: !!db.data.research?.[id],
        lastUpdated: db.data.lastUpdated?.[id] || null,
      });
    } catch(e) {
      res.status(500).json({ error: e.message });
    }
  });

"""

if 'api/research' not in content:
    content = content.replace(
        "  app.get('/manage'",
        research_endpoint + "  app.get('/manage'"
    )
    with open(routes_path, 'w') as f:
        f.write(content)
    print("Done — research API endpoints added to accountRoutes.js")
else:
    print("Skipped — research endpoints already exist")

# ── Step 2: Write a fresh accountManager.js with research buttons ──
manager_path = os.path.join(base, "src", "accountManager.js")

# Write the HTML to a temp file then read it to avoid escaping
html_path = os.path.join(base, "src", "manager_temp.html")

with open(html_path, 'w') as f:
    f.write("""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Account Manager</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&family=DM+Mono&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{--navy:#0F2240;--blue:#1E56A0;--bl:#EBF2FC;--teal:#0A7C6E;--tl:#E6F5F2;--amber:#B45309;--al:#FEF3C7;--red:#991B1B;--rl:#FEE2E2;--green:#166534;--gl:#DCFCE7;--g0:#F9FAFB;--g1:#F3F4F6;--g2:#E5E7EB;--g4:#9CA3AF;--g5:#6B7280;--g6:#4B5563;--g7:#374151;--g9:#111827;--f:"DM Sans",sans-serif;--r:10px;--rl:14px}
body{font-family:var(--f);font-size:14px;color:var(--g9);background:var(--g0);min-height:100vh}
.tb{height:52px;background:var(--navy);display:flex;align-items:center;padding:0 20px;gap:16px}
.tb a{color:rgba(255,255,255,.7);text-decoration:none;font-size:13px}
.tb a:hover{color:#fff}
.tb-t{font-size:15px;font-weight:600;color:#fff}
.wrap{max-width:1000px;margin:0 auto;padding:28px 20px}
.ph{display:flex;align-items:center;justify-content:space-between;margin-bottom:20px}
.pt{font-size:20px;font-weight:600;color:var(--g9)}
.ps{font-size:13px;color:var(--g5);margin-top:3px}
.btn{display:inline-flex;align-items:center;gap:5px;padding:7px 13px;border-radius:var(--r);border:1px solid var(--g2);background:#fff;cursor:pointer;font-size:13px;font-weight:500;color:var(--g7);font-family:var(--f);transition:all .12s}
.btn:hover{background:var(--g0);border-color:var(--g4)}
.btn:disabled{opacity:.5;cursor:not-allowed}
.btn-p{background:var(--blue);border-color:var(--blue);color:#fff}
.btn-p:hover{background:#1a4d8f}
.btn-d{color:var(--red);border-color:var(--rl)}
.btn-d:hover{background:var(--rl)}
.btn-sm{padding:4px 9px;font-size:12px}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px}
.sc{background:#fff;border:1px solid var(--g2);border-radius:var(--rl);padding:14px 16px}
.sn{font-size:26px;font-weight:600;letter-spacing:-.02em}
.sl{font-size:11px;color:var(--g4);margin-top:3px}
.card{background:#fff;border:1px solid var(--g2);border-radius:var(--rl);overflow:hidden;margin-bottom:16px}
.card-hdr{padding:12px 16px;border-bottom:1px solid var(--g2);display:flex;align-items:center;justify-content:space-between;gap:12px}
.card-hdr-t{font-size:14px;font-weight:600}
.filters{display:flex;gap:8px;align-items:center}
.filters input{padding:6px 10px;border:1px solid var(--g2);border-radius:var(--r);font-size:12px;font-family:var(--f);width:180px}
.filters select{padding:6px 10px;border:1px solid var(--g2);border-radius:var(--r);font-size:12px;font-family:var(--f)}
.add-form{padding:16px;border-bottom:1px solid var(--g2);background:var(--g0);display:none}
.form-row{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-bottom:12px}
.fg label{display:block;font-size:12px;font-weight:500;color:var(--g6);margin-bottom:4px}
.fg input,.fg select{width:100%;padding:7px 10px;border:1px solid var(--g2);border-radius:var(--r);font-size:13px;font-family:var(--f);color:var(--g9)}
.fg input:focus,.fg select:focus{outline:none;border-color:var(--blue)}
.reminder{display:none;background:var(--tl);border:1px solid #A7D7D0;border-radius:var(--r);padding:11px 14px;margin:0 16px 12px;font-size:13px;color:var(--teal);font-weight:500}
table{width:100%;border-collapse:collapse}
th{padding:8px 12px;text-align:left;font-size:11px;font-weight:600;color:var(--g5);border-bottom:1px solid var(--g2);background:var(--g0);text-transform:uppercase;letter-spacing:.04em}
td{padding:9px 12px;border-bottom:1px solid var(--g1);font-size:13px;vertical-align:middle}
tr:last-child td{border-bottom:none}
tr:hover td{background:var(--g0)}
.bdg{display:inline-flex;font-size:10px;font-weight:500;padding:2px 7px;border-radius:20px}
.bg{background:var(--gl);color:var(--green)}
.ba{background:var(--al);color:var(--amber)}
.br{background:var(--rl);color:var(--red)}
.ind{font-size:11px;color:var(--g5)}
.btn-row{display:flex;gap:5px;flex-wrap:nowrap}
.modal-bg{position:fixed;inset:0;background:rgba(0,0,0,.3);display:flex;align-items:center;justify-content:center;z-index:100;opacity:0;pointer-events:none;transition:opacity .15s}
.modal-bg.show{opacity:1;pointer-events:all}
.modal{background:#fff;border-radius:var(--rl);padding:22px;width:360px;box-shadow:0 20px 40px rgba(0,0,0,.15)}
.modal h3{font-size:15px;font-weight:600;margin-bottom:8px}
.modal p{font-size:13px;color:var(--g6);margin-bottom:16px;line-height:1.5}
.modal-act{display:flex;justify-content:flex-end;gap:8px}
.toast{position:fixed;bottom:24px;right:24px;background:var(--navy);color:#fff;padding:11px 16px;border-radius:var(--r);font-size:13px;font-weight:500;opacity:0;transition:opacity .2s;pointer-events:none;z-index:200}
.toast.show{opacity:1}
.toast.ok{background:var(--teal)}
.toast.err{background:var(--red)}
</style>
</head>
<body>
<div class="tb">
  <a href="/">&#8592; Dashboard</a>
  <span class="tb-t">Account Manager</span>
</div>
<div class="wrap">
  <div class="ph">
    <div><div class="pt">Manage accounts</div><div class="ps">Add, remove, and research your tracked accounts</div></div>
    <div style="display:flex;gap:8px">
      <button class="btn" onclick="researchAllPending()" id="rap-btn">&#128269; Research pending</button>
      <button class="btn btn-p" onclick="toggleAdd()">+ Add account</button>
    </div>
  </div>
  <div class="stats">
    <div class="sc"><div class="sn" id="st-tot">-</div><div class="sl">Total accounts</div></div>
    <div class="sc"><div class="sn" id="st-res">-</div><div class="sl">Researched</div></div>
    <div class="sc"><div class="sn" id="st-pen">-</div><div class="sl">Needs research</div></div>
    <div class="sc"><div class="sn" id="st-iss">-</div><div class="sl">Active issues</div></div>
  </div>
  <div class="card">
    <div class="add-form" id="add-form">
      <div class="form-row">
        <div class="fg"><label>Company name *</label><input id="nn" placeholder="e.g. Acme Corporation" oninput="validateAdd()"></div>
        <div class="fg"><label>Industry *</label>
          <select id="ni" onchange="validateAdd()">
            <option value="">Select...</option>
            <option>AI / ML</option><option>Aerospace</option><option>Agriculture / Commodities</option>
            <option>Analytics / Technology</option><option>Cybersecurity</option><option>E-commerce</option>
            <option>E-commerce / Delivery</option><option>Energy / Nuclear</option><option>Energy / Utilities</option>
            <option>Engineering / Construction</option><option>Enterprise software</option><option>Entertainment / Gaming</option>
            <option>Financial services</option><option>Financial software</option><option>Fintech</option>
            <option>Gaming / Hospitality</option><option>Healthcare / MedTech</option><option>Hospitality</option>
            <option>IP / Patent</option><option>IT services</option><option>Logistics / Supply chain</option>
            <option>Manufacturing</option><option>Mining / Natural resources</option><option>Music / Entertainment</option>
            <option>Retail</option><option>Retail / Consumer goods</option><option>Retail / Food and Beverage</option>
            <option>Semiconductors</option><option>Specialty chemicals</option><option>Sports / Media</option>
            <option>Technology</option><option>Technology / Infrastructure</option><option>Technology / Social media</option>
            <option>Technology / Transportation</option><option>Technology consulting</option>
            <option>Utility services</option><option>Venture capital</option><option>Other</option>
          </select>
        </div>
        <div class="fg"><label>HQ location *</label><input id="nl" placeholder="e.g. San Francisco, CA" oninput="validateAdd()"></div>
      </div>
      <div style="display:flex;gap:8px;align-items:center">
        <button class="btn btn-p" id="add-btn" onclick="addAccount()" disabled>Add account</button>
        <button class="btn" onclick="toggleAdd()">Cancel</button>
      </div>
    </div>
    <div class="reminder" id="reminder"></div>
    <div class="card-hdr">
      <div class="card-hdr-t">All accounts</div>
      <div class="filters">
        <input placeholder="Search..." oninput="renderTable()" id="srch">
        <select onchange="renderTable()" id="sf">
          <option value="">All</option>
          <option value="researched">Researched</option>
          <option value="pending">Needs research</option>
        </select>
      </div>
    </div>
    <table>
      <thead><tr>
        <th>Company</th><th>Industry</th><th>Location</th>
        <th>Status</th><th>Contacts</th><th>Issues</th><th>Updated</th><th>Actions</th>
      </tr></thead>
      <tbody id="tbody"></tbody>
    </table>
  </div>
</div>
<div class="modal-bg" id="modal">
  <div class="modal">
    <h3>Remove account?</h3>
    <p id="modal-txt"></p>
    <div class="modal-act">
      <button class="btn" onclick="closeModal()">Cancel</button>
      <button class="btn btn-d" id="modal-ok" onclick="doDelete()">Remove</button>
    </div>
  </div>
</div>
<div class="toast" id="toast"></div>
<script>
var accounts=[], delId=null, delName=null;
async function init(){await load();}
async function load(){
  var r=await fetch('/api/config/accounts').then(function(r){return r.json();});
  accounts=r;
  document.getElementById('st-tot').textContent=r.length;
  document.getElementById('st-res').textContent=r.filter(function(a){return a.hasData;}).length;
  document.getElementById('st-pen').textContent=r.filter(function(a){return !a.hasData;}).length;
  document.getElementById('st-iss').textContent=r.reduce(function(s,a){return s+(a.activeIssues||0);},0);
  renderTable();
}
function renderTable(){
  var q=document.getElementById('srch').value.toLowerCase();
  var sf=document.getElementById('sf').value;
  var f=accounts.filter(function(a){
    var mq=!q||a.name.toLowerCase().includes(q)||a.industry.toLowerCase().includes(q)||a.location.toLowerCase().includes(q);
    var ms=!sf||(sf==='researched'&&a.hasData)||(sf==='pending'&&!a.hasData);
    return mq&&ms;
  });
  var tb=document.getElementById('tbody');
  if(!f.length){tb.innerHTML='<tr><td colspan="8" style="padding:24px;text-align:center;color:#9CA3AF">No accounts match</td></tr>';return;}
  tb.innerHTML=f.map(function(a){
    var upd=a.lastUpdated?new Date(a.lastUpdated).toLocaleDateString('en-US',{month:'short',day:'numeric',year:'2-digit'}):'Never';
    var sbdg=a.hasData?'<span class="bdg bg">Researched</span>':'<span class="bdg ba">Needs research</span>';
    var ibdg=a.activeIssues>0?'<span class="bdg br">'+a.activeIssues+'</span>':'-';
    var rLabel=a.hasData?'&#8635; Update':'&#128269; Research';
    return '<tr id="row-'+a.id+'">'
      +'<td><strong>'+a.name+'</strong></td>'
      +'<td><span class="ind">'+a.industry+'</span></td>'
      +'<td style="color:var(--g5);font-size:12px">'+a.location+'</td>'
      +'<td id="st-'+a.id+'">'+sbdg+'</td>'
      +'<td>'+(a.contactCount||'-')+'</td>'
      +'<td>'+ibdg+'</td>'
      +'<td style="font-size:12px;color:var(--g5)" id="upd-'+a.id+'">'+upd+'</td>'
      +'<td><div class="btn-row">'
        +'<a href="/" class="btn btn-sm">View</a>'
        +'<button class="btn btn-sm" id="rb-'+a.id+'" onclick="doResearch(\''+a.id+'\',\''+a.name.replace(/'/g,"\\'")+'\')" >'+rLabel+'</button>'
        +'<button class="btn btn-sm btn-d" onclick="showModal(\''+a.id+'\',\''+a.name.replace(/'/g,"\\'")+'\')">Remove</button>'
      +'</div></td>'
      +'</tr>';
  }).join('');
}
function toggleAdd(){
  var f=document.getElementById('add-form');
  f.style.display=f.style.display==='block'?'none':'block';
  if(f.style.display==='block')document.getElementById('nn').focus();
}
function validateAdd(){
  var ok=document.getElementById('nn').value.trim()&&document.getElementById('ni').value&&document.getElementById('nl').value.trim();
  document.getElementById('add-btn').disabled=!ok;
}
async function addAccount(){
  var name=document.getElementById('nn').value.trim();
  var industry=document.getElementById('ni').value;
  var location=document.getElementById('nl').value.trim();
  var btn=document.getElementById('add-btn');
  btn.disabled=true;btn.textContent='Adding...';
  try{
    var r=await fetch('/api/config/accounts',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,industry,location})});
    var d=await r.json();
    if(!r.ok)throw new Error(d.error||'Failed');
    toast(name+' added!','ok');
    document.getElementById('nn').value='';document.getElementById('ni').value='';document.getElementById('nl').value='';
    toggleAdd();
    var rem=document.getElementById('reminder');
    rem.textContent='Added: '+name+'. Click Research to start research, or it will run automatically at 7 AM tomorrow.';
    rem.style.display='block';
    setTimeout(function(){rem.style.display='none';},8000);
    await load();
  }catch(e){toast(e.message,'err');}
  finally{btn.disabled=false;btn.textContent='Add account';}
}
async function doResearch(id,name){
  var btn=document.getElementById('rb-'+id);
  if(!btn)return;
  btn.disabled=true;
  btn.textContent='Researching...';
  var start=Date.now();
  try{
    var r=await fetch('/api/research/'+id,{method:'POST'});
    var d=await r.json();
    if(!r.ok)throw new Error(d.error||'Failed');
    toast('Research started for '+name+'. Check email in 2-3 min.','ok');
    // Poll for completion
    var timer=setInterval(async function(){
      try{
        var sr=await fetch('/api/research/'+id+'/status').then(function(r){return r.json();});
        var elapsed=Math.round((Date.now()-start)/1000);
        if(btn)btn.textContent=elapsed+'s...';
        if(sr.lastUpdated&&new Date(sr.lastUpdated)>new Date(start-3000)){
          clearInterval(timer);
          toast(name+' research complete!','ok');
          var st=document.getElementById('st-'+id);
          if(st)st.innerHTML='<span class="bdg bg">Researched</span>';
          var ud=document.getElementById('upd-'+id);
          if(ud)ud.textContent=new Date(sr.lastUpdated).toLocaleDateString('en-US',{month:'short',day:'numeric',year:'2-digit'});
          btn.disabled=false;btn.textContent='&#8635; Update';
        }
        if(elapsed>300){clearInterval(timer);btn.disabled=false;btn.textContent='&#8635; Update';}
      }catch(e){clearInterval(timer);btn.disabled=false;btn.textContent='&#8635; Update';}
    },8000);
  }catch(e){
    toast(e.message,'err');
    btn.disabled=false;btn.textContent=accounts.find(function(a){return a.id===id;})?.hasData?'&#8635; Update':'&#128269; Research';
  }
}
async function researchAllPending(){
  var pending=accounts.filter(function(a){return !a.hasData;});
  if(!pending.length){toast('No pending accounts','');return;}
  var btn=document.getElementById('rap-btn');
  btn.disabled=true;btn.textContent='Queuing '+pending.length+'...';
  toast('Queuing research for '+pending.length+' accounts...','ok');
  for(var i=0;i<pending.length;i++){
    try{await fetch('/api/research/'+pending[i].id,{method:'POST'});}catch(e){}
    await new Promise(function(r){setTimeout(r,800);});
  }
  btn.disabled=false;btn.textContent='&#128269; Research pending';
  toast('All '+pending.length+' accounts queued. Check email for updates.','ok');
}
function showModal(id,name){delId=id;delName=name;document.getElementById('modal-txt').textContent='Remove "'+name+'" and all its research data? This cannot be undone.';document.getElementById('modal').classList.add('show');}
function closeModal(){document.getElementById('modal').classList.remove('show');delId=null;delName=null;}
async function doDelete(){
  var btn=document.getElementById('modal-ok');btn.disabled=true;btn.textContent='Removing...';
  try{
    var r=await fetch('/api/config/accounts/'+delId,{method:'DELETE'});
    var d=await r.json();
    if(!r.ok)throw new Error(d.error||'Failed');
    toast(delName+' removed','ok');closeModal();await load();
  }catch(e){toast(e.message,'err');}
  finally{btn.disabled=false;btn.textContent='Remove';}
}
function toast(msg,type){
  var t=document.getElementById('toast');
  t.textContent=msg;t.className='toast show'+(type?' '+type:'');
  setTimeout(function(){t.classList.remove('show');},3500);
}
init();
</script>
</body>
</html>""")

print("Done — manager HTML written to temp file")

# Read it and write to accountManager.js
with open(html_path, 'r') as f:
    html_content = f.read()

os.remove(html_path)

with open(manager_path, 'w') as f:
    f.write("// accountManager.js\nexport const ACCOUNT_MANAGER_HTML = " + repr(html_content) + ";\n")

print("Done — accountManager.js written")
print("")
print("Restart: pkill -f 'node src/index.js' && npm start")
print("Then open: http://localhost:3000/manage")
