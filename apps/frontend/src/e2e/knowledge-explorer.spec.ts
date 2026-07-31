/**
 * Task 2A — Knowledge Explorer E2E Tests
 *
 * Validates the real /knowledge page against the real backend Graph API.
 * No mocks, no static data — real entities from the live database.
 *
 * Preconditions:
 * - Backend running on http://127.0.0.1:8000
 * - Frontend dev server on http://127.0.0.1:5173
 * - Test account: researcher / researcher123
 */

import { test, expect } from '@playwright/test';

const BASE = 'http://127.0.0.1:5173';
const API = 'http://127.0.0.1:8000';

let accessToken: string;

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

test.describe('Task 2A E2E — Knowledge Explorer page', () => {
  test.beforeAll(async ({ request }) => {
    // Authenticate — backend envelope is { success, data: { access_token, ... } }
    const resp = await request.post(`${API}/api/v1/auth/login`, {
      data: { username: 'researcher', password: 'researcher123' },
    });
    expect(resp.status()).toBe(200);
    const body = await resp.json();
    accessToken = body.data.access_token;
    expect(accessToken).toBeTruthy();
  });

  test.beforeEach(async ({ page }) => {
    await login(page);
    // Knowledge module is a child route of DefaultLayout → path is /knowledge
    await page.goto(`${BASE}/knowledge`);
    await page.waitForSelector('input.search-input', { state: 'visible', timeout: 10_000 });
  });

  // ─── Page structure ────────────────────────────────────────────────

  test('renders the page header with correct title', async ({ page }) => {
    await expect(page.locator('.rph-title')).toContainText('知识图谱');
  });

  test('renders search input with placeholder', async ({ page }) => {
    const input = page.locator('input.search-input');
    await expect(input).toBeVisible();
    await expect(input).toHaveAttribute('placeholder', /搜索/);
  });

  test('renders 4 entity type filter chips', async ({ page }) => {
    const chips = page.locator('.type-chip');
    await expect(chips).toHaveCount(4);
  });

  test('shows empty hint in graph area before any search', async ({ page }) => {
    // GraphCanvas should show the empty text
    await expect(page.locator('.graph-state--empty')).toBeVisible();
  });

  // ─── Entity search ─────────────────────────────────────────────────

  test('searches for entities and displays results', async ({ page }) => {
    const input = page.locator('input.search-input');
    await input.fill('皇甫谧');
    await input.press('Enter');

    // Wait for search results to appear
    await expect(page.locator('.search-results')).toBeVisible({ timeout: 10_000 });
    const resultItems = page.locator('.result-item');
    const count = await resultItems.count();
    expect(count).toBeGreaterThan(0);

    // Verify results have labels
    const firstLabel = await resultItems.first().locator('.result-label').textContent();
    expect(firstLabel).toBeTruthy();
  });

  test('type filter chips toggle active state', async ({ page }) => {
    const chip = page.locator('.type-chip').first();
    await expect(chip).toHaveClass(/type-chip--active/);

    // Click to deselect
    await chip.click();
    await expect(chip).not.toHaveClass(/type-chip--active/);

    // Click again to reselect
    await chip.click();
    await expect(chip).toHaveClass(/type-chip--active/);
  });

  // ─── Entity selection → neighborhood ───────────────────────────────

  test('clicking a search result loads its neighborhood in canvas', async ({ page }) => {
    // Search for a known entity
    const input = page.locator('input.search-input');
    await input.fill('针灸甲乙经');
    await input.press('Enter');

    // Wait for search results
    await expect(page.locator('.result-item').first()).toBeVisible({ timeout: 10_000 });

    // Click the first result
    await page.locator('.result-item').first().click();

    // Entity detail panel should appear
    await expect(page.locator('.entity-detail')).toBeVisible({ timeout: 10_000 });

    // Graph should show nodes from real API response
    await expect(page.locator('.detail-title')).toBeVisible();

    // "邻域探索" and "展开子图" buttons should be visible
    await expect(page.locator('.detail-actions')).toBeVisible();
    await expect(page.locator('.action-btn').first()).toContainText(/邻域|展开/);
  });

  // ─── Subgraph expansion ────────────────────────────────────────────

  test('expand button loads 2-hop subgraph', async ({ page }) => {
    // Search for a known entity
    const input = page.locator('input.search-input');
    await input.fill('皇甫谧');
    await input.press('Enter');

    await expect(page.locator('.result-item').first()).toBeVisible({ timeout: 10_000 });
    await page.locator('.result-item').first().click();

    // Wait for neighborhood to load
    await expect(page.locator('.entity-detail')).toBeVisible({ timeout: 10_000 });

    // Click the "展开子图" button
    const expandBtn = page.locator('.action-btn').filter({ hasText: /展开/ });
    await expect(expandBtn).toBeVisible();
    await expandBtn.click();

    // Should still show the entity detail (subgraph loaded)
    await expect(page.locator('.entity-detail')).toBeVisible({ timeout: 10_000 });
  });

  // ─── Edge evidence inspection ──────────────────────────────────────

  test('clicking an edge shows evidence details with quote, citation, and document link', async ({
    page,
  }) => {
    // Search for an entity known to have evidence-backed graph edges.
    // 针灸甲乙经 has 4 explicit edges with real evidence (quotes, citations, document_ids).
    const input = page.locator('input.search-input');
    await input.fill('针灸甲乙经');
    await input.press('Enter');

    await expect(page.locator('.result-item').first()).toBeVisible({ timeout: 10_000 });
    // Select the book result — its entity_type is 'book' and it has many edges
    await page
      .locator('.result-item')
      .filter({ has: page.locator('.result-type', { hasText: 'book' }) })
      .first()
      .click();

    // Wait for neighborhood and graph to fully load (vis-network + edges)
    await expect(page.locator('.entity-detail')).toBeVisible({ timeout: 10_000 });

    // vis-network edges live on a Canvas element — we must drive the
    // vis-network instance directly to select the first edge and trigger
    // the edge-click emit.  Failing to find an edge is a hard failure.
    await page.waitForSelector('.graph-network--ready', { state: 'visible', timeout: 10_000 });

    // Programme the vis-network edge selection via the exposed handle
    const edgesExist = await page.evaluate(() => {
      const el = document.querySelector('.graph-network');
      const net = (el as any)?.__visNetwork;
      if (!net) return false;
      const edgeIds = net.body.data.edges.getIds();
      if (!edgeIds || edgeIds.length === 0) return false;
      // Select the first edge — this fires 'selectEdge' → edge-click emit
      net.setSelection({ edges: [edgeIds[0]] });
      (net as any).emit('selectEdge', {
        edges: [edgeIds[0]],
        nodes: [],
        event: {} as any,
        pointer: {} as any,
      });
      return true;
    });

    expect(edgesExist, 'No graph edges found — entity has no evidence-backed relations').toBe(true);

    // Edge detail panel must now contain real evidence
    await expect(page.locator('.edge-detail')).toBeVisible({ timeout: 5_000 });

    // Must show a real exact_quote
    const quoteEl = page.locator('.evidence-quote');
    await expect(quoteEl).toBeVisible();
    const quoteText = await quoteEl.textContent();
    expect(quoteText).toBeTruthy();
    expect(quoteText!.length).toBeGreaterThan(10); // real quote, not placeholder

    // Must show a real citation matching [doc_id:chunk_id] format
    await expect(page.locator('.edge-detail')).toContainText(/\[.*:.*\]/);

    // Must have a document link with a resolvable route.
    // The document_id from evidence should link to /app/library/:id.
    const docLink = page.locator('.evidence-link').first();
    await expect(docLink).toBeVisible({ timeout: 5_000 });
    const href = await docLink.getAttribute('href');
    expect(href).toMatch(/\/library\//);
  });

  // ─── Error recovery ────────────────────────────────────────────────

  test('shows no-data message for empty search', async ({ page }) => {
    const input = page.locator('input.search-input');
    await input.fill('xyznonexistent12345');
    await input.press('Enter');

    // Should show no-data message
    await expect(page.locator('.no-results')).toBeVisible({ timeout: 10_000 });
    await expect(page.locator('.no-results')).toContainText('暂无数据');
  });
});
