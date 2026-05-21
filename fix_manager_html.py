import os

home = os.path.expanduser("~")
base = os.path.join(home, "legal-tracker")

# Write accountManager.js to just serve a separate HTML file
manager_js_path = os.path.join(base, "src", "accountManager.js")
manager_html_path = os.path.join(base, "src", "manager.html")
routes_path = os.path.join(base, "src", "accountRoutes.js")

# Update accountManager.js to read from file instead
with open(manager_js_path, 'w') as f:
    f.write("""// accountManager.js — serves manager.html
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
const __dirname = dirname(fileURLToPath(import.meta.url));
export function getManagerHTML() {
  return readFileSync(join(__dirname, 'manager.html'), 'utf8');
}
export const ACCOUNT_MANAGER_HTML = getManagerHTML();
""")
print("Done — accountManager.js updated to read from file")

# Update the /manage route in accountRoutes.js to serve manager.html directly
with open(routes_path, 'r') as f:
    routes_content = f.read()

old_manage = """  // GET manage page
  app.get('/manage', async (req, res) => {
    const mod = await import('./accountManager.js');
    res.send(mod.ACCOUNT_MANAGER_HTML);
  });"""

new_manage = """  // GET manage page — serve directly from file
  app.get('/manage', (req, res) => {
    res.sendFile(path.join(__dirname, 'manager.html'));
  });"""

if old_manage in routes_content:
    routes_content = routes_content.replace(old_manage, new_manage)
    with open(routes_path, 'w') as f:
        f.write(routes_content)
    print("Done — /manage route updated to serve file directly")
else:
    # Add import for path and dirname if not there, append route fix
    print("Adding sendFile route...")
    routes_content = routes_content.replace(
        "app.get('/manage'",
        "// Serve manager HTML directly\n  app.get('/manage-old'",
    )
    # Add new route before registerAccountRoutes closes
    routes_content = routes_content.replace(
        "\n}\n",
        "\n  app.get('/manage', (req, res) => { res.sendFile(path.join(__dirname, 'manager.html')); });\n}\n",
        1
    )
    with open(routes_path, 'w') as f:
        f.write(routes_content)

print("Done — accountRoutes.js updated")
print("")
print("Now run:")
print("  python3 write_manager_html.py")
print("  (next file will write the actual manager.html)")
