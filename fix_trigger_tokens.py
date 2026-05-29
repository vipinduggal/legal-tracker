import os, re

home = os.path.expanduser("~")
base = os.path.join(home, "legal-tracker")
verifier_path = os.path.join(base, "src", "contactVerifier.js")

with open(verifier_path, 'r') as f:
    content = f.read()

# Fix 1: Increase max_tokens in the main structuring call from 2000 to 4000
fixed = 0
# Find the Claude structuring call and increase tokens
old1 = '''    const response = await client.messages.create({
      model: "claude-sonnet-4-5",
      max_tokens: 2000,
      messages: [{ role: "user", content: structurePrompt }],
    });'''
new1 = '''    const response = await client.messages.create({
      model: "claude-sonnet-4-5",
      max_tokens: 4000,
      messages: [{ role: "user", content: structurePrompt }],
    });'''
if old1 in content:
    content = content.replace(old1, new1)
    print("Done — main structuring call increased to 4000 tokens")
    fixed += 1

# Fix 2: Increase max_tokens in the force extraction call from 1000 to 2000
old2 = '''        const resp2 = await client2.messages.create({
          model: "claude-sonnet-4-5",
          max_tokens: 1000,
          messages: [{ role: "user", content: forcePrompt }],
        });'''
new2 = '''        const resp2 = await client2.messages.create({
          model: "claude-sonnet-4-5",
          max_tokens: 2000,
          messages: [{ role: "user", content: forcePrompt }],
        });'''
if old2 in content:
    content = content.replace(old2, new2)
    print("Done — force extraction call increased to 2000 tokens")
    fixed += 1

# Fix 3: Also check debugTriggers.js which used 1000 tokens
debug_path = os.path.join(base, "scripts", "debugTriggers.js")
if os.path.exists(debug_path):
    with open(debug_path, 'r') as f:
        debug = f.read()
    debug = debug.replace("max_tokens: 1000,", "max_tokens: 2500,")
    with open(debug_path, 'w') as f:
        f.write(debug)
    print("Done — debugTriggers.js updated to 2500 tokens")

# If patterns not found exactly, do a broader search
if fixed == 0:
    print("Exact patterns not found — doing broad replacement...")
    # Find all max_tokens lines in the file and increase small ones
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if 'max_tokens:' in line and ('1000' in line or '2000' in line):
            old_line = line
            new_line = line.replace('1000,', '2500,').replace('2000,', '4000,')
            lines[i] = new_line
            print(f"Line {i+1}: {old_line.strip()} -> {new_line.strip()}")
    content = '\n'.join(lines)

with open(verifier_path, 'w') as f:
    f.write(content)

print("")
print("The issue was clear: Claude was generating perfect triggers but")
print("JSON was cut off at position 4294 because max_tokens was too small.")
print("")
print("Now run: node scripts/fixAMD.js")
print("Should see 4 immediate + 4 strategic triggers saved successfully")
