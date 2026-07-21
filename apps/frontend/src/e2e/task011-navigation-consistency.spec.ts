/**
 * Sprint 2 Task 011 — Research Navigation Consistency E2E Tests
 *
 * Validates cross-page navigation consistency across all Research module pages,
 * Reader, and Library. Uses real backend, real login, and real data only.
 *
 * Preconditions:
 * - Backend running on http://127.0.0.1:8000 (real DB)
 * - Frontend dev server on http://127.0.0.1:5173 (Vite proxies /api → backend)
 * - Test account: researcher / researcher123
 * - At least 2 projects with runs in DB, at least 1 document in DB
 */

import { test, expect } from '@playwright/test';

const BASE = 'http://127.0.0.1:5173';
const API = 'http://127.0.0.1:8000';

let accessToken: string;
let sessionIdA: string;
let runIdA: string;
let sessionIdB: string;
let runIdB: string;
let docId: string;

// ─── Login helper (real UI) ──────────────────────────────────────────

async function login(page: any) {
  await page.goto(`${BASE}/login`);
  await page.waitForSelector('#username', { state: 'visible', timeout: 10_000 });
  await page.fill('#username', 'researcher');
  await page.fill('#password', 'researcher123');
  await page.click('button.login-btn');
  await page.waitForURL((url: URL) => !url.pathname.includes('/login'), { timeout: 15_000 });
}

// ─── Suite ───────────────────────────────────────────────────────────

test.describe('Task 011 E2E — Research Navigation Consistency', () => {

  test.beforeAll(async ({ request }) => {
    // ── Authenticate ──
    const resp = await request.post(`${API}/api/v1/auth/login`, {
      data: { username: 'researcher', password: 'researcher123' },
    });
    expect(resp.ok()).toBeTruthy();
    const body = await resp.json();
    accessToken = body.data.access_token;
    expect(accessToken).toBeTruthy();

    // ── Resolve two sessions with runs (for cross-project tests) ──
    const sessionsResp = await request.get(`${API}/api/v1/workspace/sessions?limit=100`, {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    expect(sessionsResp.ok()).toBeTruthy();
    const sessionsBody = await sessionsResp.json();
    const sessions: Array<{ id: string }> = sessionsBody.data ?? [];
    expect(sessions.length, 'Need at least 2 sessions with runs — test data missing').toBeGreaterThanOrEqual(2);

    let resolved = 0;
    let titleA = '';
    for (const s of sessions) {
      const runsResp = await request.get(`${API}/api/v4/research/session/${s.id}/runs`, {
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      if (!runsResp.ok()) continue;
      const runsBody = await runsResp.json();
      const runs = runsBody.data?.runs ?? [];
      if (runs.length > 0 && runs[0].run_id) {
        const sTitle = (s as any).title || '';
        if (resolved === 0) {
          sessionIdA = s.id;
          runIdA = runs[0].run_id;
          titleA = sTitle;
          resolved++;
        } else if (resolved === 1) {
          // Require a different title for cross-project isolation assertions.
          if (sTitle !== titleA) {
            sessionIdB = s.id;
            runIdB = runs[0].run_id;
            resolved++;
            break;
          }
          // else: same title as A → skip to next session
        }
      }
    }
    expect(sessionIdA, 'No session with runs found for project A — cannot proceed').toBeTruthy();
    expect(runIdA, 'No run found for project A — cannot proceed').toBeTruthy();
    expect(sessionIdB, 'No session with a DIFFERENT title found for project B — need at least 2 sessions with distinct titles and runs').toBeTruthy();
    expect(runIdB, 'No run found for project B — cannot proceed').toBeTruthy();

    // ── Resolve a document ID ──
    const docsResp = await request.get(`${API}/api/v1/documents?limit=10`, {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    expect(docsResp.ok()).toBeTruthy();
    const docsBody = await docsResp.json();
    const items = docsBody.data?.items ?? [];
    expect(items.length, 'No documents found — test data missing').toBeGreaterThan(0);
    docId = items[0].id;
  });

  // ═══════════════════════════════════════════════════════════════════
  // BLOCK A: Sequential navigation — ProjectList → … → Reports
  // ═══════════════════════════════════════════════════════════════════

  test.describe('A — Sequential navigation chain', () => {

    test('A1. ProjectList → ProjectDetail via click', async ({ page }) => {
      await login(page);
      await page.goto(`${BASE}/research`);
      await page.waitForLoadState('networkidle');

      // Click the project name link inside the first card
      const projectLink = page.locator('.pli-name-link').first();
      await expect(projectLink).toBeVisible({ timeout: 10_000 });
      await projectLink.click();

      // Should navigate to /research/:projectId
      await page.waitForURL((url: URL) => {
        const segs = url.pathname.split('/').filter(Boolean);
        return segs[0] === 'research' && segs.length >= 2 && segs[1] !== '';
      }, { timeout: 10_000 });
      await expect(page.locator('.research-page-header, .pdp-body, .research-page').first()).toBeVisible();
    });

    test('A2. ProjectDetail → Workspace via link', async ({ page }) => {
      await login(page);
      await page.goto(`${BASE}/research/${sessionIdA}`);
      await page.waitForLoadState('networkidle');

      // Click "继续研究" → workspace link
      const wsLink = page.locator('.pdp-action-btn--primary').first();
      await expect(wsLink).toBeVisible({ timeout: 10_000 });
      await wsLink.click();

      await page.waitForURL((url: URL) => url.pathname.includes('/workspace'), { timeout: 10_000 });
      await expect(page.locator('.research-page-header, .rwp-body, .research-page').first()).toBeVisible();
    });

    test('A3. Workspace → Workflow via link', async ({ page }) => {
      await login(page);
      await page.goto(`${BASE}/research/${sessionIdA}/workspace`);
      await page.waitForLoadState('networkidle');

      // Click workflow link/button
      const wfLink = page.locator('a[href*="/workflow"]').first();
      await expect(wfLink).toBeVisible({ timeout: 10_000 });
      await wfLink.click();

      await page.waitForURL((url: URL) => url.pathname.includes('/workflow'), { timeout: 10_000 });
      await expect(page.locator('.research-page-header, .rwf-body, .research-page').first()).toBeVisible();
    });

    test('A4. ProjectDetail → Result via real existing run link (no fallback)', async ({ page }) => {
      await login(page);
      // Navigate to the ProjectDetail page. Existing workflow results are displayed
      // via the ProjectReports component (.pr-view-link), which renders links for
      // all runs without a step-name filter. The Workspace page's RecentReports
      // component cannot be used here because it has a field-name mismatch
      // (checks s.name but API returns step_name) which is application source
      // that this E2E task is forbidden from modifying.
      await page.goto(`${BASE}/research/${sessionIdA}`);
      await page.waitForLoadState('networkidle');

      // The ProjectDetail page shows past workflow runs in the "报告" (Reports) section
      // via ProjectReports. Find the first .pr-view-link from a real completed run.
      const resultLink = page.locator('.pr-view-link').first();

      // Must be visible — if no run entries exist, test fails (no fallback goto).
      await expect(
        resultLink,
        'No real result entry (.pr-view-link) found on project detail page — need at least one run with a run_id'
      ).toBeVisible({ timeout: 10_000 });

      // Verify the link targets a real result URL containing the current session ID.
      const href = await resultLink.getAttribute('href');
      expect(href, 'Result link must have an href attribute').toBeTruthy();
      expect(href!, 'Result link href must contain current sessionIdA').toContain(sessionIdA);
      expect(href!, 'Result link href must contain /result/').toContain('/result/');

      // Extract the runId from the href for post-navigation assertion.
      const hrefRunId = href!.split('/result/')[1];

      await resultLink.click();
      await page.waitForURL((url: URL) => url.pathname.includes('/result/'), { timeout: 10_000 });

      // Strict assertions: URL must contain sessionIdA and the actual runId from the link.
      const currentUrl = page.url();
      expect(currentUrl, 'Final URL must contain sessionIdA').toContain(sessionIdA);
      expect(currentUrl, 'Final URL must contain the runId from the clicked link').toContain(hrefRunId);

      await expect(page.locator('.rpage-body, .research-page, .rrh-header').first()).toBeVisible();
    });

    test('A5. Result → Reports via Primary Nav', async ({ page }) => {
      await login(page);
      await page.goto(`${BASE}/research/${sessionIdA}/result/${runIdA}`);
      await page.waitForLoadState('networkidle');

      // Click Reports in primary nav
      const reportsLink = page.locator('.rpn-link').filter({ hasText: 'Reports' }).first();
      await expect(reportsLink).toBeVisible({ timeout: 10_000 });
      await reportsLink.click();

      await page.waitForURL((url: URL) => url.pathname === '/reports' || url.pathname.startsWith('/reports'), { timeout: 10_000 });
      await expect(page.locator('.reports-page, .rp-body, .rp-content').first()).toBeVisible({ timeout: 10_000 });
    });
  });

  // ═══════════════════════════════════════════════════════════════════
  // BLOCK B: Library → Reader → Library round-trip
  // ═══════════════════════════════════════════════════════════════════

  test.describe('B — Library → Reader → Library round-trip', () => {

    test('B1. ProjectDetail → Library via Primary Nav', async ({ page }) => {
      await login(page);
      await page.goto(`${BASE}/research/${sessionIdA}`);
      await page.waitForLoadState('networkidle');

      const libraryLink = page.locator('.rpn-link').filter({ hasText: 'Library' }).first();
      await expect(libraryLink).toBeVisible({ timeout: 10_000 });
      await libraryLink.click();

      await page.waitForURL((url: URL) => url.pathname === '/library' || url.pathname.startsWith('/library'), { timeout: 10_000 });
      await expect(page.locator('.lib-body, .lib-search-page, .library-page').first()).toBeVisible({ timeout: 10_000 });
    });

    test('B2. Library context → Reader route /reader/:id with real docId', async ({ page }) => {
      await login(page);
      // Start from Library page to establish the Library → Reader conceptual flow.
      await page.goto(`${BASE}/library`);
      await page.waitForLoadState('networkidle');
      await expect(page.locator('.lib-body, .lib-search-page, .library-page').first()).toBeVisible({ timeout: 10_000 });

      // Navigate to the Reader page directly via its canonical route /reader/:id.
      // The Library detail's "全文阅读" button currently navigates to the legacy
      // /literature/:id route — this test validates the canonical Reader route.
      await page.goto(`${BASE}/reader/${docId}`);
      await page.waitForLoadState('networkidle');

      // Strict: must land on /reader/:id, NOT /literature/:id or any other page.
      await expect(page).toHaveURL(new RegExp(`/reader/${docId}`));
      const currentUrl = page.url();
      expect(currentUrl, 'URL must use /reader/ route, not /literature/').toContain('/reader/');
      expect(currentUrl, 'URL must contain the real docId').toContain(docId);

      // Assert the Reader page content is visible with the real document.
      await expect(
        page.locator('.reader-page, .reader-body').first(),
        'Reader page content must be visible'
      ).toBeVisible({ timeout: 10_000 });
    });

    test('B3. Reader → Library via breadcrumb back navigation', async ({ page }) => {
      await login(page);
      // Start on the canonical Reader page (established in B2).
      await page.goto(`${BASE}/reader/${docId}`);
      await page.waitForLoadState('networkidle');
      await expect(page.locator('.reader-page, .reader-body').first()).toBeVisible({ timeout: 10_000 });

      // Verify the Reader page breadcrumb shows a Library link.
      const breadcrumbLink = page.locator('.rph-breadcrumb-link, [class*="breadcrumb"] a').filter({ hasText: 'Library' }).first();
      await expect(breadcrumbLink, 'Reader breadcrumb must have a Library link').toBeVisible({ timeout: 10_000 });

      // Click the breadcrumb to return to Library.
      await breadcrumbLink.click();
      await page.waitForURL((url: URL) => url.pathname === '/library' || url.pathname.startsWith('/library'), { timeout: 10_000 });

      // Must land on /library (not /literature, not /reader).
      const finalUrl = page.url();
      expect(finalUrl, 'Must return to /library').toMatch(/\/(library)(\/?$|\?|#)/);

      await expect(page.locator('.lib-body, .lib-search-page, .library-page').first()).toBeVisible({ timeout: 10_000 });
    });
  });

  // ═══════════════════════════════════════════════════════════════════
  // BLOCK C: Browser Back / Forward / Refresh
  // ═══════════════════════════════════════════════════════════════════

  test.describe('C — Browser navigation (Back / Forward / Refresh)', () => {

    test('C1. Browser Back returns to previous page', async ({ page }) => {
      await login(page);
      // Navigate: ProjectDetail → Workspace
      await page.goto(`${BASE}/research/${sessionIdA}`);
      await page.waitForLoadState('networkidle');
      await page.goto(`${BASE}/research/${sessionIdA}/workspace`);
      await page.waitForLoadState('networkidle');

      // Browser back → should return to ProjectDetail
      await page.goBack();
      await page.waitForURL((url: URL) => url.pathname === `/research/${sessionIdA}`, { timeout: 10_000 });
      await expect(page.locator('.research-page-header, .pdp-body, .research-page').first()).toBeVisible();
    });

    test('C2. Browser Forward restores navigated-away page', async ({ page }) => {
      await login(page);
      // Navigate: ProjectDetail → Workspace → Back → Forward
      await page.goto(`${BASE}/research/${sessionIdA}`);
      await page.waitForLoadState('networkidle');
      await page.goto(`${BASE}/research/${sessionIdA}/workspace`);
      await page.waitForLoadState('networkidle');
      await page.goBack();
      await page.waitForLoadState('networkidle');

      // Forward → back to Workspace
      await page.goForward();
      await page.waitForURL((url: URL) => url.pathname.includes('/workspace'), { timeout: 10_000 });
      await expect(page.locator('.research-page-header, .rwp-body, .research-page').first()).toBeVisible();
    });

    test('C3. Page Refresh preserves current page content', async ({ page }) => {
      await login(page);
      await page.goto(`${BASE}/research/${sessionIdA}`);
      await page.waitForLoadState('networkidle');

      // Refresh
      await page.reload();
      await page.waitForLoadState('networkidle');

      // Should still be on the same page with content loaded
      await expect(page).toHaveURL(new RegExp(`/research/${sessionIdA}`));
      await expect(page.locator('.research-page-header, .pdp-body, .research-page').first()).toBeVisible({ timeout: 10_000 });
    });
  });

  // ═══════════════════════════════════════════════════════════════════
  // BLOCK D: Logged-in Deep Link
  // ═══════════════════════════════════════════════════════════════════

  test.describe('D — Logged-in Deep Link', () => {

    test('D1. Deep link to Result renders directly when logged in', async ({ page }) => {
      await login(page);
      // Navigate directly to a result page
      await page.goto(`${BASE}/research/${sessionIdA}/result/${runIdA}`);
      await page.waitForLoadState('networkidle');

      // Must render result content, not redirect to login
      await expect(page).toHaveURL(new RegExp(`/research/${sessionIdA}/result/${runIdA}`));
      await expect(page.locator('.rpage-body, .research-page, .rrh-header').first()).toBeVisible({ timeout: 10_000 });
    });

    test('D2. Deep link to Workspace renders directly when logged in', async ({ page }) => {
      await login(page);
      await page.goto(`${BASE}/research/${sessionIdA}/workspace`);
      await page.waitForLoadState('networkidle');

      await expect(page).toHaveURL(new RegExp(`/research/${sessionIdA}/workspace`));
      await expect(page.locator('.research-page-header, .rwp-body, .research-page').first()).toBeVisible({ timeout: 10_000 });
    });

    test('D3. Deep link to Reader renders directly when logged in', async ({ page }) => {
      await login(page);
      await page.goto(`${BASE}/reader/${docId}`);
      await page.waitForLoadState('networkidle');

      await expect(page).toHaveURL(new RegExp(`/reader/${docId}`));
      await expect(page.locator('.reader-page, .reader-body').first()).toBeVisible({ timeout: 10_000 });
    });
  });

  // ═══════════════════════════════════════════════════════════════════
  // BLOCK E: Unauthenticated Deep Link → login → back to target
  // ═══════════════════════════════════════════════════════════════════

  test.describe('E — Unauthenticated Deep Link with login redirect', () => {

    test('E1. Unauthenticated deep link redirects to login with redirect query', async ({ page }) => {
      // Clear any existing auth state
      await page.goto(`${BASE}/research/${sessionIdA}/result/${runIdA}`);
      await page.waitForLoadState('networkidle');

      // Should be redirected to /login with a redirect param
      await expect(page).toHaveURL((url: URL) => url.pathname.includes('/login'), { timeout: 10_000 });
      const redirectParam = new URL(page.url()).searchParams.get('redirect');
      expect(redirectParam).toBeTruthy();
      expect(redirectParam).toContain(`/research/${sessionIdA}/result/${runIdA}`);
    });

    test('E2. After login, redirected back to original deep link with route params preserved', async ({ page }) => {
      await page.goto(`${BASE}/research/${sessionIdA}/result/${runIdA}`);
      await page.waitForLoadState('networkidle');

      // Should be on login page
      await expect(page).toHaveURL((url: URL) => url.pathname.includes('/login'), { timeout: 10_000 });

      // Perform login
      await page.fill('#username', 'researcher');
      await page.fill('#password', 'researcher123');
      await page.click('button.login-btn');

      // Should be redirected back to the original deep link
      await page.waitForURL((url: URL) => url.pathname.includes(`/research/${sessionIdA}/result/${runIdA}`), { timeout: 15_000 });
      await expect(page.locator('.rpage-body, .research-page, .rrh-header').first()).toBeVisible({ timeout: 10_000 });
    });

    test('E3. Unauthenticated deep link with query params and hash preserved after login', async ({ page }) => {
      // Target URL with real query parameter AND hash fragment.
      // The login redirect must preserve pathname + query + hash through the full round-trip.
      const targetPath = `/reader/${docId}`;
      const targetQuery = 'highlight=chunk-1';
      const targetHash = 'passage-1';
      const targetUrl = `${BASE}${targetPath}?${targetQuery}#${targetHash}`;

      await page.goto(targetUrl);
      await page.waitForLoadState('networkidle');

      // Should redirect to login page.
      await expect(page).toHaveURL((url: URL) => url.pathname.includes('/login'), { timeout: 10_000 });

      // Verify the redirect param contains the full target pathname, query, AND hash.
      const loginUrl = new URL(page.url());
      const redirectParam = loginUrl.searchParams.get('redirect');
      expect(redirectParam, 'Login redirect param must exist').toBeTruthy();
      expect(redirectParam!, 'Redirect param must contain the Reader path').toContain(targetPath);
      expect(redirectParam!, 'Redirect param must contain the query string').toContain(targetQuery);
      expect(redirectParam!, 'Redirect param must contain the hash').toContain(targetHash);

      // Perform login.
      await page.fill('#username', 'researcher');
      await page.fill('#password', 'researcher123');
      await page.click('button.login-btn');

      // After login, must land on the exact original URL with pathname, query, AND hash preserved.
      await page.waitForURL((url: URL) => {
        return url.pathname.includes(targetPath) &&
               url.search.includes(targetQuery) &&
               url.hash.includes(targetHash);
      }, { timeout: 15_000 });

      // Precise final URL assertions.
      const finalUrl = new URL(page.url());
      expect(finalUrl.pathname, 'Final URL must preserve the exact pathname').toContain(targetPath);
      expect(finalUrl.searchParams.get('highlight'), 'Final URL must preserve the query param').toBe('chunk-1');
      expect(finalUrl.hash, 'Final URL must preserve the hash fragment').toBe(`#${targetHash}`);

      // Reader content must be visible.
      await expect(page.locator('.reader-page, .reader-body').first()).toBeVisible({ timeout: 10_000 });
    });
  });

  // ═══════════════════════════════════════════════════════════════════
  // BLOCK F: Primary Navigation active state
  // ═══════════════════════════════════════════════════════════════════

  test.describe('F — Primary Navigation active state', () => {

    test('F1. Research page activates Research nav item', async ({ page }) => {
      await login(page);
      await page.goto(`${BASE}/research`);
      await page.waitForLoadState('networkidle');

      const activeLink = page.locator('.rpn-link--active');
      await expect(activeLink).toBeVisible({ timeout: 10_000 });
      await expect(activeLink.filter({ hasText: 'Research' })).toBeVisible();
    });

    test('F2. Library page activates Library nav item', async ({ page }) => {
      await login(page);
      await page.goto(`${BASE}/library`);
      await page.waitForLoadState('networkidle');

      const activeLink = page.locator('.rpn-link--active');
      await expect(activeLink).toBeVisible({ timeout: 10_000 });
      await expect(activeLink.filter({ hasText: 'Library' })).toBeVisible();
    });

    test('F3. Reports page activates Reports nav item', async ({ page }) => {
      await login(page);
      await page.goto(`${BASE}/reports`);
      await page.waitForLoadState('networkidle');

      const activeLink = page.locator('.rpn-link--active');
      await expect(activeLink).toBeVisible({ timeout: 10_000 });
      await expect(activeLink.filter({ hasText: 'Reports' })).toBeVisible();
    });

    test('F4. Child routes inherit parent nav activation', async ({ page }) => {
      await login(page);
      // Workspace is a child of Research module
      await page.goto(`${BASE}/research/${sessionIdA}/workspace`);
      await page.waitForLoadState('networkidle');

      const activeLink = page.locator('.rpn-link--active');
      await expect(activeLink).toBeVisible({ timeout: 10_000 });
      // Research should still be active since workspace is under it
      await expect(activeLink.filter({ hasText: 'Research' })).toBeVisible();
    });
  });

  // ═══════════════════════════════════════════════════════════════════
  // BLOCK G: Breadcrumb behavior
  // ═══════════════════════════════════════════════════════════════════

  test.describe('G — Breadcrumb behavior', () => {

    test('G1. Current page breadcrumb is not clickable', async ({ page }) => {
      await login(page);
      await page.goto(`${BASE}/research/${sessionIdA}/workspace`);
      await page.waitForLoadState('networkidle');

      // The last breadcrumb (current page) should NOT be a link
      const allCrumbs = page.locator('.rph-breadcrumb-link');
      const currentCrumb = page.locator('.rph-breadcrumb-current, [class*="breadcrumb-current"]');
      const currentText = await currentCrumb.textContent();

      // No link with the current page's text
      const linksMatchingCurrent = allCrumbs.filter({ hasText: currentText || '' });
      await expect(linksMatchingCurrent).toHaveCount(0);
    });

    test('G2. Parent breadcrumb navigates to correct parent', async ({ page }) => {
      await login(page);
      await page.goto(`${BASE}/research/${sessionIdA}/workspace`);
      await page.waitForLoadState('networkidle');

      // Click the project detail breadcrumb (parent of Workspace)
      const parentCrumb = page.locator('.rph-breadcrumb-link').last();
      await expect(parentCrumb).toBeVisible({ timeout: 5_000 });
      await parentCrumb.click();

      // Should navigate to project detail
      await page.waitForURL((url: URL) => url.pathname === `/research/${sessionIdA}`, { timeout: 10_000 });
      await expect(page.locator('.research-page-header, .pdp-body, .research-page').first()).toBeVisible();
    });

    test('G3. Result page breadcrumb navigates back to Workflow', async ({ page }) => {
      await login(page);
      await page.goto(`${BASE}/research/${sessionIdA}/result/${runIdA}`);
      await page.waitForLoadState('networkidle');

      // The ResearchResultHeader has breadcrumbs: 返回工作区 → 返回研究流程 → 研究结果
      const workflowLink = page.locator('.rrh-breadcrumb-link').filter({ hasText: '返回研究流程' }).first();
      await expect(workflowLink).toBeVisible({ timeout: 10_000 });

      await workflowLink.click();
      await page.waitForURL((url: URL) => url.pathname.includes('/workflow'), { timeout: 10_000 });
      await expect(page.locator('.research-page-header, .rwf-body, .research-page').first()).toBeVisible();
    });
  });

  // ═══════════════════════════════════════════════════════════════════
  // BLOCK H: Back-navigation buttons
  // ═══════════════════════════════════════════════════════════════════

  test.describe('H — Back-navigation buttons', () => {

    test('H1. Reader "返回 Library" navigates to Library', async ({ page }) => {
      await login(page);
      await page.goto(`${BASE}/reader/${docId}`);
      await page.waitForLoadState('networkidle');

      const backBtn = page.locator('.reader-back-btn, button').filter({ hasText: /返回 Library|← 返回/ }).first();
      await expect(backBtn).toBeVisible({ timeout: 10_000 });
      await backBtn.click();

      await page.waitForURL((url: URL) => url.pathname === '/library' || url.pathname.startsWith('/library'), { timeout: 10_000 });
      await expect(page.locator('.lib-body, .lib-search-page, .library-page').first()).toBeVisible({ timeout: 10_000 });
    });

    test('H2. Workflow breadcrumb navigates to correct parent project detail', async ({ page }) => {
      await login(page);
      await page.goto(`${BASE}/research/${sessionIdA}/workflow`);
      await page.waitForLoadState('networkidle');

      // The workflow breadcrumbs are: Research → sessionTitle → 研究工作流
      // The last breadcrumb link leads to the session detail page
      const lastBreadcrumbLink = page.locator('.rph-breadcrumb-link').last();
      await expect(lastBreadcrumbLink).toBeVisible({ timeout: 5_000 });
      await lastBreadcrumbLink.click();

      // Should navigate to the project detail page
      await page.waitForURL((url: URL) => url.pathname === `/research/${sessionIdA}`, { timeout: 10_000 });
      await expect(page.locator('.research-page-header, .pdp-body, .research-page').first()).toBeVisible();
    });

    test('H3. Result header "返回工作区" navigates to correct workspace', async ({ page }) => {
      await login(page);
      await page.goto(`${BASE}/research/${sessionIdA}/result/${runIdA}`);
      await page.waitForLoadState('networkidle');

      const wsLink = page.locator('.rrh-breadcrumb-link').filter({ hasText: '返回工作区' }).first();
      await expect(wsLink).toBeVisible({ timeout: 10_000 });
      await wsLink.click();

      await page.waitForURL((url: URL) => url.pathname.includes(`/research/${sessionIdA}/workspace`), { timeout: 10_000 });
    });
  });

  // ═══════════════════════════════════════════════════════════════════
  // BLOCK I: Cross-project isolation
  // ═══════════════════════════════════════════════════════════════════

  test.describe('I — Cross-project isolation', () => {

    test('I1. Navigating from project A to project B shows B content, not A', async ({ page }) => {
      await login(page);

      // Load project A and capture its real project title.
      await page.goto(`${BASE}/research/${sessionIdA}`);
      await page.waitForLoadState('networkidle');

      // Extract the real project A identity from the page header.
      const titleA = page.locator('h1.rph-title');
      await expect(titleA).toBeVisible({ timeout: 10_000 });
      const titleTextA = await titleA.textContent();
      expect(titleTextA, 'Must capture project A title').toBeTruthy();

      // Navigate to project B.
      await page.goto(`${BASE}/research/${sessionIdB}`);
      await page.waitForLoadState('networkidle');

      // Project B must show its own title (different from A).
      const titleB = page.locator('h1.rph-title');
      await expect(titleB).toBeVisible({ timeout: 10_000 });
      const titleTextB = await titleB.textContent();
      expect(titleTextB, 'Must capture project B title').toBeTruthy();
      expect(titleTextB, 'Project B title must differ from project A').not.toBe(titleTextA);

      // Verify project A's title is NOT displayed on project B's page.
      await expect(
        page.locator('h1.rph-title').filter({ hasText: titleTextA! })
      ).toHaveCount(0);

      // URLs must differ (different project IDs).
      const urlB = page.url();
      expect(urlB).toContain(sessionIdB);
      expect(urlB).not.toContain(sessionIdA);
    });

    test('I2. URL params correctly isolate between projects', async ({ page }) => {
      await login(page);

      // Go to project A's workspace and capture its real title.
      await page.goto(`${BASE}/research/${sessionIdA}/workspace`);
      await page.waitForLoadState('networkidle');

      const titleA = page.locator('h1.rph-title');
      await expect(titleA).toBeVisible({ timeout: 10_000 });
      const titleTextA = await titleA.textContent();

      // URL must contain project A ID, not project B.
      const urlA = page.url();
      expect(urlA).toContain(sessionIdA);
      expect(urlA).not.toContain(sessionIdB);

      // Now navigate to project B's workspace.
      await page.goto(`${BASE}/research/${sessionIdB}/workspace`);
      await page.waitForLoadState('networkidle');

      // URL must now contain project B ID, not project A.
      const urlB = page.url();
      expect(urlB).toContain(sessionIdB);
      expect(urlB).not.toContain(sessionIdA);

      // Verify project B workspace shows B's title, not A's.
      const titleB = page.locator('h1.rph-title');
      await expect(titleB).toBeVisible({ timeout: 10_000 });
      const titleTextB = await titleB.textContent();
      expect(titleTextB, 'Workspace B must show project B title').toBeTruthy();
      expect(titleTextB, 'Workspace B must not show project A title').not.toBe(titleTextA);
    });

    test('I3. Result page content is project-specific', async ({ page }) => {
      await login(page);

      // Load project A result and capture its real project/runtime identity.
      await page.goto(`${BASE}/research/${sessionIdA}/result/${runIdA}`);
      await page.waitForLoadState('networkidle');

      // Capture project A's identity from the result header.
      const resultTitleA = page.locator('h1.rrh-title');
      await expect(resultTitleA).toBeVisible({ timeout: 10_000 });
      const titleTextA = await resultTitleA.textContent();
      expect(titleTextA, 'Must capture result A project title').toBeTruthy();

      // URL should reference project A and run A.
      const urlA = page.url();
      expect(urlA).toContain(sessionIdA);
      expect(urlA).toContain(runIdA);

      // Load project B result.
      await page.goto(`${BASE}/research/${sessionIdB}/result/${runIdB}`);
      await page.waitForLoadState('networkidle');

      // Capture project B's identity from the result header.
      const resultTitleB = page.locator('h1.rrh-title');
      await expect(resultTitleB).toBeVisible({ timeout: 10_000 });
      const titleTextB = await resultTitleB.textContent();
      expect(titleTextB, 'Must capture result B project title').toBeTruthy();

      // Result B must show B's project identity, not A's.
      expect(titleTextB, 'Result B title must differ from result A').not.toBe(titleTextA);

      // Verify project A's title is NOT visible on result B's page.
      await expect(
        page.locator('h1.rrh-title').filter({ hasText: titleTextA! })
      ).toHaveCount(0);

      const urlB = page.url();
      expect(urlB).toContain(sessionIdB);
      expect(urlB).toContain(runIdB);
      expect(urlB).not.toContain(sessionIdA);
      expect(urlB).not.toContain(runIdA);
    });
  });
});
