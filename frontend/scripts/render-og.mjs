// Render public/og-banner.svg -> public/og-image.png (1200x630 social card).
// Usage: node scripts/render-og.mjs
import { chromium } from 'playwright';
import { readFileSync, writeFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const PUBLIC_DIR = resolve(__dirname, '../public');
const svg = readFileSync(resolve(PUBLIC_DIR, 'og-banner.svg'), 'utf8');
const html = `<!doctype html><html><body style="margin:0">${svg}</body></html>`;
const tmp = resolve(PUBLIC_DIR, '_og-render.html');
writeFileSync(tmp, html);

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1200, height: 630 } });
await page.goto(`file://${tmp}`);
await page.waitForTimeout(500);
await page.screenshot({ path: resolve(PUBLIC_DIR, 'og-image.png') });
await browser.close();

import { rmSync } from 'node:fs';
rmSync(tmp, { force: true });
console.log('rendered public/og-image.png (1200x630)');
