/**
 * C1-1 — HfbToolbar & Reports page browser evidence (BLOCK_RELEASE grade).
 *
 * Prerequisites:
 * - Backend    http://127.0.0.1:8000 (real DB, real user seed)
 * - Frontend   http://127.0.0.1:5173 (Vite dev, proxies /api → backend)
 * - Test user  researcher / researcher123 (seeded)
 *
 * Design:
 * - beforeAll: none (Playwright manages browser context — each test is self-contained)
 * - No page.route() — all interactions hit real backend
 * - No "skip if absent" / "early pass" branches — every assertion is a hard must-pass
 * - Direct API calls for contract verification (V03, V04)
 * - Browser interactions for real UI evidence (all Vxx… tests)
 * - V12 uses temporary page.route() as controlled fault injection to exercise
 *   the error→retry recovery path — this is NOT data mocking; it is the standard
 *   Playwright pattern for testing error recovery. The route is removed before
 *   retry so the retry hits the real backend.
 */

import { test, expect } from '@playwright/test';

const API = 'http://127.0.0.1:8000';

// ═══════════════════════════════════════════════════════════════════════════════
// Helpers
// ═══════════════════════════════════════════════════════════════════════════════

/** Shared API login helper — fetches a fresh JWT for direct API tests and inspection. */
async function apiToken(request: { post: (url: string, opts: Record<string, unknown>) => Promise<{ ok: () => boolean; json: () => Promise<{ data: { access_token: string } }> }> }) {
  const resp = await request.post(`${API}/api/v1/auth/login`, {
    data: { username: 'researcher', password: 'researcher123' },
  });
  expect(resp.ok()).toBeTruthy();
  const body = await resp.json();
  return body.data.access_token;
}

// ═══════════════════════════════════════════════════════════════════════════════
// Suite
// ═══════════════════════════════════════════════════════════════════════════════

test.describe('C1-1 — HfbToolbar / Reports browser evidence', () => {

  // ── V01: Real UI login ────────────────────────────────────────────────────

  test('C1-1-V01: real UI login lands on authenticated page', async ({ page }) => {
    await page.goto('/login');
    await page.waitForSelector('#username', { state: 'visible', timeout: 10_000 });
    await page.fill('#username', 'researcher');
    await page.fill('#password', 'researcher123');
    await page.click('button.login-btn');
    await page.waitForURL((url: URL) => !url.pathname.includes('/login'), { timeout: 15_000 });

    // Must NOT be on login page — real redirect happened
    expect(page.url()).not.toContain('/login');

    // Body must have content (authenticated page rendered)
    const bodyText = await page.textContent('body');
    expect(bodyText).toBeTruthy();
  });

  // ── V02: HfbToolbar renders on Reports page ──────────────────────────────

  test('C1-1-V02: /reports renders HfbToolbar with all required elements', async ({ page }) => {
    // Login
    await page.goto('/login');
    await page.waitForSelector('#username', { state: 'visible', timeout: 10_000 });
    await page.fill('#username', 'researcher');
    await page.fill('#password', 'researcher123');
    await page.click('button.login-btn');
    await page.waitForURL((url: URL) => !url.pathname.includes('/login'), { timeout: 15_000 });

    // Navigate to Reports
    await page.goto('/reports', { waitUntil: 'domcontentloaded' });

    // Toolbar must be present with the search role
    const toolbar = page.locator('[role="search"]');
    await expect(toolbar).toBeVisible({ timeout: 10_000 });

    // Search input with placeholder is present
    const searchInput = toolbar.locator('input[type="search"]');
    await expect(searchInput).toBeVisible();
    await expect(searchInput).toHaveAttribute('placeholder', '搜索报告标题...');

    // Filter dropdown trigger is present
    const filterTrigger = toolbar.locator('button[aria-expanded]');
    await expect(filterTrigger).toBeVisible();

    // A real report list or one of the state indicators must be present
    // (loading, empty, or list — exactly one must be visible)
    const anyContent = page.locator(
      '.rrl-list, .loading-state, .empty-state, [role="alert"]',
    );
    await expect(anyContent.first()).toBeVisible({ timeout: 10_000 });
  });

  // ── V03: API contract — page/limit via direct API ────────────────────────

  test('C1-1-V03: GET /api/v4/research/reports returns page/limit contract via direct API', async ({ request }) => {
    const token = await apiToken(request);

    const resp = await request.get(`${API}/api/v4/research/reports`, {
      headers: { Authorization: `Bearer ${token}` },
      params: { page: 1, limit: 20 },
    });
    expect(resp.ok()).toBeTruthy();

    const body = await resp.json();
    expect(body.data).toBeDefined();
    expect(body.data).toHaveProperty('items');
    expect(body.data).toHaveProperty('total');
    expect(body.data).toHaveProperty('page', 1);
    expect(body.data).toHaveProperty('limit', 20);

    // items must be an array (may be empty; that's fine)
    const items = body.data.items;
    expect(Array.isArray(items)).toBe(true);
    // total must be a non-negative number
    expect(typeof body.data.total).toBe('number');
    expect(body.data.total).toBeGreaterThanOrEqual(0);
  });

  // ── V04: API contract — ?status=ready filter verified via direct API ─────

  test('C1-1-V04: ?status=ready returns only ready items via direct API', async ({ request }) => {
    const token = await apiToken(request);

    const resp = await request.get(`${API}/api/v4/research/reports`, {
      headers: { Authorization: `Bearer ${token}` },
      params: { page: 1, limit: 50, status: 'ready' },
    });
    expect(resp.ok()).toBeTruthy();

    const body = await resp.json();
    const items = body.data?.items ?? [];

    // Every returned item must have report_status === 'ready'
    for (const item of items) {
      expect(item.report_status).toBe('ready');
    }

    // Verify that the filter actually reduces: ?status=failed must return 0
    const failedResp = await request.get(`${API}/api/v4/research/reports`, {
      headers: { Authorization: `Bearer ${token}` },
      params: { page: 1, limit: 50, status: 'failed' },
    });
    expect(failedResp.ok()).toBeTruthy();
    const failedBody = await failedResp.json();
    const failedItems = failedBody.data?.items ?? [];

    // If all items are ready, status=failed must return 0
    expect(failedItems.length).toBe(0);
  });

  // ── V05: Search input filters displayed items in browser ─────────────────

  test('C1-1-V05: search input filters displayed items in browser with real list', async ({ page }) => {
    // Login
    await page.goto('/login');
    await page.waitForSelector('#username', { state: 'visible', timeout: 10_000 });
    await page.fill('#username', 'researcher');
    await page.fill('#password', 'researcher123');
    await page.click('button.login-btn');
    await page.waitForURL((url: URL) => !url.pathname.includes('/login'), { timeout: 15_000 });

    // Navigate to Reports
    await page.goto('/reports', { waitUntil: 'domcontentloaded' });

    // Wait for real data to load (the list or empty state, but NOT loading)
    // Since we have 43 ready items, the list must appear
    const reportList = page.locator('.rrl-list');
    await expect(reportList).toBeVisible({ timeout: 15_000 });

    // Count initial list items
    const initialCount = await reportList.locator('[role="listitem"]').count();
    expect(initialCount).toBeGreaterThanOrEqual(1);

    // Type a non-matching search term
    const searchInput = page.locator('[role="search"] input[type="search"]');
    await searchInput.fill('ZZZZNONEXISTENTZZZZ');

    // Wait for debounce (300ms) + DOM update
    await page.waitForTimeout(800);

    // After filtering with a non-matching term, the list items must
    // disappear AND the filter-no-results empty state must appear
    const noMatchEmpty = page.locator('.empty-state');
    await expect(noMatchEmpty).toBeVisible({ timeout: 5000 });
    await expect(noMatchEmpty).toContainText('暂无匹配的报告');

    // Clear search
    await searchInput.fill('');
    await page.waitForTimeout(800);

    // The list must reappear
    await expect(reportList).toBeVisible({ timeout: 5000 });
    const restoredCount = await reportList.locator('[role="listitem"]').count();
    expect(restoredCount).toBeGreaterThanOrEqual(1);
  });

  // ── V06: Filter dropdown opens and shows all five options ────────────────

  test('C1-1-V06: status filter dropdown opens and shows all five options', async ({ page }) => {
    // Login
    await page.goto('/login');
    await page.waitForSelector('#username', { state: 'visible', timeout: 10_000 });
    await page.fill('#username', 'researcher');
    await page.fill('#password', 'researcher123');
    await page.click('button.login-btn');
    await page.waitForURL((url: URL) => !url.pathname.includes('/login'), { timeout: 15_000 });

    // Navigate to Reports
    await page.goto('/reports', { waitUntil: 'domcontentloaded' });

    // Wait for data to load
    await expect(page.locator('.rrl-list, .empty-state').first()).toBeVisible({ timeout: 15_000 });

    // Open the filter dropdown
    const filterTrigger = page.locator('[role="search"] button[aria-expanded]');
    await filterTrigger.click();

    // The listbox must appear
    const listbox = page.locator('[role="listbox"]');
    await expect(listbox).toBeVisible({ timeout: 3000 });

    // All five options must be present
    const expectedOptions = ['全部', '报告就绪', '报告缺失', '报告失败', '待生成'];
    for (const label of expectedOptions) {
      const option = listbox.locator('[role="option"]', { hasText: label });
      await expect(option).toBeVisible({ timeout: 2000 });
    }

    // Close dropdown by clicking outside (triggers onClickOutside handler)
    await page.locator('body').click({ position: { x: 10, y: 10 } });
    await expect(listbox).not.toBeVisible({ timeout: 3000 });
  });

  // ── V07: Clear-all button appears, clears filters, and disappears ────────

  test('C1-1-V07: clear-all button lifecycle — appear, clear, disappear', async ({ page }) => {
    // Login
    await page.goto('/login');
    await page.waitForSelector('#username', { state: 'visible', timeout: 10_000 });
    await page.fill('#username', 'researcher');
    await page.fill('#password', 'researcher123');
    await page.click('button.login-btn');
    await page.waitForURL((url: URL) => !url.pathname.includes('/login'), { timeout: 15_000 });

    // Navigate to Reports
    await page.goto('/reports', { waitUntil: 'domcontentloaded' });

    // Wait for data to load
    await expect(page.locator('.rrl-list, .empty-state').first()).toBeVisible({ timeout: 15_000 });

    // Initially, with no filters active, clear-all button must NOT be visible
    const clearBtn = page.locator('[role="search"] button:has-text("清除筛选")');
    await expect(clearBtn).not.toBeVisible();

    // Open filter and select "报告失败" (which returns 0 items)
    const filterTrigger = page.locator('[role="search"] button[aria-expanded]');
    await filterTrigger.click();
    const listbox = page.locator('[role="listbox"]');
    await expect(listbox).toBeVisible({ timeout: 3000 });
    await listbox.locator('[role="option"]', { hasText: '报告失败' }).click();

    // Wait for the server re-fetch
    await page.waitForTimeout(800);

    // Clear-all button must now be visible (filter is active)
    await expect(clearBtn).toBeVisible({ timeout: 5000 });

    // Click clear-all
    await clearBtn.click();
    await page.waitForTimeout(800);

    // Clear-all button must disappear (no active filters)
    await expect(clearBtn).not.toBeVisible({ timeout: 5000 });

    // Page must still be on /reports
    expect(page.url()).toContain('/reports');

    // The report list must reappear (filter was cleared, data re-fetched)
    await expect(page.locator('.rrl-list')).toBeVisible({ timeout: 10_000 });
  });

  // ── V08: No hex colors in HfbToolbar inline styles ────────────────────────

  test('C1-1-V08: HfbToolbar inline styles contain no hex colors', async ({ page }) => {
    // Login
    await page.goto('/login');
    await page.waitForSelector('#username', { state: 'visible', timeout: 10_000 });
    await page.fill('#username', 'researcher');
    await page.fill('#password', 'researcher123');
    await page.click('button.login-btn');
    await page.waitForURL((url: URL) => !url.pathname.includes('/login'), { timeout: 15_000 });

    await page.goto('/reports', { waitUntil: 'domcontentloaded' });
    const toolbar = page.locator('[role="search"]');
    await expect(toolbar).toBeVisible({ timeout: 10_000 });

    const styleAttr = await toolbar.getAttribute('style');
    expect(styleAttr || '').not.toContain('#');

    const children = toolbar.locator('> *');
    const count = await children.count();
    for (let i = 0; i < count; i++) {
      const childStyle = await children.nth(i).getAttribute('style');
      expect(childStyle || '').not.toContain('#');
    }
  });

  // ── V09: Pagination renders for multi-page result set ─────────────────────

  test('C1-1-V09: pagination renders when total items > page limit', async ({ page }) => {
    // Login
    await page.goto('/login');
    await page.waitForSelector('#username', { state: 'visible', timeout: 10_000 });
    await page.fill('#username', 'researcher');
    await page.fill('#password', 'researcher123');
    await page.click('button.login-btn');
    await page.waitForURL((url: URL) => !url.pathname.includes('/login'), { timeout: 15_000 });

    await page.goto('/reports', { waitUntil: 'domcontentloaded' });

    // Wait for real data to load
    await expect(page.locator('.rrl-list')).toBeVisible({ timeout: 15_000 });

    // With 43 items and limit=20, there must be 3 pages → pagination renders
    const pagination = page.locator('.rp-pagination');
    await expect(pagination).toBeVisible({ timeout: 5000 });

    // Must show "1 / 3" page info
    const pageInfo = pagination.locator('.rp-page-info');
    await expect(pageInfo).toBeVisible();

    // Previous button must be disabled on page 1
    const prevBtn = pagination.locator('button', { hasText: '上一页' });
    await expect(prevBtn).toBeDisabled();

    // Next button must NOT be disabled (there are more pages)
    const nextBtn = pagination.locator('button', { hasText: '下一页' });
    await expect(nextBtn).not.toBeDisabled();

    // Click next page
    await nextBtn.click();
    await page.waitForTimeout(800);

    // Wait for list to reload
    await expect(page.locator('.rrl-list')).toBeVisible({ timeout: 10_000 });

    // Now page 2 → prev must be enabled, next still enabled
    await expect(prevBtn).not.toBeDisabled();
    await expect(nextBtn).not.toBeDisabled();

    // Page info should show "2 / 3"
    await expect(pageInfo).toContainText('2 / 3');

    // Navigate to last page
    await nextBtn.click();
    await page.waitForTimeout(800);
    await expect(page.locator('.rrl-list')).toBeVisible({ timeout: 10_000 });

    // On last page (3/3), next must be disabled
    await expect(nextBtn).toBeDisabled();
  });

  // ── V10: Report list item renders title, topic, status badges, view link ──

  test('C1-1-V10: report list items render title, topic, badges, and view link', async ({ page }) => {
    // Login
    await page.goto('/login');
    await page.waitForSelector('#username', { state: 'visible', timeout: 10_000 });
    await page.fill('#username', 'researcher');
    await page.fill('#password', 'researcher123');
    await page.click('button.login-btn');
    await page.waitForURL((url: URL) => !url.pathname.includes('/login'), { timeout: 15_000 });

    await page.goto('/reports', { waitUntil: 'domcontentloaded' });

    // Wait for real data to load
    await expect(page.locator('.rrl-list')).toBeVisible({ timeout: 15_000 });

    // At least one list item must be present
    const firstItem = page.locator('.rrli-root').first();
    await expect(firstItem).toBeVisible({ timeout: 5000 });

    // Session title must be present (non-empty)
    const title = firstItem.locator('.rrli-session-title');
    await expect(title).toBeVisible();
    const titleText = await title.textContent();
    expect(titleText?.trim().length || 0).toBeGreaterThan(0);

    // Topic must be present (non-empty)
    const topic = firstItem.locator('.rrli-topic');
    await expect(topic).toBeVisible();
    const topicText = await topic.textContent();
    expect(topicText?.trim().length || 0).toBeGreaterThan(0);

    // Timestamp must be present
    const time = firstItem.locator('.rrli-time');
    await expect(time).toBeVisible();

    // Since all items are ready, the "查看报告" link must be present
    const viewLink = firstItem.locator('.rrli-view-link');
    await expect(viewLink).toBeVisible({ timeout: 3000 });
    await expect(viewLink).toHaveText('查看报告');

    // Export button must be present for ready items
    const exportBtn = firstItem.locator('.rrli-export-btn');
    await expect(exportBtn).toBeVisible();
    await expect(exportBtn).toHaveText('导出');
  });

  // ── V11: Status filter via real browser — select "报告失败" → empty state ─

  test('C1-1-V11: status filter "报告失败" returns empty state then recover via clear-all', async ({ page }) => {
    // Login
    await page.goto('/login');
    await page.waitForSelector('#username', { state: 'visible', timeout: 10_000 });
    await page.fill('#username', 'researcher');
    await page.fill('#password', 'researcher123');
    await page.click('button.login-btn');
    await page.waitForURL((url: URL) => !url.pathname.includes('/login'), { timeout: 15_000 });

    await page.goto('/reports', { waitUntil: 'domcontentloaded' });

    // Real data must load first (43 ready items)
    await expect(page.locator('.rrl-list')).toBeVisible({ timeout: 15_000 });

    // Open filter dropdown and select "报告失败" (status=failed → 0 items)
    const filterTrigger = page.locator('[role="search"] button[aria-expanded]');
    await filterTrigger.click();
    const listbox = page.locator('[role="listbox"]');
    await expect(listbox).toBeVisible({ timeout: 3000 });

    // Click "报告失败" — this triggers a server re-fetch with ?status=failed
    await listbox.locator('[role="option"]', { hasText: '报告失败' }).click();

    // Wait for the server re-fetch to complete
    await page.waitForTimeout(1000);

    // Since DB has 0 items with status=failed, the empty state must appear
    // This is the "filter returned no results" empty state (hasActiveFilters=true).
    const emptyState = page.locator('.empty-state');
    await expect(emptyState).toBeVisible({ timeout: 10_000 });
    await expect(emptyState).toContainText('暂无匹配的报告');

    // The "清除筛选" button inside the empty state must be visible
    const clearFilterBtn = emptyState.locator('.rp-clear-filter-btn');
    await expect(clearFilterBtn).toBeVisible();

    // Click the inline clear button — this calls clearFilters() directly
    await clearFilterBtn.click();
    await page.waitForTimeout(1000);

    // After clearing, the full report list must reappear
    await expect(page.locator('.rrl-list')).toBeVisible({ timeout: 10_000 });
    const count = await page.locator('.rrl-list [role="listitem"]').count();
    expect(count).toBeGreaterThanOrEqual(1);
  });

  // ── V12: Error state → retry recovery ────────────────────────────────────

  test('C1-1-V12: error state renders retry button, retry recovers to data', async ({ page }) => {
    // Login
    await page.goto('/login');
    await page.waitForSelector('#username', { state: 'visible', timeout: 10_000 });
    await page.fill('#username', 'researcher');
    await page.fill('#password', 'researcher123');
    await page.click('button.login-btn');
    await page.waitForURL((url: URL) => !url.pathname.includes('/login'), { timeout: 15_000 });

    // Inject a one-shot 500 error for the reports endpoint.
    // This is controlled fault injection to exercise the error→retry recovery path,
    // NOT data mocking.
    let routeFired = false;
    await page.route('**/api/v4/research/reports*', async (route) => {
      if (!routeFired) {
        routeFired = true;
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Simulated server error for retry test' }),
        });
      } else {
        // Fall through to real backend on retry
        await route.fallback();
      }
    });

    await page.goto('/reports', { waitUntil: 'domcontentloaded' });

    // The error state must appear
    const errorState = page.locator('[role="alert"]');
    await expect(errorState).toBeVisible({ timeout: 15_000 });

    // Error title must be "报告加载失败"
    await expect(errorState.locator('.error-title')).toHaveText('报告加载失败');

    // Error message must contain the injected detail
    await expect(errorState.locator('.error-message')).toHaveText(
      'Simulated server error for retry test',
    );

    // The retry button must be visible
    const retryBtn = errorState.locator('.error-retry-btn');
    await expect(retryBtn).toBeVisible();

    // Remove the route so retry hits the real backend
    await page.unroute('**/api/v4/research/reports*');

    // Click retry — this calls fetchReports() which hits the real backend
    await retryBtn.click();
    await page.waitForTimeout(1000);

    // After retry with real backend, the report list must appear
    await expect(page.locator('.rrl-list')).toBeVisible({ timeout: 15_000 });
    const count = await page.locator('.rrl-list [role="listitem"]').count();
    expect(count).toBeGreaterThanOrEqual(1);

    // Error state must be gone
    await expect(errorState).not.toBeVisible({ timeout: 3000 });
  });

  // ── V13: Anonymous /reports redirects to login ───────────────────────────

  test('C1-1-V13: anonymous /reports redirects to login page', async ({ page, context }) => {
    // Ensure no stored auth state — clear all cookies and localStorage
    await context.clearCookies();

    // Navigate to /reports without authentication
    await page.goto('/reports', { waitUntil: 'domcontentloaded' });

    // The router guard must redirect to /login with a redirect query param
    await page.waitForURL((url: URL) => url.pathname.includes('/login'), { timeout: 10_000 });

    // The redirect query must point back to /reports
    const url = new URL(page.url());
    expect(url.searchParams.get('redirect')).toContain('/reports');

    // Login page must be rendered (username field visible)
    await expect(page.locator('#username')).toBeVisible({ timeout: 5000 });
  });
});
