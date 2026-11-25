/**
 * Open each imported workflow in a running n8n and save a canvas screenshot.
 *
 * Usage:
 *   N8N_URL=http://127.0.0.1:5688 node scripts/screenshot_canvases.mjs /path/to/id-map.json
 *
 * id-map.json is [{ "n8nId": "...", "path": "workflows/category/id" }, ...]
 */
import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";

const require = createRequire("/tmp/pw/package.json");
const { chromium } = require("playwright");

const baseUrl = process.env.N8N_URL || "http://127.0.0.1:5688";
const email = process.env.N8N_EMAIL || "mustafa@example.com";
const password = process.env.N8N_PASSWORD || "PortfolioDemo123!";
const mapPath = process.argv[2];
const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..");

if (!mapPath) {
  console.error("Pass the id map JSON path");
  process.exit(1);
}

const entries = JSON.parse(fs.readFileSync(mapPath, "utf8"));
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
const failures = [];

await page.goto(baseUrl, { waitUntil: "domcontentloaded", timeout: 60000 });
await page.waitForTimeout(1500);

async function fillIfVisible(selector, value) {
  const field = page.locator(selector).first();
  if (await field.count()) {
    if (await field.isVisible().catch(() => false)) {
      await field.fill(value);
      return true;
    }
  }
  return false;
}

if (page.url().includes("setup") || (await page.getByRole("button", { name: /set up|get started|next/i }).count())) {
  await fillIfVisible('input[name="email"]', email);
  await fillIfVisible('input[type="email"]', email);
  await fillIfVisible('input[name="firstName"]', "Mustafa");
  await fillIfVisible('input[name="lastName"]', "Automation");
  await fillIfVisible('input[type="password"]', password);
  const button = page.getByRole("button", { name: /next|set up|continue|create/i }).first();
  if (await button.count()) await button.click();
  await page.waitForTimeout(1500);
}

if (page.url().includes("signin") || (await page.locator('input[type="password"]').count())) {
  await fillIfVisible('input[type="email"]', email);
  await fillIfVisible('input[name="email"]', email);
  await fillIfVisible('input[type="password"]', password);
  const button = page.getByRole("button", { name: /sign in|log in/i }).first();
  if (await button.count()) await button.click();
  await page.waitForTimeout(2000);
}

for (const [index, entry] of entries.entries()) {
  const target = `${baseUrl}/workflow/${entry.n8nId}`;
  const file = path.join(root, entry.path, "screenshot.png");
  try {
    await page.goto(target, { waitUntil: "domcontentloaded", timeout: 60000 });
    await page.getByText("Run demo", { exact: true }).first().waitFor({ timeout: 20000 });
    const fit = page.getByRole("button", { name: /fit|zoom to fit/i }).first();
    if (await fit.count()) {
      await fit.click().catch(() => {});
    }
    await page.waitForTimeout(600);
    const canvas = page.locator(".vue-flow, [class*='canvas'], [data-test-id='canvas']").first();
    if (await canvas.count()) {
      await canvas.screenshot({ path: file });
    } else {
      await page.screenshot({ path: file });
    }
    console.log(`${index + 1}/${entries.length} ${entry.path}`);
  } catch (error) {
    failures.push({ path: entry.path, message: String(error).slice(0, 300) });
    await page.screenshot({ path: file }).catch(() => {});
    console.log(`${index + 1}/${entries.length} FAILED ${entry.path}`);
  }
}

await browser.close();
fs.writeFileSync(path.join(root, "test-results", "screenshots.json"), JSON.stringify({ failures }, null, 2));
console.log(`screenshots done, failures ${failures.length}`);
if (failures.length) process.exitCode = 1;
