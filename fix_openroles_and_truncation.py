import os, re

home = os.path.expanduser("~")
base = os.path.join(home, "legal-tracker")

# ── Fix 1: researcher.js — increase max_tokens for large accounts ──
researcher_path = os.path.join(base, "src", "researcher.js")
with open(researcher_path, 'r') as f:
    researcher = f.read()

# Find and increase the main Claude research call tokens
old_tokens = re.search(r'max_tokens:\s*(\d+)', researcher)
if old_tokens:
    current = int(old_tokens.group(1))
    print(f"Current max_tokens in researcher.js: {current}")
    if current < 8192:
        researcher = researcher.replace(
            f"max_tokens: {current}",
            "max_tokens: 8192",
            1  # only first occurrence (the main research call)
        )
        print("Done — max_tokens increased to 8192")
    else:
        print("Already at", current)

with open(researcher_path, 'w') as f:
    f.write(researcher)

# ── Fix 2: Fix open roles parsing in contactVerifier.js ──
verifier_path = os.path.join(base, "src", "contactVerifier.js")
with open(verifier_path, 'r') as f:
    content = f.read()

# The problem: open roles section check looks for "=== OPEN_ROLES ===" 
# but the combined perplexityAnswer uses "=== OPEN_ROLES ===" as separator
# Let's verify and fix the parsing logic

old_roles_parse = '''    const openRolesSection = perplexityAnswer.includes("=== OPEN_ROLES ===")
      ? perplexityAnswer.split("=== OPEN_ROLES ===")[1]?.split("===")[0] || ""
      : "";'''

new_roles_parse = '''    // Extract open roles section from combined Perplexity answer
    const openRolesSectionMatch = perplexityAnswer.match(/=== OPEN_ROLES ===([\\s\\S]*?)(?:===|$)/);
    const openRolesSection = openRolesSectionMatch ? openRolesSectionMatch[1].trim() : "";'''

if old_roles_parse in content:
    content = content.replace(old_roles_parse, new_roles_parse)
    print("Done — open roles section parser fixed")
else:
    print("WARNING — open roles parse pattern not found, checking...")
    idx = content.find("openRolesSection")
    if idx > 0:
        print("Found at:", idx)
        print(content[idx:idx+200])

# Also fix the search label — make sure it uses "open_roles" consistently
# The perplexityAnswer combines sections as "=== LABEL.UPPERCASE() ==="
old_label_check = '      label: "open_roles",'
if old_label_check in content:
    print("open_roles label found correctly")
else:
    print("WARNING — open_roles label not found in searches array")

with open(verifier_path, 'w') as f:
    f.write(content)

# ── Fix 3: Update dashboard to handle missing open_roles gracefully ──
dashboard_path = os.path.join(base, "src", "dashboard.html")
with open(dashboard_path, 'r') as f:
    dash = f.read()

# Check if Open Roles tab was added
if "openroles" in dash:
    print("Done — Open Roles tab already in dashboard")
else:
    print("WARNING — Open Roles tab not in dashboard, re-adding...")
    
    # Add to tabs list
    old_tabs = "var tbs=[{id:'contacts',l:'Contacts',n:(r.contacts||[]).length},"
    new_tabs = "var tbs=[{id:'contacts',l:'Contacts',n:(r.contacts||[]).length},{id:'openroles',l:'Open Roles',n:(r.open_roles||[]).length},"
    
    if old_tabs in dash:
        dash = dash.replace(old_tabs, new_tabs)
        print("Done — Open Roles added to tabs list")

    # Add renderer before triggers tab
    old_trg = "  }else if(tab==='triggers'){"
    new_roles_renderer = """  }else if(tab==='openroles'){
    var roles=r.open_roles||[];
    if(!roles.length){
      c.innerHTML='<div class="ep"><p>No open legal roles found</p><p style="font-size:12px;margin-top:6px;color:var(--g5)">Re-research this account to check current postings</p></div>';
      return;
    }
    var h='<div class="sl">Open legal positions ('+roles.length+')</div>';
    roles.forEach(function(role){
      h+='<div style="background:#fff;border:1px solid var(--g2);border-left:3px solid #5B45C7;border-radius:var(--rl);padding:13px 16px;margin-bottom:8px">';
      h+='<div style="display:flex;align-items:center;gap:8px;margin-bottom:5px">';
      h+='<span style="font-size:13px;font-weight:600;color:var(--g9)">'+(role.title||'Unknown role')+'</span>';
      if(role.posted)h+='<span style="font-size:11px;color:var(--g4)">'+role.posted+'</span>';
      if(role.location)h+='<span style="font-size:11px;background:var(--g1);color:var(--g6);padding:1px 7px;border-radius:10px">'+role.location+'</span>';
      h+='</div>';
      if(role.signal)h+='<div style="font-size:12px;color:var(--teal)">&#8594; '+role.signal+'</div>';
      h+='</div>';
    });
    c.innerHTML=h;
  """ + old_trg

    if old_trg in dash:
        dash = dash.replace(old_trg, new_roles_renderer)
        print("Done — Open Roles renderer added to dashboard")

    with open(dashboard_path, 'w') as f:
        f.write(dash)

print("")
print("Restart: pkill -f 'node src/index.js' && npm start")
print("Then: npm run research:account \"Microsoft\"")
print("Watch for: [info] Live triggers applied for Microsoft: X immediate, Y strategic, Z open roles")
