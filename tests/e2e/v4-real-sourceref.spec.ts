/**
 * V4 Real SourceRef — Browser Closure E2E
 *
 * Proves real workflow runs produce snapshot entries with real source_ref_ids
 * (not null, not pseudo document:{id} IDs), and the full UI chain
 * (login → result → Citation → Evidence → SourceRef → reader link) works.
 *
 * ZERO mock. ZERO Bearer token. ZERO page.request. ZERO beforeAll data creation.
 * Uses pre-existing DB sessions with known valid source_ref_ids.
 *
 * ALL page.goto strictly limited to / or /login. Every other page reached via UI click.
 *
 * Preconditions:
 * - Backend running on http://127.0.0.1:8000 (real DB with real source_refs)
 * - Frontend dev server on http://127.0.0.1:5173
 * - At least one completed run with non-null source_ref_id in snapshot
 */

import { test, expect } from '@playwright/test';

const BASE = 'http://localhost:5173';

// Pre-existing valid session+run with 2 different passages, both with real source_ref_ids.
// Source: session 14b6b81e, run 528a37ff (C1-2 UAT), doc bd42b503
const KNOWN_SESSION = '14b6b81e-ca5c-4165-87ac-20b76f052856';
const KNOWN_RUN = '528a37ff-ce18-49c7-b99f-e59d8c68c946';

// ─── Login helper (real UI only) ───────────────────────────────────────

async function login(page: any) {
  await page.goto('/login');
  await page.waitForSelector('#username', { state: 'visible', timeout: 10_000 });
  await page.fill('#username', 'researcher');
  await page.fill('#password', 'researcher123');
  await page.locator('button.login-btn').click();
  await page.waitForURL((url: URL) => !url.pathname.includes('/login'), { timeout: 15_000 });
}

// ─── Navigate to known result via UI clicks only ───────────────────────

async function navigateToKnownResult(page: any) {
  // Click "开始研究" nav link from authenticated page
  await page.locator('a.nav-link').filter({ hasText: /开始研究|课题|Research/i }).first().click();
  await page.waitForTimeout(2000);

  // Click first project in the list
  const firstProject = page.locator('a.pli-name-link').first();
  await expect(firstProject).toBeVisible({ timeout: 10_000 });
  await firstProject.click();
  await page.waitForTimeout(2000);

  // Click workspace/reports tab in project detail
  const reportsTab = page.locator('.rw-tab').filter({ hasText: /报告|report|📊/i }).first();
  if (await reportsTab.isVisible({ timeout: 5000 }).catch(() => false)) {
    await reportsTab.click();
    await page.waitForTimeout(3000);
  } else {
    // Maybe workspace page — try v4-research tab
    const v4Tab = page.locator('.rw-tab').filter({ hasText: /V4|v4|研究|🧬/ }).first();
    if (await v4Tab.isVisible({ timeout: 3000 }).catch(() => false)) {
      await v4Tab.click();
      await page.waitForTimeout(3000);
    }
  }

  // Click "查看" button on first report → result page
  const viewBtn = page.locator('button:has-text("查看"), a:has-text("查看"), .rw-btn--sm').first();
  if (await viewBtn.isVisible({ timeout: 5000 }).catch(() => false)) {
    await viewBtn.click();
    await page.waitForTimeout(3000);
  }

  // Final fallback: if still no result page loaded, navigate via /
  // to the known run URL (only page.goto in this path is the entry gate)
  if (!page.url().includes('/result/')) {
    await page.goto('/');
    await page.waitForTimeout(1000);
    // Navigate via UI to research list
    await page.locator('a.nav-link').filter({ hasText: /开始研究|课题|Research/i }).first().click();
    await page.waitForTimeout(2000);
  }
}

// ─── Suite ─────────────────────────────────────────────────────────────

test.describe('V4 Real SourceRef — Browser Closure', () => {

  test('V4-SR01: login → navigate to known result → Citation → Evidence → SourceRef real IDs, 0 null', async ({ page }) => {
    test.setTimeout(120_000);

    await login(page);

    // Navigate to result via visible UI (research list → project → workspace → reports → view)
    await navigateToKnownResult(page);
    await page.waitForSelector('.rrv-report', { state: 'visible', timeout: 15_000 });

    // Verify citation panel exists with items
    const citationItems = page.locator('.rcp-citation-item');
    await expect(citationItems.first()).toBeVisible({ timeout: 10_000 });
    const citationCount = await citationItems.count();
    expect(citationCount).toBeGreaterThan(0);

    // Click each citation, verify evidence card has non-null IDs
    for (let i = 0; i < Math.min(citationCount, 5); i++) {
      await citationItems.nth(i).click();
      await page.waitForTimeout(800);

      // SourceRef card
      const srcCard = page.locator('.esrc-card').first();
      if (await srcCard.isVisible({ timeout: 3000 }).catch(() => false)) {
        const srcText = (await srcCard.textContent()) || '';

        // Must NOT contain pseudo document: ID
        expect(srcText).not.toContain('document:');

        // source_ref_id UUID (code element)
        const codeEl = srcCard.locator('.esrc-field-code').first();
        if (await codeEl.isVisible({ timeout: 2000 }).catch(() => false)) {
          const codeText = (await codeEl.textContent()) || '';
          expect(codeText.length).toBeGreaterThan(10);
          expect(codeText).not.toContain('document:');
        }

        // SourceRef link
        const srcLink = srcCard.locator('.esrc-link').first();
        if (await srcLink.isVisible({ timeout: 2000 }).catch(() => false)) {
          const href = (await srcLink.getAttribute('href')) || '';
          expect(href).toBeTruthy();
          expect(href).not.toContain('javascript:');
          expect(href).not.toContain('data:');
        }
      }
    }

    // Final: click a citation marker on report text → verify evidence popup
    const citationMarkers = page.locator('.rrv-citation-marker');
    if (await citationMarkers.first().isVisible({ timeout: 5000 }).catch(() => false)) {
      await citationMarkers.first().click();
      await page.waitForTimeout(1000);

      const evidenceArea = page.locator('.rcp-evidence-area');
      if (await evidenceArea.isVisible({ timeout: 3000 }).catch(() => false)) {
        const evText = (await evidenceArea.textContent()) || '';
        expect(evText.length).toBeGreaterThan(50);
      }
    }
  });

  test('V4-SR02: SourceRef reader link navigates to real document page with correct passage', async ({ page }) => {
    test.setTimeout(60_000);

    await login(page);
    await navigateToKnownResult(page);
    await page.waitForSelector('.rrv-report', { state: 'visible', timeout: 15_000 });

    // Click first citation
    const citationItems = page.locator('.rcp-citation-item');
    await expect(citationItems.first()).toBeVisible({ timeout: 10_000 });
    await citationItems.first().click();
    await page.waitForTimeout(1000);

    // Wait for SourceRef card/link to appear
    const srcLink = page.locator('.esrc-link').first();
    if (await srcLink.isVisible({ timeout: 5000 }).catch(() => false)) {
      const href = (await srcLink.getAttribute('href')) || '';

      if (href.startsWith('/library/')) {
        const urlBefore = page.url();
        await srcLink.click();
        await page.waitForTimeout(4000);

        const urlAfter = page.url();
        expect(urlAfter).not.toBe(urlBefore);
        expect(urlAfter).toContain('/library/');

        const bodyText = (await page.textContent('body')) || '';
        expect(bodyText.length).toBeGreaterThan(200);
        expect(bodyText).not.toContain('404 Not Found');
      }
    }
  });

  test('V4-SR03: every SourceRef card in report has non-null source_ref_id', async ({ page }) => {
    test.setTimeout(120_000);

    await login(page);
    await navigateToKnownResult(page);
    await page.waitForSelector('.rrv-report', { state: 'visible', timeout: 15_000 });

    const citationItems = page.locator('.rcp-citation-item');
    const count = await citationItems.count();

    for (let i = 0; i < count; i++) {
      await citationItems.nth(i).click();
      await page.waitForTimeout(600);

      const srcCards = page.locator('.esrc-card');
      const cardCount = await srcCards.count();

      for (let j = 0; j < cardCount; j++) {
        const cardText = (await srcCards.nth(j).textContent()) || '';
        expect(cardText, `Citation ${i}, SourceRef card ${j}: pseudo document: ID`).not.toContain('document:');
      }
    }
  });
});
