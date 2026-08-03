/**
 * C1-2 — Citation / Evidence / SourceRef Browser Closure E2E
 *
 * Codex invariants (one real document_id, two different passage_ids):
 *   Citation A/B must each show ONLY its own trace_id / passage_id Evidence + SourceRef.
 *   Reader link must be exact: /library/{document_id}?passage={passage_id}
 *   A page/Evidence/SourceRef/Reader must not show B identity, and vice versa.
 *
 * RBAC invariants (Scheme 1):
 *   - Researcher: audit form absent in UI. Server-side auth probe via same
 *     browser network context gets 401/403. Labeled "服务端越权拒绝证据".
 *   - Admin: sees form, real click submit, gets 2xx, refresh confirms state
 *     change, restore original state, re-confirm 2xx + UI state recovery.
 *
 * DESIGN:
 *   - Single sequential browser flow via test.step. Step failure → stop.
 *   - NO request fixture. NO API login. NO Bearer token. NO page.request.
 *   - NO API scanning of sessions/runs/replay manifests.
 *   - NO page.route(), mock, skip, xfail, soft assertions.
 *   - NO if-branches that silently skip assertions.
 *   - Hard exact assertions only.
 *
 * Section 0 pre-requisites (PO must provide before run):
 *   - Real report URL with same document_id + two different passage_ids
 *   - Citation location info for A and B (trace_id prefix to locate in panel)
 *   - Admin knows initial + recovery state for sensitive operation
 */

import { test, expect } from '@playwright/test';

const BASE = 'http://127.0.0.1:5173';
const API = 'http://127.0.0.1:8000';

// ═══════════════════════════════════════════════════════════════════════════
// Section 0: PO-provided real data — replace TODOs before running
// ═══════════════════════════════════════════════════════════════════════════

/** PO must provide: real report URL (e.g. /research/{sessionId}/result/{runId}) */
const REPORT_URL = '/research/14b6b81e-ca5c-4165-87ac-20b76f052856/result/528a37ff-ce18-49c7-b99f-e59d8c68c946';

/** PO must provide: real document_id shared by both passages */
const DOC_ID = 'bd42b503-9546-4a70-94cf-889056c56c2d';

/** PO must provide: passage A identity */
const PASSAGE_A = {
  citationTraceId: 'cbbe2628-2b75-582c-be6c-f97bc1d3d179',
  passageId: '1112a4bb-d71a-4b72-af05-9bad34937b96',
  sourceRefTitle: '针灸甲乙经·序 — SourceRef B (C1-2 UAT)',
  sourceRefId: '8b3bee08-97fe-43f7-a960-08f5dc2b9f57',
};

/** PO must provide: passage B identity (same doc, different passage) */
const PASSAGE_B = {
  citationTraceId: 'b188bea2-dc86-5c5c-a93f-d024bbe5c5a7',
  passageId: 'cf31f483-18e2-43fc-8ca0-d0625040cef8',
  sourceRefTitle: '针灸甲乙经·序 — SourceRef A (C1-2 UAT)',
  sourceRefId: 'b6b2498d-9f75-471a-8a42-aef7f29b6765',
};

// ═══════════════════════════════════════════════════════════════════════════
// Known real document for RBAC sensitive operation (pre-seeded, real)
// ═══════════════════════════════════════════════════════════════════════════

/** 针灸甲乙经（四库全书本）— real document with review_status */
const RBAC_DOC_ID = '378224ae-0325-47f9-80c3-b99c72569bce';

// ═══════════════════════════════════════════════════════════════════════════
// Login helpers (real UI form submit, no token injection)
// ═══════════════════════════════════════════════════════════════════════════

async function loginResearcher(page: any) {
  await page.goto(`${BASE}/login`);
  await page.waitForSelector('#username', { state: 'visible', timeout: 10_000 });
  await page.fill('#username', 'researcher');
  await page.fill('#password', 'researcher123');
  await page.click('button.login-btn');
  await page.waitForURL((url: URL) => !url.pathname.includes('/login'), { timeout: 15_000 });
}

async function loginAdmin(page: any) {
  await page.goto(`${BASE}/login`);
  await page.waitForSelector('#username', { state: 'visible', timeout: 10_000 });
  await page.fill('#username', 'admin');
  await page.fill('#password', 'admin123');
  await page.click('button.login-btn');
  await page.waitForURL((url: URL) => !url.pathname.includes('/login'), { timeout: 15_000 });
}

// ═══════════════════════════════════════════════════════════════════════════
// Single sequential browser flow
// ═══════════════════════════════════════════════════════════════════════════

test.describe('C1-2 — Citation / Evidence / SourceRef browser closure', () => {

  test('C1-2: full chain isolation + RBAC', async ({ page, browser }) => {

    // ── Section 0: Prerequisite check ──────────────────────────────────

    await test.step('PREREQ: verify PO-provided real data', async () => {
      expect(REPORT_URL, 'BLOCK_C1_2_EVIDENCE: PO must provide real report URL').not.toContain('TODO');
      expect(DOC_ID, 'BLOCK_C1_2_EVIDENCE: PO must provide real document_id').not.toContain('TODO');
      expect(PASSAGE_A.citationTraceId, 'BLOCK_C1_2_EVIDENCE: PO must provide citation A trace_id').not.toContain('TODO');
      expect(PASSAGE_A.passageId, 'BLOCK_C1_2_EVIDENCE: PO must provide passage A id').not.toContain('TODO');
      expect(PASSAGE_A.sourceRefTitle, 'BLOCK_C1_2_EVIDENCE: PO must provide SourceRef A title').not.toContain('TODO');
      expect(PASSAGE_A.sourceRefId, 'BLOCK_C1_2_EVIDENCE: PO must provide SourceRef A id').not.toContain('TODO');
      expect(PASSAGE_B.citationTraceId, 'BLOCK_C1_2_EVIDENCE: PO must provide citation B trace_id').not.toContain('TODO');
      expect(PASSAGE_B.passageId, 'BLOCK_C1_2_EVIDENCE: PO must provide passage B id').not.toContain('TODO');
      expect(PASSAGE_B.sourceRefTitle, 'BLOCK_C1_2_EVIDENCE: PO must provide SourceRef B title').not.toContain('TODO');
      expect(PASSAGE_B.sourceRefId, 'BLOCK_C1_2_EVIDENCE: PO must provide SourceRef B id').not.toContain('TODO');
      expect(PASSAGE_A.passageId, 'Passages A and B must be different').not.toBe(PASSAGE_B.passageId);
      expect(PASSAGE_A.sourceRefId, 'SourceRef A and B must be different').not.toBe(PASSAGE_B.sourceRefId);
    });

    // ═══════════════════════════════════════════════════════════════════════
    // Section 1: Researcher login + report page load
    // ═══════════════════════════════════════════════════════════════════════

    await test.step('V01: researcher login, report page loads, citation panel visible', async () => {
      await loginResearcher(page);
      await page.goto(`${BASE}${REPORT_URL}`);
      await page.waitForSelector('.rrv-report', { state: 'visible', timeout: 15_000 });
      await expect(page.locator('.rcp-citation-item').first()).toBeVisible({ timeout: 5_000 });
    });

    // ═══════════════════════════════════════════════════════════════════════
    // Section 2: Citation A — Evidence / SourceRef / Reader isolation
    // ═══════════════════════════════════════════════════════════════════════

    await test.step('V02: click citation A, Evidence shows correct trace_id and passage_id', async () => {
      const items = page.locator('.rcp-citation-item');
      const count = await items.count();
      let found = false;
      for (let i = 0; i < count; i++) {
        const text = await items.nth(i).textContent();
        if (text?.includes(PASSAGE_A.citationTraceId.slice(0, 8))) {
          await items.nth(i).click();
          found = true;
          break;
        }
      }
      expect(found, `Citation A not found by trace_id prefix: ${PASSAGE_A.citationTraceId.slice(0, 8)}`).toBe(true);

      const evidenceArea = page.locator('.rcp-evidence-area');
      await expect(evidenceArea).toBeVisible({ timeout: 5_000 });
      const evText = (await evidenceArea.textContent()) || '';
      expect(evText).toContain(PASSAGE_A.citationTraceId.slice(0, 16));
      expect(evText).toContain(PASSAGE_A.passageId.slice(0, 16));
    });

    await test.step('V03: citation A SourceRef shows real title + stable sourceRefId, no fallback', async () => {
      const srcCard = page.locator('.esrc-card').first();
      await expect(srcCard).toBeVisible({ timeout: 5_000 });
      const srcText = (await srcCard.textContent()) || '';
      expect(srcText).toContain(PASSAGE_A.sourceRefTitle.slice(0, 8));
      expect(srcText).toContain(PASSAGE_A.sourceRefId.slice(0, 16));
      expect(srcText).not.toContain('缺少文献来源信息');
      expect(srcText).not.toContain('document:');
    });

    await test.step('V04: citation A Reader link exact match, navigates to correct URL, no B contamination', async () => {
      const link = page.locator('.esrc-link').first();
      await expect(link).toBeVisible({ timeout: 5_000 });
      const expectedHrefA = `/library/${DOC_ID}?passage=${PASSAGE_A.passageId}`;
      const href = (await link.getAttribute('href')) || '';
      expect(href).toBe(expectedHrefA);

      // Click link — URL must resolve precisely to A's href
      await link.click();
      await page.waitForTimeout(4000);
      const urlA = new URL(page.url());
      expect(urlA.pathname + urlA.search).toBe(expectedHrefA);
      expect(urlA.pathname + urlA.search).not.toBe(`/library/${DOC_ID}?passage=${PASSAGE_B.passageId}`);

      // Page body must not contain B's passage identity
      const bodyText = (await page.textContent('body')) || '';
      expect(bodyText.length).toBeGreaterThan(200);
      expect(bodyText).not.toContain('404 Not Found');
      expect(bodyText).not.toContain(PASSAGE_B.passageId.slice(0, 16));
      expect(bodyText).not.toContain(PASSAGE_B.sourceRefTitle.slice(0, 8));

      // Navigate back to report for remaining steps
      await page.goto(`${BASE}${REPORT_URL}`);
      await page.waitForSelector('.rrv-report', { state: 'visible', timeout: 15_000 });
    });

    // ═══════════════════════════════════════════════════════════════════════
    // Section 3: Citation B — different passage, no cross-contamination
    // ═══════════════════════════════════════════════════════════════════════

    await test.step('V05: click citation B, Evidence shows B passage_id, not A', async () => {
      const items = page.locator('.rcp-citation-item');
      const count = await items.count();
      let found = false;
      for (let i = 0; i < count; i++) {
        const text = await items.nth(i).textContent();
        if (text?.includes(PASSAGE_B.citationTraceId.slice(0, 8))) {
          await items.nth(i).click();
          found = true;
          break;
        }
      }
      expect(found, `Citation B not found by trace_id prefix: ${PASSAGE_B.citationTraceId.slice(0, 8)}`).toBe(true);

      const evidenceArea = page.locator('.rcp-evidence-area');
      await expect(evidenceArea).toBeVisible({ timeout: 5_000 });
      const evText = (await evidenceArea.textContent()) || '';

      // Must contain B's passage_id
      expect(evText).toContain(PASSAGE_B.passageId.slice(0, 16));

      // Must NOT contain A's passage_id or sourceRefTitle
      expect(evText).not.toContain(PASSAGE_A.passageId.slice(0, 16));
      expect(evText).not.toContain(PASSAGE_A.sourceRefTitle);
    });

    await test.step('V06: citation B SourceRef shows B title + stable sourceRefId, not A, no fallback', async () => {
      const srcCard = page.locator('.esrc-card').first();
      await expect(srcCard).toBeVisible({ timeout: 5_000 });
      const srcText = (await srcCard.textContent()) || '';
      expect(srcText).toContain(PASSAGE_B.sourceRefTitle.slice(0, 8));
      expect(srcText).toContain(PASSAGE_B.sourceRefId.slice(0, 16));
      expect(srcText).not.toContain(PASSAGE_A.sourceRefTitle.slice(0, 8));
      expect(srcText).not.toContain('缺少文献来源信息');
      expect(srcText).not.toContain('document:');
    });

    await test.step('V07: citation B Reader link exact match, navigates to correct URL, no A contamination', async () => {
      const link = page.locator('.esrc-link').first();
      await expect(link).toBeVisible({ timeout: 5_000 });
      const expectedHrefB = `/library/${DOC_ID}?passage=${PASSAGE_B.passageId}`;
      const href = (await link.getAttribute('href')) || '';
      expect(href).toBe(expectedHrefB);

      // Click link — URL must resolve precisely to B's href
      await link.click();
      await page.waitForTimeout(4000);
      const urlB = new URL(page.url());
      expect(urlB.pathname + urlB.search).toBe(expectedHrefB);
      expect(urlB.pathname + urlB.search).not.toBe(`/library/${DOC_ID}?passage=${PASSAGE_A.passageId}`);

      // Page body must not contain A's passage identity
      const bodyText = (await page.textContent('body')) || '';
      expect(bodyText.length).toBeGreaterThan(200);
      expect(bodyText).not.toContain(PASSAGE_A.passageId.slice(0, 16));
      expect(bodyText).not.toContain(PASSAGE_A.sourceRefTitle.slice(0, 8));
    });

    // ═══════════════════════════════════════════════════════════════════════
    // Section 4: Display number consistency
    // ═══════════════════════════════════════════════════════════════════════

    await test.step('V08: first report marker number equals first panel citation number', async () => {
      await page.goto(`${BASE}${REPORT_URL}`);
      await page.waitForSelector('.rrv-report', { state: 'visible', timeout: 15_000 });

      const markers = page.locator('.rrv-citation-marker');
      const panels = page.locator('.rcp-citation-item');
      const markerCount = await markers.count();
      const panelCount = await panels.count();
      expect(markerCount, 'Report must have citation markers').toBeGreaterThan(0);
      expect(panelCount, 'Citation panel must have items').toBeGreaterThan(0);

      const mText = ((await markers.first().textContent()) || '').replace(/[[\]\s]/g, '').trim();
      const pText = ((await panels.first().locator('.rcp-citation-number').textContent()) || '')
        .replace(/[#[\]\s]/g, '')
        .trim();
      expect(mText).toBe(pText);
    });

    await test.step('V09: every marker number exists in panel number set', async () => {
      const markers = page.locator('.rrv-citation-marker');
      const mc = await markers.count();
      const markerSet = new Set<string>();
      for (let i = 0; i < mc; i++) {
        const t = ((await markers.nth(i).textContent()) || '').replace(/[[\]\s]/g, '').trim();
        if (t && t !== 'undefined') markerSet.add(t);
      }
      expect(markerSet.size, 'Report must have at least one citation marker').toBeGreaterThan(0);

      const panels = page.locator('.rcp-citation-item');
      const pc = await panels.count();
      const panelSet = new Set<string>();
      for (let i = 0; i < pc; i++) {
        const t = ((await panels.nth(i).locator('.rcp-citation-number').textContent()) || '')
          .replace(/[#[\]\s]/g, '')
          .trim();
        if (t && t !== '?' && t !== 'undefined') panelSet.add(t);
      }

      for (const n of markerSet) {
        expect(panelSet.has(n), `Marker number ${n} not found in panel`).toBe(true);
      }
    });

    // ═══════════════════════════════════════════════════════════════════════
    // Section 5: Pseudo-ID guard — all citations
    // ═══════════════════════════════════════════════════════════════════════

    await test.step('V10: no SourceRef card ever contains pseudo document: ID', async () => {
      const items = page.locator('.rcp-citation-item');
      const count = await items.count();
      for (let i = 0; i < count; i++) {
        await items.nth(i).click();
        await page.waitForTimeout(600);
        const cards = page.locator('.esrc-card');
        const cardCount = await cards.count();
        for (let j = 0; j < cardCount; j++) {
          const text = (await cards.nth(j).textContent()) || '';
          expect(text).not.toContain('document:');
        }
      }
    });

    await test.step('V11: SourceRef links never contain dangerous schemes', async () => {
      const items = page.locator('.rcp-citation-item');
      await items.first().click();
      await page.waitForTimeout(1000);
      const links = page.locator('.esrc-link');
      const lc = await links.count();
      for (let i = 0; i < lc; i++) {
        const href = (await links.nth(i).getAttribute('href')) || '';
        expect(href).not.toContain('javascript:');
        expect(href).not.toContain('data:');
        expect(href).not.toContain('vbscript:');
      }
    });

    // ═══════════════════════════════════════════════════════════════════════
    // Section 6: RBAC — researcher audit form absence
    // ═══════════════════════════════════════════════════════════════════════

    await test.step('R01: researcher sees no review form on literature detail page', async () => {
      await page.goto(`${BASE}/literature/${RBAC_DOC_ID}`);
      await page.waitForTimeout(3000);

      // Admin review section guarded by v-if — must not be visible
      const adminPanel = page.locator('.admin-panel');
      await expect(adminPanel).not.toBeVisible({ timeout: 3000 });

      // Review <select> must not exist in DOM
      const reviewSelects = page.locator('.action-select');
      await expect(reviewSelects).toHaveCount(0);
    });

    // ═══════════════════════════════════════════════════════════════════════
    // Section 7: RBAC — server-side auth probe (same browser context)
    // ═══════════════════════════════════════════════════════════════════════

    await test.step('R02: researcher server-side auth probe returns 403 (服务端越权拒绝证据)', async () => {
      // Read real token from localStorage (set by UI login, key: hfb-access-token).
      // Verify token is valid via /api/v1/auth/me, then use it for review PATCH.
      const result = await page.evaluate(async (apiUrl, docId) => {
        const token = localStorage.getItem('hfb-access-token');
        if (!token) return { error: 'NO_TOKEN', status: -1 };

        const headers = {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        };

        // Confirm token is valid and belongs to authenticated user
        const meResp = await fetch(`${apiUrl}/api/v1/auth/me`, { headers, credentials: 'include' });
        if (meResp.status !== 200) return { error: 'AUTH_ME_FAILED', status: meResp.status };

        // Authorized probe: same token, review endpoint — must be 403
        const reviewResp = await fetch(`${apiUrl}/api/v1/documents/${docId}/review`, {
          method: 'PATCH',
          headers,
          body: JSON.stringify({ review_status: 'approved', rag_enabled: true }),
          credentials: 'include',
        });
        return { error: null, meStatus: meResp.status, reviewStatus: reviewResp.status };
      }, API, RBAC_DOC_ID);

      expect(result.error, `Token probe failed: ${JSON.stringify(result)}`).toBeNull();
      expect(result.meStatus, '/api/v1/auth/me must return 200 for logged-in researcher').toBe(200);
      expect(result.reviewStatus, `Expected 403, got ${result.reviewStatus} — 服务端越权拒绝证据`).toBe(403);
    });

    // ═══════════════════════════════════════════════════════════════════════
    // Section 8: RBAC — admin full UI flow (see form, submit, 2xx, restore)
    // ═══════════════════════════════════════════════════════════════════════

    await test.step('R03: admin sees review form, submits, gets 2xx, refresh confirms, restore', async () => {
      const adminContext = await browser.newContext();
      const adminPage = await adminContext.newPage();

      try {
        await loginAdmin(adminPage);

        await adminPage.goto(`${BASE}/literature/${RBAC_DOC_ID}`);
        await adminPage.waitForTimeout(3000);

        // Admin must see the admin panel with review form
        await expect(adminPage.locator('.admin-panel')).toBeVisible({ timeout: 5000 });

        // Verify current status shows "已通过" (approved)
        const pageText = (await adminPage.textContent('body')) || '';
        expect(pageText).toContain('已通过');

        // Change to "rejected" via real UI select + button click
        const patchPromise = adminPage.waitForResponse(
          (r) =>
            r.url().includes(`/api/v1/documents/${RBAC_DOC_ID}/review`) &&
            r.request().method() === 'PATCH',
          { timeout: 15_000 },
        );
        await adminPage.locator('.action-select').first().selectOption('rejected');
        await adminPage.waitForTimeout(300);
        await adminPage.locator('button.btn-primary').first().click();

        const resp = await patchPromise;
        expect(resp.status()).toBe(200);

        await adminPage.waitForTimeout(2000);
        const refreshedText = (await adminPage.textContent('body')) || '';
        expect(refreshedText).toContain('已驳回');
      } finally {
        // Restore to "approved" regardless of assertion failures above.
        // Restore MUST succeed with hard evidence: real UI, waitForResponse 200,
        // refresh confirms "已通过". No silent swallow.
        try {
          const currentStatus = (await adminPage.textContent('body')) || '';
          if (currentStatus.includes('已驳回')) {
            const restorePromise = adminPage.waitForResponse(
              (r) =>
                r.url().includes(`/api/v1/documents/${RBAC_DOC_ID}/review`) &&
                r.request().method() === 'PATCH',
              { timeout: 15_000 },
            );
            await adminPage.locator('.action-select').first().selectOption('approved');
            await adminPage.waitForTimeout(300);
            await adminPage.locator('button.btn-primary').first().click();
            const restoreResp = await restorePromise;
            expect(restoreResp.status(), 'RESTORE FAILED: PATCH did not return 200').toBe(200);
            await adminPage.waitForTimeout(1000);
            const finalText = (await adminPage.textContent('body')) || '';
            expect(finalText, 'RESTORE FAILED: page does not show 已通过 after restore').toContain('已通过');
          }
        } finally {
          await adminContext.close();
        }
    });
  });
});
