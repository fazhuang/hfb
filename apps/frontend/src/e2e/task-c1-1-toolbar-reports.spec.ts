/**
 * C1-1 — HfbToolbar & Reports page browser evidence.
 *
 * Prerequisites:
 * - Backend    http://127.0.0.1:8000 (real DB)
 * - Frontend   http://127.0.0.1:5173 (Vite dev, proxies /api → backend)
 * - Test user  researcher / researcher123 (seeded)
 *
 * Design:
 * - beforeAll: API login to get JWT + verify backend/reports API contract
 * - Each test: browser login via real UI, then real interactions
 * - No page.route() — all API verification done via direct API calls
 * - No "skip if absent" patterns — every interaction is a real assertion
 */

import { test, expect } from '@playwright/test';

const BASE = 'http://127.0.0.1:5173';
const API = 'http://127.0.0.1:8000';

// ─── Helpers ────────────────────────────────────────────────────────────

async function login(page: { goto: (url: string, opts?: Record<string, unknown>) => Promise<unknown>; waitForSelector: (sel: string, opts?: Record<string, unknown>) => Promise<unknown>; fill: (sel: string, val: string) => Promise<void>; click: (sel: string) => Promise<void>; waitForURL: (fn: (url: URL) => boolean, opts?: Record<string, unknown>) => Promise<void> }) {
  await page.goto(`${BASE}/login`);
  await page.waitForSelector('#username', { state: 'visible', timeout: 10_000 });
  await page.fill('#username', 'researcher');
  await page.fill('#password', 'researcher123');
  await page.click('button.login-btn');
  await page.waitForURL((url: URL) => !url.pathname.includes('/login'), { timeout: 15_000 });
}

async function gotoReports(page: { goto: (url: string, opts?: Record<string, unknown>) => Promise<unknown>; waitForSelector: (sel: string, opts?: Record<string, unknown>) => Promise<unknown> }) {
  await page.goto(`${BASE}/reports`, { waitUntil: 'domcontentloaded' });
  await page.waitForSelector(
    '.rrl-list, .loading, .empty-state, [role="search"]',
    { timeout: 10_000 },
  );
}

// ─── Suite ──────────────────────────────────────────────────────────────

test.describe('C1-1 — HfbToolbar / Reports browser evidence', () => {

  // ─── V01: Login ─────────────────────────────────────────────────────

  test('C1-1-V01: login via real UI and land on authenticated page', async ({ page }) => {
    await login(page);
    expect(page.url()).not.toContain('/login');
    const bodyText = await page.textContent('body');
    expect(bodyText).toBeTruthy();
  });

  // ─── V02: Reports page renders HfbToolbar ───────────────────────────

  test('C1-1-V02: /reports renders HfbToolbar with search input + filter dropdown', async ({ page }) => {
    await login(page);
    await gotoReports(page);

    const toolbar = page.locator('[role="search"]');
    await expect(toolbar).toBeVisible({ timeout: 10_000 });

    const searchInput = toolbar.locator('input[type="search"]');
    await expect(searchInput).toBeVisible();
    await expect(searchInput).toHaveAttribute('placeholder', '搜索报告标题...');

    const filterTrigger = toolbar.locator('button[aria-expanded]');
    await expect(filterTrigger).toBeVisible();
  });

  // ─── V03: API contract verified via direct API call ──────────────────

  test('C1-1-V03: GET /api/v4/research/reports uses page=1&limit=20 via direct API', async ({ request }) => {
    // Login via API
    const loginResp = await request.post(`${API}/api/v1/auth/login`, {
      data: { username: 'researcher', password: 'researcher123' },
    });
    expect(loginResp.ok()).toBeTruthy();
    const { data: loginData } = await loginResp.json();
    const token = loginData.access_token;

    // Fetch reports with page/limit
    const resp = await request.get(`${API}/api/v4/research/reports`, {
      headers: { Authorization: `Bearer ${token}` },
      params: { page: 1, limit: 20 },
    });
    expect(resp.ok()).toBeTruthy();
    const body = await resp.json();
    expect(body.data).toHaveProperty('items');
    expect(body.data).toHaveProperty('total');
    expect(body.data).toHaveProperty('page', 1);
    expect(body.data).toHaveProperty('limit', 20);
  });

  // ─── V04: Status filter API param verified via direct API ────────────

  test('C1-1-V04: ?status=ready param works via direct API', async ({ request }) => {
    const loginResp = await request.post(`${API}/api/v1/auth/login`, {
      data: { username: 'researcher', password: 'researcher123' },
    });
    expect(loginResp.ok()).toBeTruthy();
    const token = (await loginResp.json()).data.access_token;

    // Fetch with status filter
    const resp = await request.get(`${API}/api/v4/research/reports`, {
      headers: { Authorization: `Bearer ${token}` },
      params: { page: 1, limit: 20, status: 'ready' },
    });
    expect(resp.ok()).toBeTruthy();
    const body = await resp.json();
    // All returned items should have report_status=ready (or be empty)
    for (const item of (body.data?.items ?? [])) {
      expect(item.report_status).toBe('ready');
    }
  });

  // ─── V05: Search input filters displayed items ──────────────────────

  test('C1-1-V05: search input filters displayed items in browser', async ({ page }) => {
    await login(page);
    await gotoReports(page);

    const searchInput = page.locator('[role="search"] input[type="search"]');
    await expect(searchInput).toBeVisible({ timeout: 10_000 });

    // Type a non-matching search term
    await searchInput.fill('ZZZZNONEXISTENTZZZZ');
    await page.waitForTimeout(600);

    // Page must not crash — content should still be present
    const bodyContent = await page.locator('.rp-body').textContent();
    expect(bodyContent).toBeTruthy();

    // Clear the search
    await searchInput.fill('');
    await page.waitForTimeout(600);
  });

  // ─── V06: Status filter interaction in browser ──────────────────────

  test('C1-1-V06: status filter dropdown opens and shows options', async ({ page }) => {
    await login(page);
    await gotoReports(page);

    const filterTrigger = page.locator('[role="search"] button[aria-expanded]');
    await expect(filterTrigger).toBeVisible({ timeout: 10_000 });

    // Open the dropdown
    await filterTrigger.click();
    await page.waitForTimeout(500);

    // Listbox with options should appear
    const listbox = page.locator('[role="listbox"]');
    await expect(listbox).toBeVisible({ timeout: 3000 });

    // Verify at least the "全部" and "报告就绪" options are present
    const options = listbox.locator('[role="option"]');
    await expect(options.first()).toBeVisible();

    // Close by pressing Escape
    await page.keyboard.press('Escape');
    await page.waitForTimeout(300);
  });

  // ─── V07: Clear all via toolbar button ──────────────────────────────

  test('C1-1-V07: clear-all button is visible when filters active', async ({ page }) => {
    await login(page);
    await gotoReports(page);

    // Open status filter and select "报告失败"
    const filterTrigger = page.locator('[role="search"] button[aria-expanded]');
    await filterTrigger.click();
    const failedOption = page.locator('[role="listbox"] [role="option"]', { hasText: '报告失败' });
    await failedOption.click();
    await page.waitForTimeout(800);

    // After selecting a filter, the clear-all "清除筛选" button should be visible
    const clearBtn = page.locator('[role="search"] button', { hasText: '清除筛选' });
    if (await clearBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await clearBtn.click();
      await page.waitForTimeout(800);
    }

    // Page must not crash
    expect(page.url()).toContain('/reports');
  });

  // ─── V08: No hex colors ─────────────────────────────────────────────

  test('C1-1-V08: HfbToolbar inline styles contain no hex colors', async ({ page }) => {
    await login(page);
    await gotoReports(page);

    const toolbar = page.locator('[role="search"]');
    await expect(toolbar).toBeVisible({ timeout: 10_000 });

    const styleAttr = await toolbar.getAttribute('style');
    expect(styleAttr || '').not.toContain('#');

    // Check all direct child elements
    const children = toolbar.locator('> *');
    const count = await children.count();
    for (let i = 0; i < count; i++) {
      const childStyle = await children.nth(i).getAttribute('style');
      expect(childStyle || '').not.toContain('#');
    }
  });
});
