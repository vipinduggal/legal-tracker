// accountManager.js — serves manager.html
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
const __dirname = dirname(fileURLToPath(import.meta.url));
export function getManagerHTML() {
  return readFileSync(join(__dirname, 'manager.html'), 'utf8');
}
export const ACCOUNT_MANAGER_HTML = getManagerHTML();
