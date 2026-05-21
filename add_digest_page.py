import os

home = os.path.expanduser("~")
base = os.path.join(home, "legal-tracker")

# Write the digest HTML page as a separate file
digest_html_path = os.path.join(base, "src", "digest.html")

with open(digest_html_path, 'w') as f:
    f.write("""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Weekly Outreach Digest</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&family=DM+Mono&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{--navy:#0F2240;--blue:#1E56A0;--bl:#EBF2FC;--teal:#0A7C6E;--tl:#E6F5F2;--amber:#B45309;--al:#FEF3C7;--red:#991B1B;--rl:#FEE2E2;--green:#166534;--gl:#DCFCE7;--g0:#F9FAFB;--g1:#F3F4F6;--g2:#E5E7EB;--g4:#9CA3AF;--g5:#6B7280;--g6:#4B5563;--g7:#374151;--g9:#111827;--f:"DM Sans",sans-serif;--mono:"DM Mono",monospace;--r:10px;--rl:14px}
body{font-family:var(--f);font-size:14px;color:var(--g9);background:var(--g0);min-height:100vh}
.tb{height:52px;background:var(--navy);display:flex;align-items:center;padding:0 20px;gap:16px;position:sticky;top:0;z-index:10}
.tb a{color:rgba(255,255,255,.7);text-decoration:none;font-size:13px}
.tb a:hover{color:#fff}
.tb-t{font-size:15px;font-weight:600;color:#fff}
.tb-sub{font-size:12px;color:rgba(255,255,255,.45)}
.tb-r{margin-left:auto;display:flex;align-items:center;gap:8px}
.tb-date{font-size:12px;color:rgba(255,255,255,.55)}
.wrap{max-width:820px;margin:0 auto;padding:28px 20px 60px}
.summary-box{background:linear-gradient(135deg,#EBF2FC,#F0F7FF);border:1px solid #BFCFE8;border-radius:var(--rl);padding:18px 20px;margin-bottom:24px}
.summary-label{font-size:11px;font-weight:700;color:var(--blue);text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px}
.summary-text{font-size:14px;color:var(--navy);line-height:1.7;font-weight:400}
.section-title{font-size:12px;font-weight:700;color:var(--g4);text-transform:uppercase;letter-spacing:.06em;margin:28px 0 12px;display:flex;align-items:center;gap:8px}
.section-title::after{content:"";flex:1;height:1px;background:var(--g2)}
.priority-card{background:#fff;border:1px solid var(--g2);border-radius:var(--rl);padding:18px 20px;margin-bottom:12px;transition:box-shadow .12s}
.priority-card:hover{box-shadow:0 4px 12px rgba(0,0,0,.08)}
.priority-header{display:flex;align-items:center;gap:10px;margin-bottom:10px}
.rank{width:26px;height:26px;border-radius:50%;background:var(--navy);color:#fff;font-size:11px;font-weight:700;display:flex;align-items:center;justify-content:center;flex-shrink:0}
.rank.critical{background:var(--red)}
.rank.high{background:var(--amber)}
.acct-name{font-size:15px;font-weight:600;color:var(--g9)}
.urgency{font-size:10px;font-weight:600;padding:2px 8px;border-radius:20px}
.urgency.Critical{background:var(--rl);color:var(--red)}
.urgency.High{background:var(--al);color:var(--amber)}
.urgency.Medium{background:var(--bl);color:var(--blue)}
.trigger-box{background:var(--g0);border-left:3px solid var(--blue);padding:10px 14px;border-radius:0 6px 6px 0;margin-bottom:12px;font-size:13px;color:var(--g7);line-height:1.6}
.contact-chip{display:inline-flex;align-items:center;gap:5px;background:var(--bl);color:var(--blue);font-size:12px;font-weight:500;padding:4px 10px;border-radius:20px;margin-bottom:10px}
.talking-point{font-size:13px;font-style:italic;color:var(--g6);background:var(--g0);border:1px solid var(--g2);border-radius:var(--r);padding:10px 13px;margin-bottom:12px;line-height:1.6}
.email-block{background:#FAFAFA;border:1px solid var(--g2);border-radius:var(--r);overflow:hidden}
.email-header{padding:10px 14px;border-bottom:1px solid var(--g2);display:flex;align-items:center;justify-content:space-between}
.email-label{font-size:11px;font-weight:600;color:var(--g5);text-transform:uppercase;letter-spacing:.05em}
.copy-btn{font-size:11px;padding:3px 10px;border-radius:5px;border:1px solid var(--g2);background:#fff;cursor:pointer;color:var(--g6);font-family:var(--f);transition:all .12s}
.copy-btn:hover{background:var(--bl);border-color:var(--blue);color:var(--blue)}
.copy-btn.copied{background:var(--gl);border-color:var(--green);color:var(--green)}
.email-subject{padding:10px 14px;font-size:13px;font-weight:600;color:var(--g9);border-bottom:1px solid var(--g2)}
.email-body{padding:14px;font-size:13px;color:var(--g7);line-height:1.75;white-space:pre-wrap;font-family:var(--f)}
.linkedin-block{margin-top:10px;background:var(--bl);border-radius:var(--r);padding:12px 14px}
.linkedin-label{font-size:11px;font-weight:600;color:var(--blue);text-transform:uppercase;letter-spacing:.05em;margin-bottom:5px;display:flex;align-items:center;justify-content:space-between}
.linkedin-text{font-size:13px;color:var(--navy);line-height:1.6}
.alert-card{background:#fff;border:1px solid var(--rl);border-left:4px solid var(--red);border-radius:var(--rl);padding:14px 16px;margin-bottom:10px}
.alert-type{font-size:11px;font-weight:700;color:var(--red);text-transform:uppercase;letter-spacing:.06em;margin-bottom:4px}
.alert-acct{font-size:14px;font-weight:600;color:var(--g9);margin-bottom:4px}
.alert-summary{font-size:13px;color:var(--g6);line-height:1.5;margin-bottom:6px}
.alert-action{font-size:13px;color:var(--amber);font-weight:500}
.watch-card{background:#fff;border:1px solid #A7D7D0;border-left:4px solid var(--teal);border-radius:var(--rl);padding:14px 16px;margin-bottom:10px}
.watch-person{font-size:14px;font-weight:600;color:var(--g9);margin-bottom:2px}
.watch-acct{font-size:12px;color:var(--teal);font-weight:500;margin-bottom:4px}
.watch-change{font-size:13px;color:var(--g6);margin-bottom:4px}
.watch-window{font-size:12px;color:var(--amber);font-weight:500}
.quick-list{background:#fff;border:1px solid var(--g2);border-radius:var(--rl);overflow:hidden}
.quick-item{padding:11px 16px;border-bottom:1px solid var(--g1);display:flex;align-items:flex-start;gap:10px;font-size:13px}
.quick-item:last-child{border-bottom:none}
.quick-acct{font-weight:600;color:var(--g9);flex-shrink:0;min-width:160px}
.quick-action{color:var(--g6);line-height:1.5}
.empty{padding:24px;text-align:center;color:var(--g4);font-size:13px;background:#fff;border:1px solid var(--g2);border-radius:var(--rl)}
.gen-btn{display:block;width:100%;padding:12px;border:1.5px dashed var(--g2);border-radius:var(--rl);background:transparent;cursor:pointer;font-size:13px;color:var(--g5);font-family:var(--f);transition:all .15s;margin-top:12px}
.gen-btn:hover{border-color:var(--blue);color:var(--blue);background:var(--bl)}
.spinner{display:inline-block;width:14px;height:14px;border:2px solid var(--g2);border-top-color:var(--blue);border-radius:50%;animation:spin .6s linear infinite;margin-right:6px;vertical-align:middle}
@keyframes spin{to{transform:rotate(360deg)}}
.no-digest{text-align:center;padding:60px 20px;color:var(--g4)}
.no-digest h2{font-size:18px;font-weight:600;color:var(--g7);margin-bottom:8px}
.no-digest p{font-size:13px;margin-bottom:16px;line-height:1.6}
.no-digest code{font-family:var(--mono);background:var(--g1);padding:4px 10px;border-radius:6px;font-size:12px;color:var(--g7)}
</style>
</head>
<body>
<div class="tb">
  <a href="/">&#8592; Dashboard</a>
  <span class="tb-t">Weekly Outreach Digest</span>
  <span class="tb-sub" id="tb-date"></span>
  <div class="tb-r">
    <button class="copy-btn" onclick="generateNew()" id="gen-btn">&#8635; Generate new digest</button>
  </div>
</div>

<div class="wrap" id="content">
  <div style="text-align:center;padding:40px;color:var(--g4)">
    <div class="spinner"></div> Loading digest...
  </div>
</div>

<script>
async function load() {
  try {
    var r = await fetch('/api/digest');
    var d = await r.json();
    if (d.message) {
      renderEmpty();
      return;
    }
    render(d);
  } catch(e) {
    document.getElementById('content').innerHTML = '<div class="empty">Failed to load digest: ' + e.message + '</div>';
  }
}

function render(d) {
  var c = document.getElementById('content');
  var savedAt = d.savedAt ? new Date(d.savedAt).toLocaleDateString('en-US',{weekday:'long',month:'long',day:'numeric',year:'numeric'}) : '';
  document.getElementById('tb-date').textContent = savedAt ? 'Week of ' + savedAt : '';

  var html = '';

  // Week summary
  if (d.week_summary) {
    html += '<div class="summary-box">';
    html += '<div class="summary-label">&#128200; This week\'s themes</div>';
    html += '<div class="summary-text">' + d.week_summary + '</div>';
    html += '</div>';
  }

  // Priority accounts
  var priorities = d.priority_accounts || [];
  if (priorities.length) {
    html += '<div class="section-title">&#11088; Priority outreach &mdash; top ' + priorities.length + ' accounts</div>';
    priorities.forEach(function(p) {
      var urgClass = (p.urgency || '').toLowerCase();
      html += '<div class="priority-card">';

      // Header
      html += '<div class="priority-header">';
      html += '<div class="rank ' + urgClass + '">' + p.priority_rank + '</div>';
      html += '<div class="acct-name">' + p.account_name + '</div>';
      if (p.urgency) html += '<span class="urgency ' + p.urgency + '">' + p.urgency + '</span>';
      html += '</div>';

      // Trigger
      if (p.trigger) {
        html += '<div class="trigger-box">' + p.trigger + '</div>';
      }

      // Contact chip
      if (p.contact) {
        html += '<div><span class="contact-chip">&#8594; ' + p.contact.name + ' &middot; ' + p.contact.title + '</span>';
        if (p.contact.why_them) html += '<span style="font-size:12px;color:var(--g5);margin-left:8px">' + p.contact.why_them + '</span>';
        html += '</div>';
      }

      // Talking point
      if (p.talking_point) {
        html += '<div class="talking-point">&ldquo;' + p.talking_point + '&rdquo;</div>';
      }

      // Email
      if (p.email) {
        var emailId = 'email-' + p.priority_rank;
        html += '<div class="email-block">';
        html += '<div class="email-header"><span class="email-label">&#9993; Suggested email</span>';
        html += '<button class="copy-btn" onclick="copyEmail(\'' + emailId + '\')" id="copy-' + emailId + '">Copy email</button></div>';
        html += '<div class="email-subject">Subject: ' + p.email.subject + '</div>';
        html += '<div class="email-body" id="' + emailId + '">' + escHtml(p.email.body) + '</div>';
        html += '</div>';
      }

      // LinkedIn message
      if (p.linkedin_message) {
        html += '<div class="linkedin-block">';
        html += '<div class="linkedin-label"><span>&#128100; LinkedIn InMail</span>';
        html += '<button class="copy-btn" onclick="copyText(\'' + escAttr(p.linkedin_message) + '\')" style="background:transparent;border-color:rgba(30,86,160,.3)">Copy</button></div>';
        html += '<div class="linkedin-text">' + escHtml(p.linkedin_message) + '</div>';
        html += '</div>';
      }

      html += '</div>';
    });
  }

  // New filings alerts
  var filings = d.new_filings_alert || [];
  if (filings.length) {
    html += '<div class="section-title">&#128680; New filings alert</div>';
    filings.forEach(function(f) {
      html += '<div class="alert-card">';
      html += '<div class="alert-type">' + f.filing_type + '</div>';
      html += '<div class="alert-acct">' + f.account_name + '</div>';
      html += '<div class="alert-summary">' + f.summary + '</div>';
      if (f.suggested_action) html += '<div class="alert-action">&#128161; ' + f.suggested_action + '</div>';
      html += '</div>';
    });
  }

  // Personnel watch
  var personnel = d.personnel_watch || [];
  if (personnel.length) {
    html += '<div class="section-title">&#128100; Personnel watch</div>';
    personnel.forEach(function(p) {
      html += '<div class="watch-card">';
      html += '<div class="watch-person">' + p.person + '</div>';
      html += '<div class="watch-acct">' + p.account_name + '</div>';
      html += '<div class="watch-change">' + p.change + '</div>';
      if (p.window) html += '<div class="watch-window">&#9200; Window: ' + p.window + '</div>';
      html += '</div>';
    });
  }

  // Quick touches
  var quick = d.quick_touches || [];
  if (quick.length) {
    html += '<div class="section-title">&#9889; Quick touches</div>';
    html += '<div class="quick-list">';
    quick.forEach(function(q) {
      html += '<div class="quick-item">';
      html += '<span class="quick-acct">' + q.account_name + '</span>';
      html += '<span class="quick-action">' + q.action + '</span>';
      html += '</div>';
    });
    html += '</div>';
  }

  html += '<button class="gen-btn" onclick="generateNew()">&#8635; Generate new digest based on latest research</button>';

  c.innerHTML = html;
}

function renderEmpty() {
  document.getElementById('content').innerHTML = '<div class="no-digest">'
    + '<h2>No digest generated yet</h2>'
    + '<p>Your first weekly digest will arrive Monday at 8 AM automatically.<br>Or generate one now:</p>'
    + '<code>npm run digest:weekly</code>'
    + '<br><br><button class="copy-btn" style="padding:8px 16px;font-size:13px" onclick="generateNew()">&#8635; Generate now</button>'
    + '</div>';
}

async function generateNew() {
  var btn = document.getElementById('gen-btn');
  if (btn) { btn.innerHTML = '<span class="spinner"></span>Generating...'; btn.disabled = true; }
  try {
    var r = await fetch('/api/digest/generate', { method: 'POST' });
    var d = await r.json();
    if (d.queued) {
      alert('Digest generation started. This takes 1-2 minutes. The page will refresh automatically.');
      setTimeout(function() { window.location.reload(); }, 90000);
    }
  } catch(e) {
    alert('To generate a new digest, run in terminal:\nnpm run digest:weekly');
  }
  if (btn) { btn.innerHTML = '&#8635; Generate new digest'; btn.disabled = false; }
}

function copyEmail(id) {
  var el = document.getElementById(id);
  if (!el) return;
  var subjectEl = el.previousElementSibling;
  var subject = subjectEl ? subjectEl.textContent.replace('Subject: ', '') : '';
  var text = (subject ? 'Subject: ' + subject + '\\n\\n' : '') + el.textContent;
  navigator.clipboard.writeText(text).then(function() {
    var btn = document.getElementById('copy-' + id);
    if (btn) { btn.textContent = 'Copied!'; btn.classList.add('copied'); setTimeout(function(){ btn.textContent = 'Copy email'; btn.classList.remove('copied'); }, 2000); }
  });
}

function copyText(text) {
  navigator.clipboard.writeText(text).then(function() {
    alert('Copied to clipboard');
  });
}

function escHtml(str) {
  return String(str)
    .replace(/&/g,'&amp;')
    .replace(/</g,'&lt;')
    .replace(/>/g,'&gt;')
    .replace(/\\n/g,'<br>');
}

function escAttr(str) {
  return String(str).replace(/'/g,'&#39;').replace(/"/g,'&quot;');
}

load();
</script>
</body>
</html>""")

print("Done — digest.html written")

# Add /digest route to accountRoutes.js
routes_path = os.path.join(base, "src", "accountRoutes.js")
with open(routes_path, 'r') as f:
    routes_content = f.read()

digest_routes = """
  // GET readable digest page
  app.get('/digest', (req, res) => {
    res.sendFile(path.join(__dirname, 'digest.html'));
  });

  // POST generate new digest (queues it)
  app.post('/api/digest/generate', async (req, res) => {
    res.json({ queued: true, message: 'Digest generation started' });
    setImmediate(async () => {
      try {
        const { runWeeklyDigest } = await import('../jobs/weeklyDigest.js');
        await runWeeklyDigest();
      } catch(e) {
        console.error('Digest generation failed:', e.message);
      }
    });
  });

"""

if "app.get('/digest'" not in routes_content:
    routes_content = routes_content.replace(
        "  app.get('/manage'",
        digest_routes + "  app.get('/manage'"
    )
    with open(routes_path, 'w') as f:
        f.write(routes_content)
    print("Done — /digest route added to accountRoutes.js")
else:
    print("Skipped — /digest route already exists")

# Update dashboard topbar to link to /digest instead of /api/digest
dashboard_path = os.path.join(base, "src", "dashboard.html")
with open(dashboard_path, 'r') as f:
    dash = f.read()

old_link = '<a href="/api/digest" target="_blank" class="nd">Digest</a>'
new_link = '<a href="/digest" class="nd">Digest</a>'

if old_link in dash:
    dash = dash.replace(old_link, new_link)
    with open(dashboard_path, 'w') as f:
        f.write(dash)
    print("Done — dashboard Digest link updated to /digest")
else:
    print("Skipped dashboard link — pattern not found")

print("")
print("Restart: pkill -f 'node src/index.js' && npm start")
print("")
print("Available URLs:")
print("  http://localhost:3000/digest  — Beautiful weekly digest page")
print("  http://localhost:3000/manage  — Account manager")
print("  http://localhost:3000         — Main dashboard")
