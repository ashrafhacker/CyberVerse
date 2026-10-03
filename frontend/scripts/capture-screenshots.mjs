// Capture README screenshots from a running local frontend (npm run dev).
// Usage: node scripts/capture-screenshots.mjs
import { chromium } from 'playwright';
import { mkdirSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUT_DIR = resolve(__dirname, '../../docs/images');
const BASE_URL = process.env.CAPTURE_BASE_URL ?? 'http://localhost:3000';

const pages = [
  { path: '/', file: 'landing.png' },
  { path: '/login', file: 'login.png' },
  { path: '/register', file: 'register.png' },
];

mkdirSync(OUT_DIR, { recursive: true });

const browser = await chromium.launch();
const context = await browser.newContext({
  viewport: { width: 1440, height: 900 },
  deviceScaleFactor: 2,
});

for (const { path, file } of pages) {
  const page = await context.newPage();
  await page.goto(`${BASE_URL}${path}`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(3000);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(500);
  await page.screenshot({ path: resolve(OUT_DIR, file), fullPage: true });
  console.log(`captured ${file} (${path})`);
  await page.close();
}

await context.close();
await browser.close();
console.log(`done -> ${OUT_DIR}`);
