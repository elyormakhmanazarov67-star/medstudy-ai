/* Offline build: copies existing Mini App exactly, without secrets.
 * Cloudflare static assets are served for free outside Workers invocation.
 */
import { readFileSync, mkdirSync, cpSync, rmSync, writeFileSync } from 'node:fs';
import { dirname, resolve, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..', '..');
const publicDir = join(root, 'cloudflare', 'public');
const generatedDir = join(root, 'cloudflare', 'generated');
const raw = readFileSync(join(root, 'content', 'lessons.json'), 'utf8');
const catalog = JSON.parse(raw);
if (catalog.subjects.length !== 6 ||
    catalog.subjects.reduce((n, s) => n + s.lessons.length, 0) !== 81) {
  throw new Error('Unexpected lesson catalog; refuse preview build.');
}
rmSync(publicDir, { recursive: true, force: true });
mkdirSync(join(publicDir, 'static'), { recursive: true });
mkdirSync(generatedDir, { recursive: true });
cpSync(join(root, 'app', 'static'), join(publicDir, 'static'), { recursive: true });
cpSync(join(root, 'app', 'static', 'index.html'), join(publicDir, 'index.html'));
writeFileSync(join(generatedDir, 'catalog.mjs'),
  '/* Generated from content/lessons.json; do not hand-edit. */\nexport default ' +
  JSON.stringify(catalog) + ';\n');
console.log('Cloudflare preview assets built: 6 subjects, 81 lessons.');
