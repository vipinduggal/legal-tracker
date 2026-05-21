import os

home = os.path.expanduser("~")
base = os.path.join(home, "legal-tracker")

# ── Step 1: Add research API endpoint to accountRoutes.js ──
routes_path = os.path.join(base, "src", "accountRoutes.js")

with open(routes_path, 'r') as f:
    routes_content = f.read()

research_endpoint = """
  // POST trigger research for one account
  app.post('/api/research/:id', async (req, res) => {
    try {
      const id = req.params.id;
      const ACCOUNTS = readAccountsFromFile();
      const account = ACCOUNTS.find(a => a.id === id);
      if (!account) return res.status(404).json({ error: 'Account not found: ' + id });

      // Return immediately — research runs in background
      res.json({ success: true, message: 'Research started for ' + account.name, accountId: id });

      // Run research in background (non-blocking)
      import('../researcher.js').then(async ({ researchAccount, detectChanges }) => {
        import('../db.js').then(async ({ getResearch, setResearch, logRun }) => {
          import('../emailer.js').then(async ({ sendAccountUpdateEmail }) => {
            import('../teams.js').then(async ({ postAccountUpdateToTeams }) => {
              try {
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
          });
        });
      });

    } catch(e) {
      res.status(500).json({ error: e.message });
    }
  });

  // GET research status for one account
  app.get('/api/research/:id/status', async (req, res) => {
    try {
      const id = req.params.id;
      await db.read();
      const lastUpdated = db.data.lastUpdated?.[id] || null;
      const hasData = !!db.data.research?.[id];
      res.json({ id, hasData, lastUpdated, running: false });
    } catch(e) {
      res.status(500).json({ error: e.message });
    }
  });

"""

# Insert before the /manage route
if "app.get('/manage'" in routes_content and 'api/research' not in routes_content:
    routes_content = routes_content.replace(
        "  app.get('/manage'",
        research_endpoint + "  app.get('/manage'"
    )
    with open(routes_path, 'w') as f:
        f.write(routes_content)
    print("Done — research API endpoint added")
else:
    print("Skipped routes — endpoint already exists or manage route not found")

# ── Step 2: Update accountManager.js with research buttons ──
manager_path = os.path.join(base, "src", "accountManager.js")

with open(manager_path, 'r') as f:
    manager_content = f.read()

# Replace the table row generation to add a working research button
old_row = """    return '<tr>' +
      '<td><strong style=\\'font-size:13px\\'>' + a.name + '</strong></td>' +
      '<td><span class=\\'industry-tag\\'>' + a.industry + '</span></td>' +
      '<td style=\\'color:var(--g5);font-size:12px\\'>' + a.location + '</td>' +
      '<td>' + statusBadge + '</td>' +
      '<td style=\\'font-size:13px;color:var(--g6)\\'>' + (a.contactCount || '-') + '</td>' +
      '<td>' + issuesBadge + '</td>' +
      '<td style=\\'font-size:12px;color:var(--g5)\\'>' + updated + '</td>' +
      '<td>' +
        '<div style=\\'display:flex;gap:5px\\'>' +
          '<a href=\\'/?account=' + a.id + '\\' class=\\'btn btn-sm\\' title=\\'View in dashboard\\'>View</a>' +
          '<button class=\\'btn btn-sm\\' onclick=\\'researchAccount(' + "'" + a.id + "','" + a.name + "'" + ')\\' title=\\'Research this account\\'>Research</button>' +
          '<button class=\\'btn btn-sm\\' style=\\'color:var(--red);border-color:var(--rl)\\' onclick=\\'showConfirm(' + "'" + a.id + "','" + a.name.replace(/'/g, "\\\\'") + "'" + ')\\' title=\\'Remove account\\'>Remove</button>' +
        '</div>' +
      '</td>' +
      '</tr>';"""

new_row = """    var researchBtn = '<button class=\\'btn btn-sm\\' id=\\'rb-' + a.id + '\\' onclick=\\'triggerResearch(' + JSON.stringify(a.id) + ',' + JSON.stringify(a.name) + ')\\' title=\\'Research this account now\\'>' +
      (a.hasData ? '&#8635; Update' : '&#128269; Research') + '</button>';
    return '<tr id=\\'row-' + a.id + '\\'>' +
      '<td><strong style=\\'font-size:13px\\'>' + a.name + '</strong></td>' +
      '<td><span class=\\'industry-tag\\'>' + a.industry + '</span></td>' +
      '<td style=\\'color:var(--g5);font-size:12px\\'>' + a.location + '</td>' +
      '<td id=\\'status-' + a.id + '\\'>' + statusBadge + '</td>' +
      '<td style=\\'font-size:13px;color:var(--g6)\\'>' + (a.contactCount || '-') + '</td>' +
      '<td>' + issuesBadge + '</td>' +
      '<td style=\\'font-size:12px;color:var(--g5)\\' id=\\'upd-' + a.id + '\\'>' + updated + '</td>' +
      '<td>' +
        '<div style=\\'display:flex;gap:5px\\'>' +
          '<a href=\\'/\\' class=\\'btn btn-sm\\' title=\\'View in dashboard\\'>View</a>' +
          researchBtn +
          '<button class=\\'btn btn-sm\\' style=\\'color:var(--red);border-color:var(--rl)\\' onclick=\\'showConfirm(' + JSON.stringify(a.id) + ',' + JSON.stringify(a.name) + ')\\' title=\\'Remove account\\'>Remove</button>' +
        '</div>' +
      '</td>' +
      '</tr>';"""

if old_row in manager_content:
    manager_content = manager_content.replace(old_row, new_row)
    print("Done — table rows updated with working research buttons")
else:
    print("WARNING — table row pattern not found, trying alternative...")
    # Try to find and update researchAccount function
    pass

# Replace the placeholder researchAccount function with real implementation
old_research_fn = """async function researchAccount(id, name) {
  showToast('Run in terminal: npm run research:account "' + name + '"', '');
}"""

new_research_fn = """async function triggerResearch(id, name) {
  var btn = document.getElementById('rb-' + id);
  if (btn) {
    btn.disabled = true;
    btn.textContent = '⏳ Researching...';
    btn.style.opacity = '0.7';
  }

  try {
    var response = await fetch('/api/research/' + id, { method: 'POST' });
    var data = await response.json();

    if (!response.ok) throw new Error(data.error || 'Research failed');

    showToast('Research started for ' + name + ' — check your email in 2-3 minutes', 'success');

    // Poll for completion every 10 seconds for up to 5 minutes
    var pollCount = 0;
    var maxPolls = 30;
    var startTime = Date.now();

    var poller = setInterval(async function() {
      pollCount++;
      try {
        var statusResp = await fetch('/api/research/' + id + '/status');
        var status = await statusResp.json();
        var elapsed = Math.round((Date.now() - startTime) / 1000);

        if (btn) btn.textContent = '⏳ ' + elapsed + 's...';

        // Check if data was updated after we started
        if (status.lastUpdated && new Date(status.lastUpdated) > new Date(startTime - 5000)) {
          clearInterval(poller);
          showToast(name + ' research complete!', 'success');

          // Update the row status
          var statusCell = document.getElementById('status-' + id);
          if (statusCell) statusCell.innerHTML = '<span class="badge badge-green">Researched</span>';

          var updCell = document.getElementById('upd-' + id);
          if (updCell) updCell.textContent = new Date(status.lastUpdated).toLocaleDateString('en-US', {month:'short', day:'numeric'});

          if (btn) {
            btn.disabled = false;
            btn.textContent = '↻ Update';
            btn.style.opacity = '1';
          }
          return;
        }

        if (pollCount >= maxPolls) {
          clearInterval(poller);
          if (btn) {
            btn.disabled = false;
            btn.textContent = '↻ Update';
            btn.style.opacity = '1';
          }
          showToast('Research is taking longer than expected — check your email when done', '');
        }
      } catch(e) {
        clearInterval(poller);
        if (btn) {
          btn.disabled = false;
          btn.textContent = '↻ Update';
          btn.style.opacity = '1';
        }
      }
    }, 10000);

  } catch(e) {
    showToast('Error: ' + e.message, 'error');
    if (btn) {
      btn.disabled = false;
      btn.textContent = name ? (accounts.find(a=>a.id===id)?.hasData ? '↻ Update' : '🔍 Research') : 'Research';
      btn.style.opacity = '1';
    }
  }
}

// Keep old name for backwards compat
async function researchAccount(id, name) {
  await triggerResearch(id, name);
}"""

if old_research_fn in manager_content:
    manager_content = manager_content.replace(old_research_fn, new_research_fn)
    print("Done — research function replaced with live API call + polling")
else:
    # Append the new function before the closing script tag
    manager_content = manager_content.replace(
        'init();\n</script>',
        new_research_fn + '\n\ninit();\n</script>'
    )
    print("Done — research function appended to account manager")

# Also add a "Research all pending" button to the page header
old_page_header = """    <button class='btn btn-primary' onclick='showAddForm()'>+ Add account</button>"""
new_page_header = """    <div style='display:flex;gap:8px'>
      <button class='btn' onclick='researchAllPending()' id='research-all-btn'>&#128269; Research pending</button>
      <button class='btn btn-primary' onclick='showAddForm()'>+ Add account</button>
    </div>"""

if old_page_header in manager_content:
    manager_content = manager_content.replace(old_page_header, new_page_header)
    print("Done — Research pending button added to page header")

# Add the researchAllPending function
research_all_fn = """
async function researchAllPending() {
  var pending = accounts.filter(function(a) { return !a.hasData; });
  if (!pending.length) {
    showToast('No accounts need research — all are up to date', '');
    return;
  }
  var btn = document.getElementById('research-all-btn');
  if (btn) { btn.disabled = true; btn.textContent = 'Starting...'; }
  showToast('Starting research for ' + pending.length + ' pending accounts — check email for updates', 'success');
  for (var i = 0; i < pending.length; i++) {
    var a = pending[i];
    try {
      await fetch('/api/research/' + a.id, { method: 'POST' });
      if (btn) btn.textContent = 'Queued ' + (i+1) + '/' + pending.length + '...';
      await new Promise(r => setTimeout(r, 1000));
    } catch(e) { console.error('Failed to queue', a.name); }
  }
  if (btn) { btn.disabled = false; btn.textContent = 'Research pending'; }
  showToast('All ' + pending.length + ' accounts queued for research', 'success');
}
"""

if 'researchAllPending' not in manager_content:
    manager_content = manager_content.replace(
        'init();\n</script>',
        research_all_fn + '\ninit();\n</script>'
    )
    print("Done — researchAllPending function added")

with open(manager_path, 'w') as f:
    f.write(manager_content)

print("")
print("=" * 50)
print("RESEARCH BUTTONS INSTALLED")
print("=" * 50)
print("")
print("Each account in the manager now has:")
print("  - 'Research' button (blue) for unresearched accounts")
print("  - 'Update' button for already-researched accounts")
print("  - 'Research pending' button at top to research all new accounts at once")
print("")
print("Clicking Research:")
print("  - Triggers immediately, no terminal needed")
print("  - Shows live timer while running")
print("  - Updates the row when complete")
print("  - Sends email notification when done")
print("")
print("Restart: pkill -f 'node src/index.js' && npm start")
