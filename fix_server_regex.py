import os, re

home = os.path.expanduser("~")
path = os.path.join(home, "legal-tracker", "src", "server.js")

with open(path, 'r') as f:
    content = f.read()

# Fix the broken regex in the delete endpoint
# The issue is fileContent.replace(/ which is an unterminated regex
# Replace the entire delete endpoint with a clean version

old_delete = """app.delete('/api/config/accounts/:id', async (req, res) => {
  try {
    const { id } = req.params;
    const fs = await import('fs');
    const path = await import('path');
    const { fileURLToPath } = await import('url');
    const __dirname = path.default.dirname(fileURLToPath(import.meta.url));
    const accountsPath = path.default.join(__dirname, '..', 'config', 'accounts.js');
    let fileContent = fs.default.readFileSync(accountsPath, 'utf8');

    // Remove the line containing this id
    const lines = fileContent.split('\\\\n');
    const filtered = lines.filter(line => !line.includes('"' + id + '"'));
    if (filtered.length === lines.length) {
      return res.status(404).json({ error: 'Account not found: ' + id });
    }
    fs.default.writeFileSync(accountsPath, filtered.join('\\\\n'));

    // Also remove from database
    await db.read();
    if (db.data.research) delete db.data.research[id];
    if (db.data.lastUpdated) delete db.data.lastUpdated[id];
    await db.write();

    res.json({ success: true, removed: id });
  } catch(e) {
    res.status(500).json({ error: e.message });
  }
});"""

new_delete = """app.delete('/api/config/accounts/:id', async (req, res) => {
  try {
    const { id } = req.params;
    const fs = await import('fs');
    const pathMod = await import('path');
    const { fileURLToPath } = await import('url');
    const __dirname = pathMod.default.dirname(fileURLToPath(import.meta.url));
    const accountsPath = pathMod.default.join(__dirname, '..', 'config', 'accounts.js');
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
});"""

# Also fix the add endpoint which may have similar issues
old_add_replace = """fileContent = fileContent.replace(/\\\\n\\];/, '\\\\n' + newEntry + '\\\\n];');"""
new_add_replace = """const closeTag = '\\n];';
    const insertPos = fileContent.lastIndexOf(closeTag);
    if (insertPos === -1) {
      return res.status(500).json({ error: 'Could not find insertion point in accounts.js' });
    }
    fileContent = fileContent.slice(0, insertPos) + '\\n' + newEntry + closeTag;"""

if old_delete in content:
    content = content.replace(old_delete, new_delete)
    print("Fixed delete endpoint")
else:
    # Try to find and fix any unterminated regex
    lines = content.split('\n')
    fixed_lines = []
    for i, line in enumerate(lines):
        # Fix lines with broken regex patterns
        if 'fileContent.replace(/' in line and not line.strip().startswith('//'):
            # Replace the broken regex replace with string-based approach
            fixed_lines.append('    const closeTag = "\\n];";')
            fixed_lines.append('    const insertPos = fileContent.lastIndexOf(closeTag);')
            fixed_lines.append('    if (insertPos === -1) return res.status(500).json({ error: "Could not find insertion point" });')
            fixed_lines.append('    fileContent = fileContent.slice(0, insertPos) + "\\n" + newEntry + closeTag;')
            print("Fixed broken regex on line " + str(i+1) + ": " + line.strip())
        else:
            fixed_lines.append(line)
    content = '\n'.join(fixed_lines)

# Fix double-escaped newlines in split/join
content = content.replace("split('\\\\n')", "split('\\n')")
content = content.replace("join('\\\\n')", "join('\\n')")

with open(path, 'w') as f:
    f.write(content)

print("Done — server.js fixed")
print("File size: " + str(os.path.getsize(path)) + " bytes")
