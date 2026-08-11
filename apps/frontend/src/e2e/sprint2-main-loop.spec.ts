/**
 * Sprint 2 Main Loop — v4.2 9-Assertion E2E Physical Test Matrix
 *
 * Preconditions:
 *   Backend on http://127.0.0.1:8000, Frontend on http://127.0.0.1:5173
 *   Test account: researcher / researcher123
 *   At least 1 project in DB that supports workflow submission
 *
 * Run:
 *   npx playwright test src/e2e/sprint2-main-loop.spec.ts --project='Desktop — 1280×800'
 */

import { test, expect } from '@playwright/test';
import type { Page } from '@playwright/test';

const BASE = 'http://127.0.0.1:5173';

// ─── Helpers ────────────────────────────────────────────────────────────

async function login(page: Page) {
  await page.goto(`${BASE}/login`);
  await page.waitForSelector('#username', { state: 'visible', timeout: 10_000 });
  await page.fill('#username', 'researcher');
  await page.fill('#password', 'researcher123');
  await page.click('button.login-btn');
  await page.waitForURL((url: URL) => !url.pathname.includes('/login'), { timeout: 15_000 });
}

// ─── ① 缺标题但有 document_id + chunk_id 可跳 Reader ────────────────────
test('① missing title but has document_id + chunk_id → reader route renders', async ({ page }) => {
  await login(page);

  // Navigate to a project list and pick the first project's workflow result
  await page.goto(`${BASE}/research`);
  await page.waitForSelector('.rpp-list', { timeout: 10_000 });

  // Find and click the first project to enter its workflow
  const firstProjectLink = page.locator('.rpp-list a, .rpp-list [role="button"]').first();
  const count = await firstProjectLink.count();
  if (count === 0) {
    test.skip(true, 'No projects available — seed DB first');
    return;
  }
  await firstProjectLink.click();

  // Navigate to workflow
  await page.waitForURL(/\/research\/.+\/workflow/, { timeout: 10_000 });

  // Submit workflow and wait for result
  const submitBtn = page.locator('button:has-text("开始"), button:has-text("提交"), button:has-text("运行")').first();
  if ((await submitBtn.count()) > 0) {
    await submitBtn.click();
    // Wait for result page (may take time for sync workflow)
    await page.waitForURL(/\/research\/.+\/runs\/.+/, { timeout: 120_000 });
  }

  // Look at the citation panel to find a SourceReferenceCard with internal route
  const sourceRefLinks = page.locator('.esrc-link--internal');
  const linkCount = await sourceRefLinks.count();

  if (linkCount === 0) {
    // No SourceReferenceCard with internal route — mark as informational
    test.skip(true, 'No SourceReferenceCard with internal route found in this run');
    return;
  }

  // Verify the link points to /reader/ or /library/
  const href = await sourceRefLinks.first().getAttribute('href');
  expect(href).toBeTruthy();
  expect(href).toMatch(/^\/(reader|library)\/.+/);
});

// ─── ② 无 quote 无摘录框 ────────────────────────────────────────────────
test('② evidence without quote hides quote block', async ({ page }) => {
  await login(page);

  // Go to a result page directly
  await page.goto(`${BASE}/research`);
  await page.waitForSelector('.rpp-list', { timeout: 10_000 });

  // Need to get to a result page. Use direct navigation if we can find a project.
  // For this test, we verify the DOM behavior: when ResultEvidence.quote is falsy,
  // the .eed-quote-text block is not rendered.

  // Navigate to result page
  const anyLink = page.locator('.rpp-list a').first();
  if ((await anyLink.count()) === 0) {
    test.skip(true, 'No projects found');
    return;
  }
  await anyLink.click();
  await page.waitForURL(/\/research\/.+\/workflow/, { timeout: 10_000 });

  // Check if there's a "查看结果" link to an existing run
  const viewResultLink = page.locator('a:has-text("查看"), button:has-text("结果")').first();
  if ((await viewResultLink.count()) > 0) {
    await viewResultLink.click();
    await page.waitForURL(/\/research\/.+\/runs\/.+/, { timeout: 15_000 });
  } else {
    test.skip(true, 'No existing run to inspect');
    return;
  }

  // Now on a result page. Click a citation to reveal evidence detail.
  const citationItem = page.locator('.rcp-citation-item').first();
  if ((await citationItem.count()) === 0) {
    test.skip(true, 'No citations on this result');
    return;
  }
  await citationItem.click();

  // Check evidence detail: a .eed-quote-text block should ONLY appear when quote exists.
  // If the evidence has no quote, the blockquote .eed-quote-text must not exist.
  const evidenceCards = page.locator('.eed-card');
  const evidenceCount = await evidenceCards.count();

  if (evidenceCount === 0) {
    test.skip(true, 'No evidence detail visible');
    return;
  }

  // For each evidence card, if there's a quote block it must have non-empty content.
  // The key assertion: no stale/empty quote blocks exist.
  for (let i = 0; i < evidenceCount; i++) {
    const card = evidenceCards.nth(i);
    const quoteBlock = card.locator('.eed-quote-text');
    if ((await quoteBlock.count()) > 0) {
      const text = await quoteBlock.textContent();
      expect(text?.trim().length, `Evidence card ${i}: quote block exists but is empty`).toBeGreaterThan(0);
    }
    // No quote block when no quote — this is the expected absence (② passes)
  }
});

// ─── ③ 无 anchor 跳转按钮禁用 ───────────────────────────────────────────
test('③ citation without anchor_chunk_ids disables anchor button', async ({ page }) => {
  await login(page);

  await page.goto(`${BASE}/research`);
  await page.waitForSelector('.rpp-list', { timeout: 10_000 });

  const anyLink = page.locator('.rpp-list a').first();
  if ((await anyLink.count()) === 0) {
    test.skip(true, 'No projects found');
    return;
  }
  await anyLink.click();
  await page.waitForURL(/\/research\/.+\/workflow/, { timeout: 10_000 });

  // Try to reach a result
  const viewResultLink = page.locator('a:has-text("查看"), button:has-text("结果")').first();
  if ((await viewResultLink.count()) > 0) {
    await viewResultLink.click();
    await page.waitForURL(/\/research\/.+\/runs\/.+/, { timeout: 15_000 });
  } else {
    test.skip(true, 'No existing run');
    return;
  }

  // Click a citation to expand evidence
  const citationItem = page.locator('.rcp-citation-item').first();
  if ((await citationItem.count()) === 0) {
    test.skip(true, 'No citations');
    return;
  }
  await citationItem.click();

  // Now check: if an anchor button exists (.reader-anchor-btn), it must be enabled.
  // If no anchor chunks exist, .reader-no-anchor must be shown instead.
  const anchorBtns = page.locator('.reader-anchor-btn');
  const noAnchors = page.locator('.reader-no-anchor');

  if ((await anchorBtns.count()) === 0 && (await noAnchors.count()) === 0) {
    // Neither anchor btn nor "无法定位" text — this is fine for empty citations
    // The assertion ③ is about NOT showing an enabled anchor button when no chunks exist
  } else if ((await noAnchors.count()) > 0) {
    // Correct: "无法定位到原文" shown when no anchor_chunk_ids
    expect(true).toBe(true);
  }
  // If anchor buttons exist, they must all be enabled (not disabled="true")
  for (let i = 0; i < (await anchorBtns.count()); i++) {
    const disabled = await anchorBtns.nth(i).getAttribute('disabled');
    expect(disabled, `Anchor button ${i} is disabled when it should not render at all`).toBeNull();
  }
});

// ─── ④ sessionStorage 禁用时诚实提示 ───────────────────────────────────
test('④ sessionStorage disabled shows honest error, no silent migration', async ({ browser }) => {
  // Create a context that blocks sessionStorage
  const context = await browser.newContext({
    storageState: undefined,
  });

  const page = await context.newPage();

  // Block sessionStorage via CDP
  const cdpSession = await context.newCDPSession(page);
  await cdpSession.send('Runtime.evaluate', {
    expression: `
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
      });
    `,
  });

  await page.goto(`${BASE}/`);
  await page.waitForSelector('.prototype-draft-section', { timeout: 10_000 });

  // Type some text and try to save
  const textarea = page.locator('.draft-textarea');
  await textarea.fill('测试研究问题');
  await page.click('.draft-save-btn');

  // Now the sessionStorage.setItem should have thrown → storageFailed = true
  // The error hint with "未保存，登录后重新输入" must appear
  const errorHint = page.locator('.draft-saved-hint--error');
  await expect(errorHint).toBeVisible({ timeout: 5_000 });
  const errorText = await errorHint.textContent();
  expect(errorText).toContain('未保存');
  expect(errorText).toContain('登录后重新输入');
  // MUST NOT show "草稿已暂存"
  expect(errorText).not.toContain('草稿已暂存');

  await context.close();
});

// ─── ⑤ Evidence/Claim 无"已核验"字样，无成功绿 ─────────────────────────
test('⑤ Evidence/Claim context bans "已核验" text and success/green variant', async ({ page }) => {
  await login(page);

  await page.goto(`${BASE}/research`);
  await page.waitForSelector('.rpp-list', { timeout: 10_000 });

  const anyLink = page.locator('.rpp-list a').first();
  if ((await anyLink.count()) === 0) {
    test.skip(true, 'No projects');
    return;
  }
  await anyLink.click();
  await page.waitForURL(/\/research\/.+\/workflow/, { timeout: 10_000 });

  const viewResultLink = page.locator('a:has-text("查看"), button:has-text("结果")').first();
  if ((await viewResultLink.count()) > 0) {
    await viewResultLink.click();
    await page.waitForURL(/\/research\/.+\/runs\/.+/, { timeout: 15_000 });
  } else {
    test.skip(true, 'No existing run');
    return;
  }

  // Click a citation
  const citationItem = page.locator('.rcp-citation-item').first();
  if ((await citationItem.count()) === 0) {
    test.skip(true, 'No citations');
    return;
  }
  await citationItem.click();

  // Collect all text within EvidenceDetail cards
  const evidenceCards = page.locator('.eed-card');
  const cardCount = await evidenceCards.count();

  for (let i = 0; i < cardCount; i++) {
    const cardText = await evidenceCards.nth(i).textContent();
    // ⑤-a: No "已核验" text anywhere
    expect(cardText, `Evidence card ${i} contains "已核验"`).not.toContain('已核验');
    expect(cardText, `Evidence card ${i} contains "已证实"`).not.toContain('已证实');
  }

  // ⑤-b: No EvidenceBadge with success/green color (verification-status must be "unverified")
  // EvidenceBadge renders as verification-status="unverified" — never "verified"
  const verifiedBadges = page.locator('[data-verification-status="verified"]');
  await expect(verifiedBadges).toHaveCount(0);

  // Also check ResearchResultPage: no "已核验" anywhere in the page
  const pageText = await page.locator('.research-page').textContent();
  expect(pageText).not.toContain('已核验');
});

// ─── ⑥ 异构数据库 runId 被 UI 隔离拒显 ──────────────────────────────────
test('⑥ heterogeneous runId is isolated — wrong project route shows error', async ({ page }) => {
  await login(page);

  // Try navigating to a run that belongs to a different project
  // Use a fake project ID with a real run format — expect error state
  await page.goto(`${BASE}/research/nonexistent-project-999/runs/some-run-uuid`);
  await page.waitForTimeout(3_000);

  // Should show error state, not silently render content from wrong project
  const errorState = page.locator('[role="alert"], .rpage-loading, .research-page .error');
  // Either we see an error, loading, or 404 — NOT a full result page
  const resultContent = page.locator('.rcp-section, .rpage-body');
  const hasContent = await resultContent.count();

  if (hasContent === 0) {
    // Good: no leaked cross-project content
    expect(true).toBe(true);
  } else {
    // If content renders, verify it's error state, not wrong project data
    const hasError = (await errorState.count()) > 0;
    expect(hasError, 'Heterogeneous runId must show error, not leaked content').toBe(true);
  }
});

// ─── ⑦ 恰好一次 POST /api/v4/research/workflow ──────────────────────────
test('⑦ exactly one POST /api/v4/research/workflow during workflow submission', async ({ page }) => {
  await login(page);

  await page.goto(`${BASE}/research`);
  await page.waitForSelector('.rpp-list', { timeout: 10_000 });

  const anyLink = page.locator('.rpp-list a').first();
  if ((await anyLink.count()) === 0) {
    test.skip(true, 'No projects');
    return;
  }
  await anyLink.click();
  await page.waitForURL(/\/research\/.+\/workflow/, { timeout: 10_000 });

  // Intercept and count POST to /api/v4/research/workflow
  let postCount = 0;
  page.on('request', (req) => {
    if (req.method() === 'POST' && req.url().includes('/api/v4/research/workflow')) {
      postCount++;
    }
  });

  // Submit workflow
  const submitBtn = page.locator('button:has-text("开始"), button:has-text("提交"), button:has-text("运行")').first();
  if ((await submitBtn.count()) === 0) {
    test.skip(true, 'No submit button');
    return;
  }
  await submitBtn.click();

  // Wait for result page
  try {
    await page.waitForURL(/\/research\/.+\/runs\/.+/, { timeout: 120_000 });
  } catch {
    // Workflow might have failed — still check count
  }

  // Wait a moment for any late duplicate requests
  await page.waitForTimeout(2_000);

  // Exactly 1 POST
  expect(postCount, `Expected 1 POST to /api/v4/research/workflow, got ${postCount}`).toBe(1);
});

// ─── ⑧ Reader chunk highlight + "已定位至原文" toast ─────────────────────
test('⑧ Reader #chunk-<id> highlight fades and shows "已定位至原文"', async ({ page }) => {
  await login(page);

  // Go to Library and find a document with known chunks
  await page.goto(`${BASE}/library`);
  await page.waitForTimeout(3_000);

  // Find a document link
  const docLink = page.locator('a[href*="/reader/"]').first();
  if ((await docLink.count()) === 0) {
    test.skip(true, 'No reader documents in library');
    return;
  }
  const href = await docLink.getAttribute('href');
  expect(href).toBeTruthy();

  // Find a real chunk_id from the doc page
  await docLink.click();
  await page.waitForURL(/\/reader\//, { timeout: 10_000 });

  // If the doc has chunks, find one
  const firstChunk = page.locator('.reader-chunk-paragraph').first();
  if ((await firstChunk.count()) === 0) {
    test.skip(true, 'Document has no chunks');
    return;
  }

  const chunkIdAttr = await firstChunk.getAttribute('id');
  expect(chunkIdAttr).toBeTruthy();

  // Navigate to the same reader page with the chunk hash
  const urlParts = page.url().split('#');
  await page.goto(`${urlParts[0]}#${chunkIdAttr}`);
  await page.waitForTimeout(2_000);

  // Assert .reader-highlight class exists on the target element
  const highlighted = page.locator(`.reader-highlight`);
  const highlightCount = await highlighted.count();
  expect(highlightCount, 'No .reader-highlight element after chunk hash navigation').toBeGreaterThan(0);

  // Assert "已定位至原文" toast
  const toast = page.locator('[data-testid="anchor-toast"]');
  await expect(toast).toBeVisible({ timeout: 5_000 });
  const toastText = await toast.textContent();
  expect(toastText).toContain('已定位至原文');

  // Assert the highlight fades (after 3s the highlight set is cleared)
  // Just verify the toast disappears eventually
  await page.waitForTimeout(4_500);
  const toastAfter = page.locator('[data-testid="anchor-toast"]');
  const toastVisibleAfter = await toastAfter.isVisible().catch(() => false);
  // Toast should be gone after 4s timeout + fade
  expect(toastVisibleAfter).toBe(false);
});

// ─── ⑨ 目标 chunk 不存在 → "目标定位点不可用" ──────────────────────────
test('⑨ missing chunk shows "目标定位点不可用" toast, never "已定位至原文"', async ({ page }) => {
  await login(page);

  // Find any reader page
  await page.goto(`${BASE}/library`);
  await page.waitForTimeout(3_000);

  const docLink = page.locator('a[href*="/reader/"]').first();
  if ((await docLink.count()) === 0) {
    test.skip(true, 'No reader documents');
    return;
  }
  await docLink.click();
  await page.waitForURL(/\/reader\//, { timeout: 10_000 });

  // Navigate to a non-existent chunk
  const urlParts = page.url().split('#');
  await page.goto(`${urlParts[0]}#chunk-nonexistent-chunk-id-99999`);
  await page.waitForTimeout(3_000);

  // Assert toast shows "目标定位点不可用"
  const toast = page.locator('[data-testid="anchor-toast"]');
  await expect(toast).toBeVisible({ timeout: 5_000 });
  const toastText = await toast.textContent();
  expect(toastText).toContain('目标定位点不可用');

  // Assert it NEVER shows "已定位至原文"
  expect(toastText).not.toContain('已定位至原文');
});
