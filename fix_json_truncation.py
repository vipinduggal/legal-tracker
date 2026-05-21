import os, re

home = os.path.expanduser("~")
base = os.path.join(home, "legal-tracker")
researcher_path = os.path.join(base, "src", "researcher.js")

with open(researcher_path, 'r') as f:
    content = f.read()

# Fix 1: Increase max_tokens from 4096 to 8192
old_tokens = "max_tokens: 4096"
new_tokens = "max_tokens: 8192"
if old_tokens in content:
    content = content.replace(old_tokens, new_tokens)
    print("Done — max_tokens increased to 8192")
else:
    # Try other common values
    for old in ["max_tokens: 2000", "max_tokens: 3000", "max_tokens: 4000", "max_tokens: 5000"]:
        if old in content:
            content = content.replace(old, new_tokens)
            print("Done — " + old + " increased to 8192")
            break
    else:
        # Find any max_tokens line
        match = re.search(r'max_tokens:\s*\d+', content)
        if match:
            content = content.replace(match.group(), "max_tokens: 8192")
            print("Done — found and updated: " + match.group())
        else:
            print("WARNING — max_tokens not found, searching for messages create call...")
            # Add max_tokens if not found
            content = content.replace(
                "model: \"claude-sonnet-4-5\",",
                "model: \"claude-sonnet-4-5\",\n      max_tokens: 8192,"
            )
            print("Done — added max_tokens: 8192")

# Fix 2: Improve JSON recovery to handle truncated responses better
old_recovery = """    // Attempt to fix truncated JSON by finding the last complete object
    let parsed;
    try {
      parsed = JSON.parse(cleaned);
    } catch (e) {
      // Try to salvage truncated response by finding last valid closing brace
      const lastBrace = cleaned.lastIndexOf('}');
      if (lastBrace > 0) {
        try {
          parsed = JSON.parse(cleaned.slice(0, lastBrace + 1));
          logger.warn(`Truncated JSON recovered for ${account.name}`);
        } catch (e2) {
          throw new Error('JSON parse failed even after truncation recovery: ' + e.message);
        }
      } else {
        throw e;
      }
    }"""

new_recovery = """    // Robust JSON parsing with multiple recovery strategies
    let parsed;
    try {
      parsed = JSON.parse(cleaned);
    } catch (e) {
      logger.warn(`JSON parse failed for ${account.name}, attempting recovery...`);

      // Strategy 1: Find the last complete top-level closing brace
      let recovered = false;
      const lastBrace = cleaned.lastIndexOf('}');
      if (lastBrace > 0) {
        try {
          parsed = JSON.parse(cleaned.slice(0, lastBrace + 1));
          logger.warn(`Strategy 1 recovery succeeded for ${account.name}`);
          recovered = true;
        } catch (e2) {}
      }

      // Strategy 2: Truncate at last complete array item
      if (!recovered) {
        try {
          // Find last complete contact/litigation/regulatory entry
          const truncated = cleaned
            .replace(/,\\s*\\{[^}]*$/, '') // remove last incomplete object
            .replace(/,\\s*"[^"]*":\\s*$/, '') // remove trailing incomplete key
            .replace(/,\\s*$/, ''); // remove trailing comma

          // Close any open arrays and objects
          let depth = 0;
          let inStr = false;
          for (const ch of truncated) {
            if (ch === '"' && !inStr) inStr = true;
            else if (ch === '"' && inStr) inStr = false;
            else if (!inStr && (ch === '{' || ch === '[')) depth++;
            else if (!inStr && (ch === '}' || ch === ']')) depth--;
          }

          let fixed = truncated;
          // Close open structures
          for (let i = 0; i < Math.abs(depth); i++) {
            fixed += depth > 0 ? '}' : ']';
          }

          parsed = JSON.parse(fixed);
          logger.warn(`Strategy 2 recovery succeeded for ${account.name}`);
          recovered = true;
        } catch (e3) {}
      }

      // Strategy 3: Extract what we can with a minimal valid structure
      if (!recovered) {
        logger.warn(`All recovery strategies failed for ${account.name}, using minimal structure`);
        parsed = {
          contacts: [],
          tech: [],
          counsel: [],
          alsp: [],
          flex: [],
          litigation: [],
          regulatory: [],
          financial_intel: {},
          personnel_changes: [],
          sales_triggers: [],
          intel_summary: "Research data truncated — re-run research for this account",
        };
        // Try to extract contacts at minimum
        const contactMatch = cleaned.match(/"contacts":\\s*(\\[.*?\\])/s);
        if (contactMatch) {
          try { parsed.contacts = JSON.parse(contactMatch[1]); } catch(e4) {}
        }
      }
    }"""

if old_recovery in content:
    content = content.replace(old_recovery, new_recovery)
    print("Done — JSON recovery improved with 3 strategies")
else:
    print("WARNING — old recovery pattern not found, checking for simpler version...")
    # Try to find any JSON parse block
    if "JSON parse failed even after truncation" in content:
        print("Found different version — patching inline")
        content = content.replace(
            "throw new Error('JSON parse failed even after truncation recovery: ' + e.message);",
            """logger.warn('Full recovery failed for ' + account.name + ', using minimal structure');
          parsed = { contacts: [], tech: [], counsel: [], alsp: [], flex: [], litigation: [], regulatory: [], financial_intel: {}, personnel_changes: [], sales_triggers: [], intel_summary: 'Research truncated — re-run for full data' };"""
        )
        print("Done — fallback patched")

with open(researcher_path, 'w') as f:
    f.write(content)

print("")
print("Now test:")
print('  npm run research:account "Microsoft"')
print("  Should complete without truncation errors")
