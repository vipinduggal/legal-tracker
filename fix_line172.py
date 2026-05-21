import os

home = os.path.expanduser("~")
path = os.path.join(home, "legal-tracker", "src", "server.js")

with open(path, 'r') as f:
    content = f.read()

# Fix the broken regex in the ini function
old = r"function ini(n){return n.split(/[\s\\/\\-]+/).map(function(w){return w[0];}).join('').slice(0,2).toUpperCase();}"
new = "function ini(n){var p=n.split(' ');return p.map(function(w){return w[0]||'';}).join('').slice(0,2).toUpperCase();}"

if old in content:
    content = content.replace(old, new)
    print("Fixed ini function regex")
else:
    # Try finding and replacing any regex with backslash issues around line 172
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if 'ini' in line and 'split' in line and i > 160 and i < 185:
            print("Found ini at line " + str(i+1) + ": " + line[:80])
            lines[i] = "function ini(n){var p=n.split(' ');return p.map(function(w){return w[0]||'';}).join('').slice(0,2).toUpperCase();}"
            print("Fixed")
            break
    content = '\n'.join(lines)

with open(path, 'w') as f:
    f.write(content)

print("Done")
