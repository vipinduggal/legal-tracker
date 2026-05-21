import os

home = os.path.expanduser("~")
path = os.path.join(home, "legal-tracker", "src", "prompts.js")

with open(path, 'r') as f:
    content = f.read()

print("File size:", len(content), "bytes")
print("")

# Check what functions exist
if "buildWeeklyDigestPrompt" in content:
    idx = content.index("buildWeeklyDigestPrompt")
    print("buildWeeklyDigestPrompt found at index:", idx)
    print("")
    print("First 200 chars of function:")
    print(content[idx:idx+200])
    print("")
    print("Last 200 chars of function:")
    print(content[-400:])
else:
    print("buildWeeklyDigestPrompt NOT FOUND in prompts.js")
    print("")
    print("Functions found:")
    import re
    fns = re.findall(r'export function \w+', content)
    for f in fns:
        print(" ", f)
