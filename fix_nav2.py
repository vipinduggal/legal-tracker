import os, re

home = os.path.expanduser("~")
base = os.path.join(home, "legal-tracker")
server_path = os.path.join(base, "src", "server.js")

with open(server_path, 'r') as f:
    content = f.read()

# Find the right place — look for the Live dot in the topbar
# and inject nav links after it
nav_links = """
    <a href='/manage' style='font-size:12px;color:rgba(255,255,255,.85);text-decoration:none;padding:5px 12px;border:1px solid rgba(255,255,255,.3);border-radius:6px;margin-left:4px;font-weight:500'>&#9881; Manage</a>
    <a href='/api/status' target='_blank' style='font-size:12px;color:rgba(255,255,255,.55);text-decoration:none;padding:5px 10px;border:1px solid rgba(255,255,255,.15);border-radius:6px'>Status</a>"""

# Strategy: find the closing </div> of the topbar-right div
# Insert nav links before it
# Look for the live dot div followed by closing divs

# Find the pattern: live dot + closing divs
patterns_to_try = [
    ("Live</div>\\n  </div>", "Live</div>" + nav_links + "\\n  </div>"),
    ("Live</div>\\n</div>", "Live</div>" + nav_links + "\\n</div>"),
    ("<div class=\\'live-dot\\'></div>&nbsp;Live</div>", "<div class=\\'live-dot\\'></div>&nbsp;Live</div>" + nav_links),
    (".live-dot.></div>.nbsp.Live</div>", None),  # skip
]

found = False
for old, new in patterns_to_try:
    if new is None:
        continue
    if old in content:
        content = content.replace(old, new, 1)
        found = True
        print("Fixed using pattern: " + old[:40])
        break

if not found:
    # Find the topbar right div and append before its closing
    # Look for stat-iss which is always in the topbar
    idx = content.find('stat-iss')
    if idx > 0:
        # Find the next </div></div> after stat-iss
        close_idx = content.find('</div>', idx)
        if close_idx > 0:
            next_close = content.find('</div>', close_idx + 6)
            if next_close > 0:
                insert_pos = next_close + 6
                content = content[:insert_pos] + nav_links + content[insert_pos:]
                found = True
                print("Fixed using stat-iss anchor insertion")

if not found:
    print("WARNING: Could not find topbar insertion point")
    print("Showing relevant section of server.js for debugging:")
    idx = content.find('stat-iss')
    if idx > 0:
        print(repr(content[idx-50:idx+200]))
else:
    with open(server_path, 'w') as f:
        f.write(content)
    print("Nav links written to server.js")

# Also fix the research:account command to handle simple names
# by updating researchOne.js to be more flexible
research_one_path = os.path.join(base, "src", "jobs", "researchOne.js")
with open(research_one_path, 'r') as f:
    r1 = f.read()

old_find = """const account = ACCOUNTS.find(a =>
  a.id.includes(query) ||
  a.name.toLowerCase().includes(query)
);"""

new_find = """const account = ACCOUNTS.find(a =>
  a.id === query ||
  a.id.includes(query) ||
  a.name.toLowerCase() === query ||
  a.name.toLowerCase().includes(query) ||
  a.name.toLowerCase().replace(/[^a-z0-9]/g, '').includes(query.replace(/[^a-z0-9]/g, ''))
);"""

if old_find in r1:
    r1 = r1.replace(old_find, new_find)
    with open(research_one_path, 'w') as f:
        f.write(r1)
    print("Done — researchOne.js updated with flexible name matching")
else:
    print("Skipped researchOne.js — pattern not found")

print("")
print("Restart and test:")
print("  pkill -f 'node src/index.js' && npm start")
print("  Then check http://localhost:3000 for nav buttons")
print("")
print("For Apple, check how it was saved:")
print("  grep -i apple ~/legal-tracker/config/accounts.js")
