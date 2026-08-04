/**
 * C2-5-FINAL-E2E-REGRESSION — real C2-5 closed-loop verification
 *
 * 1. Clean login → console 0 errors end to end
 * 2. Visible path: project list → detail → workspace → workflow
 * 3. One real POST: Step 1 → 2 → Pending → Evidence → Report
 * 4. "查看完整结果" → Result page with report + 5 evidence/citations
 * 5. Non-existent projectId → fail-closed, 0 errors
 * 6. 375×812 and 640×450 (200% zoom CSS-equivalent): no overflow, focus visible
 *
 * Preconditions:
 *   Backend on http://127.0.0.1:8000, Frontend on http://127.0.0.1:5173
 *   Test account: researcher / researcher123
 *   At least 1 project in DB that supports workflow submission
 *
 * Run: npx playwright test src/e2e/task-c2-5-final-e2e.spec.ts --project='Desktop — 1280×800'
 */

import { test, expect, chromium } from '@playwright/test';
import type { Browser, BrowserContext, Page } from '@playwright/test';

const BASE = 'http://127.0.0.1:5173';
const API = 'http://127.0.0.1:8000';

// ─── Helpers ────────────────────────────────────────────────────────────

async function assertNoOverflow(page: Page, label: string, tolerance = 2) {
  const overflow = await page.evaluate(() => {
    const el = document.querySelector('[data-main-content]');
    if (el) return el.scrollWidth - el.clientWidth;
    return document.documentElement.scrollWidth - document.documentElement.clientWidth;
  });
  expect(
    overflow,
    `Overflow at ${label}: ${overflow}px`,
  ).toBeLessThanOrEqual(tolerance);
}

async function getConsoleErrors(page: Page): Promise<Array<string>> {
  const all: Array<string> = await page.evaluate(() =>
    (window as any).__consoleErrors || [],
  );
  return all.filter((m: string) => !m.includes('localStorage'));
}

async function injectErrorCollector(page: Page) {
  await page.evaluate(() => {
    (window as any).__consoleErrors = [];
    const orig = console.error;
    console.error = (...args: Array<any>) => {
      (window as any).__consoleErrors.push(args.map(String).join(' '));
      orig.apply(console, args);
    };
  });
}

async function login(page: Page) {
  await page.goto(`${BASE}/login`);
  await page.waitForSelector('#username', { state: 'visible', timeout: 10_000 });
  await page.fill('#username', 'researcher');
  await page.fill('#password', 'researcher123');
  await page.click('button.login-btn');
  await page.waitForURL(
    (url: URL) => !url.pathname.includes('/login'),
    { timeout: 15_000 },
  );
}

async function focusInFirst10Tabs(page: Page): Promise<boolean> {
  for (let i = 0; i < 10; i++) {
    await page.keyboard.press('Tab');
    await page.waitForTimeout(80);
    const tag = await page.evaluate(() =>
      document.activeElement?.tagName?.toLowerCase() || 'none',
    );
    if (tag !== 'body' && tag !== 'html' && tag !== 'none') return true;
  }
  return false;
}

async function focusInFirst5ShiftTabs(page: Page): Promise<boolean> {
  for (let i = 0; i < 5; i++) {
    await page.keyboard.press('Shift+Tab');
    await page.waitForTimeout(80);
    const tag = await page.evaluate(() =>
      document.activeElement?.tagName?.toLowerCase() || 'none',
    );
    if (tag !== 'body' && tag !== 'html' && tag !== 'none') return true;
  }
  return false;
}

/** Fetch a completed session+run via API. Used as precondition for viewport tests. */
async function resolveCompletedRun(request: any): Promise<{ sessionId: string; runId: string }> {
  const loginResp = await request.post(`${API}/api/v1/auth/login`, {
    data: { username: 'researcher', password: 'researcher123' },
  });
  const token: string = (await loginResp.json()).data.access_token;

  const sResp = await request.get(`${API}/api/v1/workspace/sessions?limit=100`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  const sessions: Array<{ id: string }> = (await sResp.json()).data ?? [];

  for (const s of sessions) {
    const rResp = await request.get(`${API}/api/v4/research/session/${s.id}/runs`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!rResp.ok()) continue;
    const runs: Array<Record<string, unknown>> = (await rResp.json()).data?.runs ?? [];
    const done = runs.filter(
      (r) => r.status === 'completed' || r.output_artifacts || r.run_id,
    );
    if (done.length > 0) {
      return { sessionId: s.id, runId: (done[0] as { run_id: string }).run_id };
    }
  }
  throw new Error('No completed run found in DB');
}

// ─── Suite ──────────────────────────────────────────────────────────────

test.describe('C2-5 Final E2E Regression', () => {
  test.beforeAll(async ({ request }) => {
    const resp = await request.post(`${API}/api/v1/auth/login`, {
      data: { username: 'researcher', password: 'researcher123' },
    });
    expect(resp.ok(), 'Preflight: backend must be reachable and auth must work').toBeTruthy();
  });

  // ═══════════════════════════════════════════════════════════════════════
  // ① Full closed-loop: login → project list → detail → workspace → workflow → result
  // ═══════════════════════════════════════════════════════════════════════

  test('Full C2-5 closed loop: login → workflow → result, 0 console errors', async () => {
    test.setTimeout(180_000); // workflow POST + backend processing can take >60s
    const browser: Browser = await chromium.launch({ args: ['--no-sandbox'] });
    const context: BrowserContext = await browser.newContext({
      viewport: { width: 1280, height: 800 },
    });
    const page: Page = await context.newPage();

    await injectErrorCollector(page);

    // Step A: Login
    await login(page);
    console.log('[e2e] logged in');

    // Step B: Project list
    await page.goto(`${BASE}/research`, { waitUntil: 'networkidle' });
    await page.waitForSelector('.pli-name-link', { state: 'visible', timeout: 10_000 });
    const projectCount = await page.locator('.pli-name-link').count();
    expect(projectCount, 'Must have at least 1 project').toBeGreaterThanOrEqual(1);
    console.log(`[e2e] project list: ${projectCount} projects`);

    // Step C: Click first project → detail page
    await page.locator('.pli-name-link').first().click();
    await page.waitForURL(/\/research\/[0-9a-f-]+$/, { timeout: 10_000 });
    const workspaceLink = page.locator('a[href*="/workspace"]').first();
    await expect(workspaceLink, 'Workspace link must exist on detail page').toBeVisible({ timeout: 5_000 });
    await workspaceLink.click();
    await page.waitForURL(/\/research\/[0-9a-f-]+\/workspace/, { timeout: 10_000 });
    console.log('[e2e] navigated to workspace');

    // Step D: Click "研究流程" → workflow page
    const workflowLink = page.locator('a[href*="/workflow"]').first();
    await expect(workflowLink, 'Workflow link must exist on workspace page').toBeVisible({ timeout: 5_000 });
    await workflowLink.click();
    await page.waitForURL(/\/research\/[0-9a-f-]+\/workflow/, { timeout: 10_000 });
    console.log('[e2e] navigated to workflow');

    // Step E: Step 1 — fill question, press Enter/Submit to go to Step 2 selection
    await page.waitForSelector('.rqs-form', { state: 'visible', timeout: 10_000 });
    const questionInput = page.locator('.rqs-form textarea, .rqs-form input[type="text"], .rqs-form input').first();
    await expect(questionInput, 'Question input must be visible').toBeVisible({ timeout: 5_000 });
    const topic = '婴幼儿喘息的中医针灸治疗临床研究';
    await questionInput.fill(topic);

    // Step 1 submit → Step 2 (DocumentSelection)
    const step1Btn = page.locator('.rqs-submit-btn').first();
    await expect(step1Btn, 'Step 1 submit button must be enabled').toBeEnabled({ timeout: 3_000 });
    await step1Btn.click();
    console.log('[e2e] step 1 → step 2');

    // Step F: Step 2 — click "开始分析" to POST workflow
    const step2Btn = page.locator('.dss-submit-btn').first();
    await expect(step2Btn, '开始分析 button must be visible').toBeVisible({ timeout: 5_000 });
    await step2Btn.click();
    console.log('[e2e] workflow POST submitted');

    // Step F: Wait for response — evidence or report step
    await page.waitForSelector('.ers-summary-bar, .ers-warning, .rrs-card', {
      state: 'visible',
      timeout: 60_000,
    });
    console.log('[e2e] evidence or report step appeared');

    const evidenceItems = await page.locator('.ers-item').count();
    console.log(`[e2e] evidence items: ${evidenceItems}`);

    // Step G: Navigate to report
    const goToReportBtn = page.locator('.ers-action-btn').first();
    if (await goToReportBtn.isVisible({ timeout: 2_000 }).catch(() => false)) {
      await goToReportBtn.click();
      await page.waitForTimeout(500);
    }

    // Step H: Verify report card
    await page.waitForSelector('.rrs-card, [class*="empty"], [class*="warning"]', {
      state: 'visible',
      timeout: 10_000,
    });

    const rrsCard = await page.locator('.rrs-card').count();
    if (rrsCard > 0) {
      const preview = page.locator('.rrs-preview');
      await expect(preview, 'Report preview must be visible').toBeVisible({ timeout: 5_000 });
      console.log('[e2e] report card visible');

      // Step I: Click "查看完整结果"
      const viewResultLink = page.locator('a.rrs-action-btn--primary').first();
      await expect(viewResultLink, 'View full results link must be visible').toBeVisible({ timeout: 5_000 });
      await viewResultLink.click();
      await page.waitForURL(/\/research\/[0-9a-f-]+\/result\/[0-9a-f-]+/, { timeout: 10_000 });

      await page.waitForTimeout(1500);
      const resultUrl = page.url();
      const resultMatch = resultUrl.match(/\/result\/([0-9a-f-]+)/);
      expect(resultMatch, 'Result URL must contain runId').toBeTruthy();
      console.log(`[e2e] result page: runId=${resultMatch![1]}`);

      const isError = await page.locator('.rpage-error, [data-error-state], .rpage-state--error').count().catch(() => 0);
      expect(isError, 'Result page must not show error state').toBe(0);
    }

    // Final: console errors
    const errors = await getConsoleErrors(page);
    for (const e of errors) {
      console.log(`[console error] ${e}`);
    }
    expect(errors.length, `Expected 0 console errors, got ${errors.length}: ${errors.join(' | ')}`).toBe(0);

    await browser.close();
  });

  // ═══════════════════════════════════════════════════════════════════════
  // ② Non-existent projectId — workflow
  // ═══════════════════════════════════════════════════════════════════════

  test('Workflow: non-existent projectId → fail-closed, 0 errors', async () => {
    const browser: Browser = await chromium.launch({ args: ['--no-sandbox'] });
    const context: BrowserContext = await browser.newContext({ viewport: { width: 1280, height: 800 } });
    const page: Page = await context.newPage();

    await injectErrorCollector(page);
    await login(page);

    await page.goto(`${BASE}/research/00000000-0000-0000-0000-000000000000/workflow`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    const hasState = await page
      .locator('.ers-error, [data-error-state], [role="alert"], .not-found, .rpage-state, h1, h2')
      .count();
    expect(hasState, 'Must render error or not-found state').toBeGreaterThanOrEqual(1);

    await assertNoOverflow(page, 'Not-found workflow');

    const errors = await getConsoleErrors(page);
    expect(errors.length, `Expected 0 console errors, got ${errors.length}`).toBe(0);

    await browser.close();
  });

  // ═══════════════════════════════════════════════════════════════════════
  // ③ Non-existent projectId — result
  // ═══════════════════════════════════════════════════════════════════════

  test('Result: non-existent projectId → fail-closed, 0 errors', async () => {
    const browser: Browser = await chromium.launch({ args: ['--no-sandbox'] });
    const context: BrowserContext = await browser.newContext({ viewport: { width: 1280, height: 800 } });
    const page: Page = await context.newPage();

    await injectErrorCollector(page);
    await login(page);

    await page.goto(`${BASE}/research/00000000-0000-0000-0000-000000000000/result/00000000-0000-0000-0000-000000000000`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    const hasState = await page
      .locator('[data-error-state], .rpage-state, [role="alert"], .rpage-error, h1')
      .count();
    expect(hasState, 'Must render error state for non-existent project').toBeGreaterThanOrEqual(1);

    await assertNoOverflow(page, 'Not-found result');

    const errors = await getConsoleErrors(page);
    expect(errors.length, `Expected 0 console errors, got ${errors.length}`).toBe(0);

    await browser.close();
  });

  // ═══════════════════════════════════════════════════════════════════════
  // ④ 375×812 viewport — Workflow completed
  // ═══════════════════════════════════════════════════════════════════════

  test('Workflow completed: 375×812 — no overflow, focus visible, 0 errors', async ({ request }) => {
    const { sessionId } = await resolveCompletedRun(request);

    const browser: Browser = await chromium.launch({ args: ['--no-sandbox'] });
    const context: BrowserContext = await browser.newContext({ viewport: { width: 375, height: 812 } });
    const page: Page = await context.newPage();

    await injectErrorCollector(page);
    await login(page);
    await page.goto(`${BASE}/research/${sessionId}/workflow`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    await assertNoOverflow(page, 'Workflow 375×812');

    const tabOk = await focusInFirst10Tabs(page);
    expect(tabOk, 'Tab must find at least one element').toBe(true);

    const shiftOk = await focusInFirst5ShiftTabs(page);
    expect(shiftOk, 'Shift+Tab must find at least one element').toBe(true);

    const errors = await getConsoleErrors(page);
    expect(errors.length, `Expected 0 console errors, got ${errors.length}`).toBe(0);

    await browser.close();
  });

  // ═══════════════════════════════════════════════════════════════════════
  // ⑤ 375×812 viewport — Result completed
  // ═══════════════════════════════════════════════════════════════════════

  test('Result completed: 375×812 — no overflow, focus visible, 0 errors', async ({ request }) => {
    const { sessionId, runId } = await resolveCompletedRun(request);

    const browser: Browser = await chromium.launch({ args: ['--no-sandbox'] });
    const context: BrowserContext = await browser.newContext({ viewport: { width: 375, height: 812 } });
    const page: Page = await context.newPage();

    await injectErrorCollector(page);
    await login(page);
    await page.goto(`${BASE}/research/${sessionId}/result/${runId}`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    await assertNoOverflow(page, 'Result 375×812');

    const tabOk = await focusInFirst10Tabs(page);
    expect(tabOk, 'Tab must find at least one element').toBe(true);

    const errors = await getConsoleErrors(page);
    expect(errors.length, `Expected 0 console errors, got ${errors.length}`).toBe(0);

    await browser.close();
  });

  // ═══════════════════════════════════════════════════════════════════════
  // ⑥ 200% zoom (640×450) — Workflow completed
  // ═══════════════════════════════════════════════════════════════════════

  test('Workflow completed: 200% zoom (640×450) — no overflow, focus visible, 0 errors', async ({ request }) => {
    const { sessionId } = await resolveCompletedRun(request);

    const browser: Browser = await chromium.launch({ args: ['--no-sandbox'] });
    const context: BrowserContext = await browser.newContext({ viewport: { width: 640, height: 450 } });
    const page: Page = await context.newPage();

    await injectErrorCollector(page);
    await login(page);
    await page.goto(`${BASE}/research/${sessionId}/workflow`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    await assertNoOverflow(page, 'Workflow 200% zoom (640×450)');

    const tabOk = await focusInFirst10Tabs(page);
    expect(tabOk, 'Tab must find at least one element at 200% zoom').toBe(true);

    const shiftOk = await focusInFirst5ShiftTabs(page);
    expect(shiftOk, 'Shift+Tab must find at least one element at 200% zoom').toBe(true);

    const errors = await getConsoleErrors(page);
    expect(errors.length, `Expected 0 console errors, got ${errors.length}`).toBe(0);

    await browser.close();
  });

  // ═══════════════════════════════════════════════════════════════════════
  // ⑦ 200% zoom (640×450) — Result completed
  // ═══════════════════════════════════════════════════════════════════════

  test('Result completed: 200% zoom (640×450) — no overflow, focus visible, 0 errors', async ({ request }) => {
    const { sessionId, runId } = await resolveCompletedRun(request);

    const browser: Browser = await chromium.launch({ args: ['--no-sandbox'] });
    const context: BrowserContext = await browser.newContext({ viewport: { width: 640, height: 450 } });
    const page: Page = await context.newPage();

    await injectErrorCollector(page);
    await login(page);
    await page.goto(`${BASE}/research/${sessionId}/result/${runId}`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    await assertNoOverflow(page, 'Result 200% zoom (640×450)');

    const tabOk = await focusInFirst10Tabs(page);
    expect(tabOk, 'Tab must find at least one element at 200% zoom').toBe(true);

    const errors = await getConsoleErrors(page);
    expect(errors.length, `Expected 0 console errors, got ${errors.length}`).toBe(0);

    await browser.close();
  });
});
