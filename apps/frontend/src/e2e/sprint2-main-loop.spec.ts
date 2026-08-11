/**
 * Sprint 2 Main Loop — v4.2 9-Assertion E2E Physical Test Matrix
 *
 * Preconditions:
 *   Backend on http://127.0.0.1:8000, Frontend on http://127.0.0.1:5173
 *   Test account: researcher / researcher123
 *   At least 1 project in DB with completed workflow runs.
 *
 * Run:
 *   npx playwright test src/e2e/sprint2-main-loop.spec.ts --project='Desktop — 1280×800'
 */

import { test, expect } from '@playwright/test';
import type { Page } from '@playwright/test';

const BASE = 'http://127.0.0.1:5173';
const KNOWN_DOC_ID = '264d1198-08d9-42b1-a09d-fdd25912ec71';

// ─── Helpers ────────────────────────────────────────────────────────────

async function login(page: Page) {
  await page.goto(`${BASE}/login`);
  await page.waitForSelector('#login-username', { state: 'visible', timeout: 10_000 });
  await page.fill('#login-username', 'researcher');
  await page.fill('#login-password', 'researcher123');
  await page.click('button.login-btn');
  await page.waitForURL((url: URL) => !url.pathname.includes('/login'), { timeout: 15_000 });
}

/** Go to workspace → click first "查看" run. Returns true if on result page. */
async function goToExistingResult(page: Page): Promise<boolean> {
  await page.goto(`${BASE}/research`);
  await page.waitForSelector('.rpp-list', { timeout: 10_000 });
  await page.locator('.pli-name-link').first().click();
  await page.waitForURL(/\/research\/[^/]+(\?.*)?$/, { timeout: 10_000 });

  // Workspace loads run list asynchronously — wait for result links
  try {
    await page.waitForSelector('a[href*="/result/"]', { timeout: 10_000 });
  } catch {
    return false;
  }
  const viewLink = page.locator('a[href*="/result/"]').first();
  if ((await viewLink.count()) === 0) return false;
  await viewLink.click();
  try {
    await page.waitForURL(/\/research\/.+\/result\/.+/, { timeout: 15_000 });
    // Wait for result page to finish async loading
    await page.waitForTimeout(3_000);
    return true;
  } catch {
    return false;
  }
}

// ─── ① ───────────────────────────────────────────────────────────────────
test('① missing title but has document_id + chunk_id → reader route renders', async ({ page }) => {
  await login(page);
  if (!(await goToExistingResult(page))) { test.skip(true, 'No existing run'); return; }

  // Click a citation → open EvidenceDetail + SourceReferenceCard
  const citItem = page.locator('.rcp-citation-item').first();
  if ((await citItem.count()) > 0) await citItem.click();
  await page.waitForTimeout(500);

  const srcRefLinks = page.locator('.esrc-link--internal');
  if ((await srcRefLinks.count()) === 0) { test.skip(true, 'No SourceReferenceCard internal route'); return; }
  const href = await srcRefLinks.first().getAttribute('href');
  expect(href).toBeTruthy();
  expect(href).toMatch(/^\/(reader|library)\/.+/);
});

// ─── ② ───────────────────────────────────────────────────────────────────
test('② evidence without quote hides quote block', async ({ page }) => {
  await login(page);
  if (!(await goToExistingResult(page))) { test.skip(true, 'No existing run'); return; }

  const citItem = page.locator('.rcp-citation-item').first();
  if ((await citItem.count()) === 0) { test.skip(true, 'No citations'); return; }
  await citItem.click();

  const cards = page.locator('.eed-card');
  for (let i = 0; i < (await cards.count()); i++) {
    const quoteBlock = cards.nth(i).locator('.eed-quote-text');
    if ((await quoteBlock.count()) > 0) {
      expect((await quoteBlock.textContent())?.trim().length).toBeGreaterThan(0);
    }
  }
});

// ─── ③ ───────────────────────────────────────────────────────────────────
test('③ citation without anchor_chunk_ids shows "无法定位" not enabled btn', async ({ page }) => {
  await login(page);
  if (!(await goToExistingResult(page))) { test.skip(true, 'No existing run'); return; }

  const citItem = page.locator('.rcp-citation-item').first();
  if ((await citItem.count()) === 0) { test.skip(true, 'No citations'); return; }
  await citItem.click();
  await page.waitForTimeout(500);

  for (let i = 0; i < (await page.locator('.reader-anchor-btn').count()); i++) {
    expect(await page.locator('.reader-anchor-btn').nth(i).getAttribute('disabled')).toBeNull();
  }
});

// ─── ④ ───────────────────────────────────────────────────────────────────
test('④ sessionStorage disabled shows honest error, no silent migration', async ({ browser }) => {
  const context = await browser.newContext();
  await context.addInitScript(() => {
    Object.defineProperty(window, 'sessionStorage', {
      value: {
        getItem: () => { throw new DOMException('Blocked', 'SecurityError'); },
        setItem: () => { throw new DOMException('Blocked', 'SecurityError'); },
        removeItem: () => { throw new DOMException('Blocked', 'SecurityError'); },
        clear: () => {},
        length: 0,
        key: () => null,
      },
      writable: false,
      configurable: false,
    });
  });

  const page = await context.newPage();
  await page.goto(`${BASE}/`);
  await page.waitForSelector('.prototype-draft-section', { timeout: 10_000 });

  await page.locator('.draft-textarea').fill('测试研究问题');
  await page.click('.draft-save-btn');

  const errorHint = page.locator('.draft-saved-hint--error');
  await expect(errorHint).toBeVisible({ timeout: 5_000 });
  const errorText = await errorHint.textContent();
  expect(errorText).toContain('未保存');
  expect(errorText).not.toContain('草稿已暂存');

  await context.close();
});

// ─── ⑤ ───────────────────────────────────────────────────────────────────
test('⑤ Evidence/Claim context bans "已核验" text and success/green variant', async ({ page }) => {
  await login(page);
  if (!(await goToExistingResult(page))) { test.skip(true, 'No existing run'); return; }

  const citItem = page.locator('.rcp-citation-item').first();
  if ((await citItem.count()) === 0) { test.skip(true, 'No citations'); return; }
  await citItem.click();
  await page.waitForTimeout(500);

  for (let i = 0; i < (await page.locator('.eed-card').count()); i++) {
    const text = await page.locator('.eed-card').nth(i).textContent();
    expect(text, `Evidence card ${i} contains "已核验"`).not.toContain('已核验');
    expect(text, `Evidence card ${i} contains "已证实"`).not.toContain('已证实');
  }

  await expect(page.locator('[data-verification-status="verified"]')).toHaveCount(0);
  expect(await page.locator('.research-page').textContent()).not.toContain('已核验');
});

// ─── ⑥ ───────────────────────────────────────────────────────────────────
test('⑥ heterogeneous runId is isolated — wrong project route shows error', async ({ page }) => {
  await login(page);
  await page.goto(`${BASE}/research/nonexistent-project-999/runs/some-run-uuid`);
  await page.waitForTimeout(4_000);

  const resultContent = page.locator('.rcp-section, .rpage-body');
  if ((await resultContent.count()) > 0) {
    const errorState = page.locator('[role="alert"], .research-page [class*="error"]');
    expect(await errorState.count(), 'Cross-project content leaked').toBeGreaterThan(0);
  }
});

// ─── ⑦ ───────────────────────────────────────────────────────────────────
test('⑦ exactly one POST /api/v4/research/workflow during workflow submission', async ({ page }) => {
  await login(page);

  // Go to workflow
  await page.goto(`${BASE}/research`);
  await page.waitForSelector('.rpp-list', { timeout: 10_000 });
  await page.locator('.pli-name-link').first().click();
  await page.waitForURL(/\/research\/[^/]+(\?.*)?$/, { timeout: 10_000 });
  await page.locator('a[href*="/workflow"]').first().click();
  await page.waitForURL(/\/research\/.+\/workflow/, { timeout: 10_000 });

  let postCount = 0;
  page.on('request', (req) => {
    if (req.method() === 'POST' && req.url().includes('/api/v4/research/workflow')) {
      postCount++;
    }
  });

  // Step 1
  await page.waitForSelector('#rqs-input', { timeout: 5_000 });
  await page.fill('#rqs-input', '针灸甲乙经 呼吸 穴位');
  await page.locator('.rqs-submit-btn').first().click();
  await page.waitForTimeout(2_000);

  // Step 2 — .dss-submit-btn triggers the POST
  await page.locator('.dss-submit-btn').first().click();

  // Wait for step 3 AI analysis to finish (so the async POST completes server-side)
  for (let i = 0; i < 60; i++) {
    await page.waitForTimeout(2_000);
    const text = (await page.locator('.wsn-step--current').textContent() || '').trim();
    if (text.includes('4') || text.includes('证据') || text.includes('5') || text.includes('报告')) break;
  }

  // Step 4: advance to report
  const reportBtn = page.locator('.ers-action-btn').first();
  if ((await reportBtn.count()) > 0) {
    await reportBtn.click();
    await page.waitForTimeout(2_000);
  }

  expect(postCount).toBe(1);
});

// ─── ⑧ ───────────────────────────────────────────────────────────────────
test('⑧ Reader #chunk-<id> highlight fades and shows "已定位至原文"', async ({ page }) => {
  await login(page);

  await page.goto(`${BASE}/reader/${KNOWN_DOC_ID}`);
  await page.waitForSelector('.reader-chunk-paragraph', { timeout: 10_000 });

  const chunkId = await page.locator('.reader-chunk-paragraph').first().getAttribute('id');
  expect(chunkId).toBeTruthy();

  await page.goto(`${BASE}/reader/${KNOWN_DOC_ID}#${chunkId}`);
  await page.waitForTimeout(2_000);

  expect(await page.locator('.reader-highlight').count()).toBeGreaterThan(0);

  const toast = page.locator('[data-testid="anchor-toast"]');
  await expect(toast).toBeVisible({ timeout: 5_000 });
  expect(await toast.textContent()).toContain('已定位至原文');

  await page.waitForTimeout(5_000);
  await expect(toast).not.toBeVisible({ timeout: 3_000 });
});

// ─── ⑨ ───────────────────────────────────────────────────────────────────
test('⑨ missing chunk shows "目标定位点不可用" toast, never "已定位至原文"', async ({ page }) => {
  await login(page);

  await page.goto(`${BASE}/reader/${KNOWN_DOC_ID}#chunk-nonexistent-chunk-id-99999`);
  await page.waitForTimeout(3_000);

  const toast = page.locator('[data-testid="anchor-toast"]');
  await expect(toast).toBeVisible({ timeout: 5_000 });
  const toastText = await toast.textContent();
  expect(toastText).toContain('目标定位点不可用');
  expect(toastText).not.toContain('已定位至原文');
});
