import os

home = os.path.expanduser("~")
base = os.path.join(home, "legal-tracker")

# ── Step 1: Add account manager API endpoints to server.js ─
server_path = os.path.join(base, "src", "server.js")

with open(server_path, 'r') as f:
    server_content = f.read()

# Add account management API endpoints before the dashboard route
new_endpoints = '''
// ── Account Management API ──────────────────────────────────

app.get('/api/config/accounts', async (req, res) => {
  try {
    const { ACCOUNTS } = await import('../config/accounts.js');
    const allResearch = await getAllResearch();
    res.json(ACCOUNTS.map(a => ({
      ...a,
      hasData: !!allResearch[a.id],
      lastUpdated: db.data.lastUpdated?.[a.id] || null,
      contactCount: allResearch[a.id]?.contacts?.length || 0,
      activeIssues: [
        ...(allResearch[a.id]?.litigation || []).filter(l => !['Resolved','Settled','Dismissed'].includes(l.status)),
        ...(allResearch[a.id]?.regulatory || []).filter(r => !['Resolved','Closed'].includes(r.status)),
      ].length,
    })));
  } catch(e) {
    res.status(500).json({ error: e.message });
  }
});

app.post('/api/config/accounts', async (req, res) => {
  try {
    const { name, industry, location } = req.body;
    if (!name || !industry || !location) {
      return res.status(400).json({ error: 'name, industry, and location are required' });
    }
    const id = name.toLowerCase().replace(/[^a-z0-9]/g, '_').replace(/_+/g, '_').replace(/^_|_$/g, '');

    // Read current accounts file
    const fs = await import('fs');
    const path = await import('path');
    const { fileURLToPath } = await import('url');
    const __dirname = path.default.dirname(fileURLToPath(import.meta.url));
    const accountsPath = path.default.join(__dirname, '..', 'config', 'accounts.js');
    let fileContent = fs.default.readFileSync(accountsPath, 'utf8');

    // Check for duplicate
    if (fileContent.includes('"' + id + '"') || fileContent.includes("'" + id + "'")) {
      return res.status(409).json({ error: 'Account already exists: ' + name });
    }

    // Add new account before the closing ];
    const newEntry = '  { id: "' + id + '", name: "' + name + '", industry: "' + industry + '", location: "' + location + '" },';
    fileContent = fileContent.replace(/\n\];/, '\n' + newEntry + '\n];');
    fs.default.writeFileSync(accountsPath, fileContent);

    res.json({ success: true, account: { id, name, industry, location } });
  } catch(e) {
    res.status(500).json({ error: e.message });
  }
});

app.delete('/api/config/accounts/:id', async (req, res) => {
  try {
    const { id } = req.params;
    const fs = await import('fs');
    const path = await import('path');
    const { fileURLToPath } = await import('url');
    const __dirname = path.default.dirname(fileURLToPath(import.meta.url));
    const accountsPath = path.default.join(__dirname, '..', 'config', 'accounts.js');
    let fileContent = fs.default.readFileSync(accountsPath, 'utf8');

    // Remove the line containing this id
    const lines = fileContent.split('\\n');
    const filtered = lines.filter(line => !line.includes('"' + id + '"'));
    if (filtered.length === lines.length) {
      return res.status(404).json({ error: 'Account not found: ' + id });
    }
    fs.default.writeFileSync(accountsPath, filtered.join('\\n'));

    // Also remove from database
    await db.read();
    if (db.data.research) delete db.data.research[id];
    if (db.data.lastUpdated) delete db.data.lastUpdated[id];
    await db.write();

    res.json({ success: true, removed: id });
  } catch(e) {
    res.status(500).json({ error: e.message });
  }
});

'''

# Insert before the dashboard route
if "app.get('/', (req, res) => res.send(HTML));" in server_content:
    server_content = server_content.replace(
        "app.get('/', (req, res) => res.send(HTML));",
        new_endpoints + "app.get('/', (req, res) => res.send(HTML));"
    )
    with open(server_path, 'w') as f:
        f.write(server_content)
    print("Done — account manager API endpoints added to server.js")
else:
    print("Could not find insertion point in server.js — will add endpoints separately")

# ── Step 2: Create account manager HTML page ───────────────
manager_html_path = os.path.join(base, "src", "accountManager.js")

manager_html = '''// accountManager.js — Account manager UI HTML
export const ACCOUNT_MANAGER_HTML = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Account Manager — Legal Tracker</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&family=DM+Mono&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{--navy:#0F2240;--blue:#1E56A0;--bl:#EBF2FC;--teal:#0A7C6E;--tl:#E6F5F2;--amber:#B45309;--al:#FEF3C7;--red:#991B1B;--rl:#FEE2E2;--green:#166534;--gl:#DCFCE7;--g0:#F9FAFB;--g1:#F3F4F6;--g2:#E5E7EB;--g4:#9CA3AF;--g5:#6B7280;--g6:#4B5563;--g7:#374151;--g9:#111827;--f:"DM Sans",sans-serif;--mono:"DM Mono",monospace;--r:10px;--rl:14px}
body{font-family:var(--f);font-size:14px;color:var(--g9);background:var(--g0);min-height:100vh}
.topbar{height:52px;background:var(--navy);display:flex;align-items:center;padding:0 24px;gap:16px}
.topbar a{color:rgba(255,255,255,.6);text-decoration:none;font-size:13px;display:flex;align-items:center;gap:5px}
.topbar a:hover{color:#fff}
.topbar-title{font-size:15px;font-weight:600;color:#fff;margin-left:4px}
.container{max-width:900px;margin:0 auto;padding:28px 20px}
.page-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:24px}
.page-title{font-size:22px;font-weight:600;color:var(--g9);letter-spacing:-.02em}
.page-sub{font-size:13px;color:var(--g5);margin-top:3px}
.btn{display:inline-flex;align-items:center;gap:6px;padding:8px 14px;border-radius:var(--r);border:1px solid var(--g2);background:#fff;cursor:pointer;font-size:13px;font-weight:500;color:var(--g7);font-family:var(--f);transition:all .12s;text-decoration:none}
.btn:hover{background:var(--g0);border-color:var(--g4)}
.btn-primary{background:var(--blue);border-color:var(--blue);color:#fff}
.btn-primary:hover{background:#1a4d8f}
.btn-danger{background:var(--red);border-color:var(--red);color:#fff}
.btn-danger:hover{background:#7f1d1d}
.btn-sm{padding:5px 10px;font-size:12px}
.card{background:#fff;border:1px solid var(--g2);border-radius:var(--rl);padding:20px;margin-bottom:16px}
.card-title{font-size:14px;font-weight:600;color:var(--g9);margin-bottom:14px;display:flex;align-items:center;gap:7px}
.form-grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-bottom:14px}
.form-group label{display:block;font-size:12px;font-weight:500;color:var(--g6);margin-bottom:5px}
.form-group input,.form-group select{width:100%;padding:8px 11px;border:1px solid var(--g2);border-radius:var(--r);font-size:13px;font-family:var(--f);color:var(--g9);background:#fff;transition:border .12s}
.form-group input:focus,.form-group select:focus{outline:none;border-color:var(--blue)}
.search-bar{display:flex;align-items:center;gap:10px;margin-bottom:16px}
.search-bar input{flex:1;padding:8px 12px;border:1px solid var(--g2);border-radius:var(--r);font-size:13px;font-family:var(--f);color:var(--g9)}
.search-bar input:focus{outline:none;border-color:var(--blue)}
.account-table{width:100%;border-collapse:collapse}
.account-table th{padding:9px 12px;text-align:left;font-size:11px;font-weight:600;color:var(--g5);text-transform:uppercase;letter-spacing:.05em;border-bottom:1px solid var(--g2);background:var(--g0)}
.account-table td{padding:10px 12px;border-bottom:1px solid var(--g1);font-size:13px;vertical-align:middle}
.account-table tr:last-child td{border-bottom:none}
.account-table tr:hover td{background:var(--g0)}
.badge{display:inline-flex;align-items:center;font-size:10px;font-weight:500;padding:2px 7px;border-radius:20px}
.badge-green{background:var(--gl);color:var(--green)}
.badge-amber{background:var(--al);color:var(--amber)}
.badge-red{background:var(--rl);color:var(--red)}
.badge-blue{background:var(--bl);color:var(--blue)}
.stats-row{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:24px}
.stat{background:#fff;border:1px solid var(--g2);border-radius:var(--rl);padding:14px 16px}
.stat-num{font-size:26px;font-weight:600;letter-spacing:-.02em}
.stat-label{font-size:11px;color:var(--g4);margin-top:3px}
.toast{position:fixed;bottom:24px;right:24px;background:var(--navy);color:#fff;padding:12px 18px;border-radius:var(--r);font-size:13px;font-weight:500;opacity:0;transition:opacity .2s;pointer-events:none;z-index:1000}
.toast.show{opacity:1}
.toast.error{background:var(--red)}
.toast.success{background:var(--teal)}
.modal-overlay{position:fixed;inset:0;background:rgba(0,0,0,.35);display:flex;align-items:center;justify-content:center;z-index:500;opacity:0;pointer-events:none;transition:opacity .15s}
.modal-overlay.show{opacity:1;pointer-events:all}
.modal{background:#fff;border-radius:var(--rl);padding:22px;width:380px;box-shadow:0 20px 40px rgba(0,0,0,.15)}
.modal h3{font-size:15px;font-weight:600;margin-bottom:8px}
.modal p{font-size:13px;color:var(--g6);margin-bottom:16px;line-height:1.5}
.modal-actions{display:flex;justify-content:flex-end;gap:8px}
.industry-tag{font-size:11px;color:var(--g5)}
.empty-table{padding:32px;text-align:center;color:var(--g4);font-size:13px}
@keyframes fadeIn{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:translateY(0)}}
.account-table tbody tr{animation:fadeIn .12s ease}
</style>
</head>
<body>
<div class="topbar">
  <a href="/">&#8592; Dashboard</a>
  <span class="topbar-title">Account Manager</span>
</div>

<div class="container">
  <div class="page-header">
    <div>
      <div class="page-title">Manage accounts</div>
      <div class="page-sub">Add, remove, and organize your tracked accounts</div>
    </div>
    <button class="btn btn-primary" onclick="showAddForm()">+ Add account</button>
  </div>

  <div class="stats-row">
    <div class="stat"><div class="stat-num" id="stat-total">-</div><div class="stat-label">Total accounts</div></div>
    <div class="stat"><div class="stat-num" id="stat-researched">-</div><div class="stat-label">Researched</div></div>
    <div class="stat"><div class="stat-num" id="stat-pending">-</div><div class="stat-label">Pending research</div></div>
    <div class="stat"><div class="stat-num" id="stat-issues">-</div><div class="stat-label">Active issues</div></div>
  </div>

  <div class="card" id="add-form-card" style="display:none">
    <div class="card-title">+ Add new account</div>
    <div class="form-grid">
      <div class="form-group">
        <label>Company name *</label>
        <input id="new-name" placeholder="e.g. Acme Corporation" oninput="validateForm()">
      </div>
      <div class="form-group">
        <label>Industry *</label>
        <select id="new-industry">
          <option value="">Select industry...</option>
          <option>AI / ML</option>
          <option>Aerospace</option>
          <option>Agriculture / Commodities</option>
          <option>Analytics / Technology</option>
          <option>Cybersecurity</option>
          <option>E-commerce</option>
          <option>E-commerce / Delivery</option>
          <option>Energy / Nuclear</option>
          <option>Energy / Utilities</option>
          <option>Engineering / Construction</option>
          <option>Entertainment / Gaming</option>
          <option>Enterprise software</option>
          <option>Enterprise software / Data</option>
          <option>Financial services</option>
          <option>Financial software</option>
          <option>Fintech</option>
          <option>Gaming / Hospitality</option>
          <option>Healthcare / MedTech</option>
          <option>Hospitality</option>
          <option>IP / Patent</option>
          <option>IT services</option>
          <option>Logistics / Supply chain</option>
          <option>Manufacturing</option>
          <option>Mining / Natural resources</option>
          <option>Music / Entertainment</option>
          <option>Retail</option>
          <option>Retail / Consumer goods</option>
          <option>Retail / Food and Beverage</option>
          <option>Semiconductors</option>
          <option>Specialty chemicals</option>
          <option>Sports / Media</option>
          <option>Technology</option>
          <option>Technology / Infrastructure</option>
          <option>Technology / Social media</option>
          <option>Technology / Transportation</option>
          <option>Technology consulting</option>
          <option>Utility services</option>
          <option>Venture capital</option>
          <option>Other</option>
        </select>
      </div>
      <div class="form-group">
        <label>HQ location *</label>
        <input id="new-location" placeholder="e.g. San Francisco, CA" oninput="validateForm()">
      </div>
    </div>
    <div style="display:flex;gap:8px;align-items:center">
      <button class="btn btn-primary" id="add-btn" onclick="addAccount()" disabled>Add account</button>
      <button class="btn" onclick="hideAddForm()">Cancel</button>
      <span id="add-status" style="font-size:12px;color:var(--g5)"></span>
    </div>
  </div>

  <div class="card" style="padding:0;overflow:hidden">
    <div style="padding:14px 16px;border-bottom:1px solid var(--g2);display:flex;align-items:center;justify-content:space-between">
      <div style="font-size:14px;font-weight:600">All accounts</div>
      <div style="display:flex;gap:8px;align-items:center">
        <input id="search" placeholder="Search..." oninput="renderTable()" style="padding:6px 10px;border:1px solid var(--g2);border-radius:var(--r);font-size:12px;font-family:var(--f);width:180px">
        <select id="filter-status" onchange="renderTable()" style="padding:6px 10px;border:1px solid var(--g2);border-radius:var(--r);font-size:12px;font-family:var(--f)">
          <option value="">All status</option>
          <option value="researched">Researched</option>
          <option value="pending">Needs research</option>
        </select>
      </div>
    </div>
    <table class="account-table">
      <thead>
        <tr>
          <th>Company</th>
          <th>Industry</th>
          <th>Location</th>
          <th>Status</th>
          <th>Contacts</th>
          <th>Issues</th>
          <th>Last updated</th>
          <th></th>
        </tr>
      </thead>
      <tbody id="account-tbody"></tbody>
    </table>
  </div>
</div>

<div class="modal-overlay" id="confirm-modal">
  <div class="modal">
    <h3>Remove account?</h3>
    <p id="confirm-text">This will remove the account and all its research data from the tracker. This cannot be undone.</p>
    <div class="modal-actions">
      <button class="btn" onclick="hideConfirm()">Cancel</button>
      <button class="btn btn-danger" id="confirm-btn" onclick="confirmDelete()">Remove account</button>
    </div>
  </div>
</div>

<div class="toast" id="toast"></div>

<script>
var accounts = [];
var deleteId = null;
var deleteName = null;

async function init() {
  await loadAccounts();
}

async function loadAccounts() {
  try {
    var response = await fetch('/api/config/accounts');
    accounts = await response.json();
    updateStats();
    renderTable();
  } catch(e) {
    showToast('Failed to load accounts: ' + e.message, 'error');
  }
}

function updateStats() {
  var researched = accounts.filter(function(a) { return a.hasData; }).length;
  var pending = accounts.filter(function(a) { return !a.hasData; }).length;
  var issues = accounts.reduce(function(s,a) { return s + a.activeIssues; }, 0);
  document.getElementById('stat-total').textContent = accounts.length;
  document.getElementById('stat-researched').textContent = researched;
  document.getElementById('stat-pending').textContent = pending;
  document.getElementById('stat-issues').textContent = issues;
}

function renderTable() {
  var q = document.getElementById('search').value.toLowerCase();
  var statusFilter = document.getElementById('filter-status').value;
  var tbody = document.getElementById('account-tbody');

  var filtered = accounts.filter(function(a) {
    var matchQ = !q || a.name.toLowerCase().includes(q) || a.industry.toLowerCase().includes(q) || a.location.toLowerCase().includes(q);
    var matchStatus = !statusFilter ||
      (statusFilter === 'researched' && a.hasData) ||
      (statusFilter === 'pending' && !a.hasData);
    return matchQ && matchStatus;
  });

  if (!filtered.length) {
    tbody.innerHTML = '<tr><td colspan="8" class="empty-table">No accounts match your search</td></tr>';
    return;
  }

  tbody.innerHTML = filtered.map(function(a) {
    var updated = a.lastUpdated
      ? new Date(a.lastUpdated).toLocaleDateString('en-US', {month:'short', day:'numeric', year:'2-digit'})
      : '-';
    var statusBadge = a.hasData
      ? '<span class="badge badge-green">Researched</span>'
      : '<span class="badge badge-amber">Needs research</span>';
    var issuesBadge = a.activeIssues > 0
      ? '<span class="badge badge-red">' + a.activeIssues + '</span>'
      : '<span style="color:var(--g4)">-</span>';

    return '<tr>' +
      '<td><strong style="font-size:13px">' + a.name + '</strong></td>' +
      '<td><span class="industry-tag">' + a.industry + '</span></td>' +
      '<td style="color:var(--g5);font-size:12px">' + a.location + '</td>' +
      '<td>' + statusBadge + '</td>' +
      '<td style="font-size:13px;color:var(--g6)">' + (a.contactCount || '-') + '</td>' +
      '<td>' + issuesBadge + '</td>' +
      '<td style="font-size:12px;color:var(--g5)">' + updated + '</td>' +
      '<td>' +
        '<div style="display:flex;gap:5px">' +
          '<a href="/?account=' + a.id + '" class="btn btn-sm" title="View in dashboard">View</a>' +
          '<button class="btn btn-sm" onclick="researchAccount(' + "'" + a.id + "','" + a.name + "'" + ')" title="Research this account">Research</button>' +
          '<button class="btn btn-sm" style="color:var(--red);border-color:var(--rl)" onclick="showConfirm(' + "'" + a.id + "','" + a.name.replace(/'/g, "\\'") + "'" + ')" title="Remove account">Remove</button>' +
        '</div>' +
      '</td>' +
      '</tr>';
  }).join('');
}

function showAddForm() {
  document.getElementById('add-form-card').style.display = 'block';
  document.getElementById('new-name').focus();
}

function hideAddForm() {
  document.getElementById('add-form-card').style.display = 'none';
  document.getElementById('new-name').value = '';
  document.getElementById('new-industry').value = '';
  document.getElementById('new-location').value = '';
  document.getElementById('add-status').textContent = '';
}

function validateForm() {
  var name = document.getElementById('new-name').value.trim();
  var industry = document.getElementById('new-industry').value;
  var location = document.getElementById('new-location').value.trim();
  document.getElementById('add-btn').disabled = !(name && industry && location);
}

async function addAccount() {
  var name = document.getElementById('new-name').value.trim();
  var industry = document.getElementById('new-industry').value;
  var location = document.getElementById('new-location').value.trim();

  if (!name || !industry || !location) return;

  var btn = document.getElementById('add-btn');
  var status = document.getElementById('add-status');
  btn.disabled = true;
  btn.textContent = 'Adding...';
  status.textContent = '';

  try {
    var response = await fetch('/api/config/accounts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, industry, location }),
    });
    var data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || 'Failed to add account');
    }

    showToast(name + ' added successfully', 'success');
    hideAddForm();
    await loadAccounts();
    status.textContent = 'To research: npm run research:account "' + name + '"';

  } catch(e) {
    showToast(e.message, 'error');
    status.textContent = e.message;
  } finally {
    btn.disabled = false;
    btn.textContent = 'Add account';
    validateForm();
  }
}

function showConfirm(id, name) {
  deleteId = id;
  deleteName = name;
  document.getElementById('confirm-text').textContent =
    'Remove "' + name + '" from your tracker? This will delete all research data for this account. This cannot be undone.';
  document.getElementById('confirm-modal').classList.add('show');
}

function hideConfirm() {
  document.getElementById('confirm-modal').classList.remove('show');
  deleteId = null;
  deleteName = null;
}

async function confirmDelete() {
  if (!deleteId) return;
  var btn = document.getElementById('confirm-btn');
  btn.textContent = 'Removing...';
  btn.disabled = true;

  try {
    var response = await fetch('/api/config/accounts/' + deleteId, { method: 'DELETE' });
    var data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Failed to remove');
    showToast(deleteName + ' removed', 'success');
    hideConfirm();
    await loadAccounts();
  } catch(e) {
    showToast(e.message, 'error');
  } finally {
    btn.textContent = 'Remove account';
    btn.disabled = false;
  }
}

async function researchAccount(id, name) {
  showToast('Run in terminal: npm run research:account "' + name + '"', '');
}

function showToast(msg, type) {
  var toast = document.getElementById('toast');
  toast.textContent = msg;
  toast.className = 'toast show' + (type ? ' ' + type : '');
  setTimeout(function() { toast.classList.remove('show'); }, 3500);
}

init();
</script>
</body>
</html>`;
''';

with open(manager_html_path, 'w') as f:
    f.write(manager_html)
print("Done — accountManager.js written")

# ── Step 3: Add /manage route to server.js ─────────────────
with open(server_path, 'r') as f:
    server_content = f.read()

manage_route = """
app.get('/manage', async (req, res) => {
  const { ACCOUNT_MANAGER_HTML } = await import('./accountManager.js');
  res.send(ACCOUNT_MANAGER_HTML);
});

"""

if "app.get('/manage'" not in server_content:
    server_content = server_content.replace(
        "app.get('/', (req, res) => res.send(HTML));",
        manage_route + "app.get('/', (req, res) => res.send(HTML));"
    )
    with open(server_path, 'w') as f:
        f.write(server_content)
    print("Done — /manage route added to server.js")
else:
    print("Skipped — /manage route already exists")

print("")
print("=" * 50)
print("ACCOUNT MANAGER INSTALLED")
print("=" * 50)
print("")
print("After restarting the tracker:")
print("  pkill -f 'node src/index.js'")
print("  npm start")
print("")
print("Open in browser:")
print("  http://localhost:3000/manage")
print("")
print("Features:")
print("  - Add accounts with name, industry, location")
print("  - Remove accounts with one click + confirmation")
print("  - Search and filter your account list")
print("  - See research status, contact count, active issues")
print("  - Direct link back to dashboard for each account")
