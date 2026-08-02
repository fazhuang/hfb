/**
 * C1-2 — Citation / Evidence / SourceRef Browser Closure E2E
 *
 * Codex invariants (one real document_id, two different passage_ids):
 *   Citation A/B must each show ONLY its own trace_id / passage_id Evidence + SourceRef.
 *   Reader link must be exact: /library/{document_id}?passage={passage_id}
 *   A page/Evidence/SourceRef/Reader must not show B identity, and vice versa.
 *
 * RBAC: researcher must be rejected (UI + 403/401); admin must succeed (2xx + visible state change).
 *
 * DESIGN:
 *   - NO beforeAll data creation. NO page.route(). NO request fixtures for browser tests.
 *   - Before any test, discovery phase scans existing sessions for real dual-passage data.
 *   - If no real data found: hard-fail BLOCK_C1_2_EVIDENCE — no synthetic bypass.
 *   - Sensitive operation: literature review on /literature/{docId} (real UI form).
 */

import { test, expect } from '@playwright/test';

const BASE = 'http://127.0.0.1:5173';
const API = 'http://127.0.0.1:8000';

// ─── Login helpers (real UI form submit, no token injection) ──────────

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

// ─── Real data scanner (API-only, used once to discover candidate) ────

interface DualPassageCandidate {
  resultUrl: string;
  sessionId: string;
  runId: string;
  docId: string;
  pair: Array<{
    citationTraceId: string;
    passageId: string;
    sourceRefTitle: string;
    sourceRefId: string;
  }>;
}

/**
 * Scan existing sessions for a run containing >=2 evidence entries
 * from the same document_id with different passage_ids AND real SourceRefs.
 */
async function discoverDualPassageCandidate(request: any): Promise<DualPassageCandidate | null> {
  const authResp = await request.post(`${API}/api/v1/auth/login`, {
    data: { username: 'researcher', password: 'researcher123' },
  });
  if (!authResp.ok()) return null;
  const token = (await authResp.json()).data.access_token;
  const h = { Authorization: `Bearer ${token}` };

  const sessResp = await request.get(`${API}/api/v1/workspace/sessions?limit=50`, { headers: h });
  if (!sessResp.ok()) return null;
  const sessions = (await sessResp.json()).data ?? [];

  for (const s of sessions) {
    const sid = s.id;
    const runsResp = await request.get(`${API}/api/v4/research/session/${sid}/runs`, { headers: h });
    if (!runsResp.ok()) continue;
    const runs = (await runsResp.json()).data?.runs ?? [];

    for (const runEntry of runs) {
      const manifest = runEntry.replay_manifest ?? {};
      const snapshot: Array<Record<string, unknown>> = manifest.retrieval_snapshot ?? [];
      const traces: Array<Record<string, unknown>> = manifest.traces ?? [];
      if (snapshot.length < 2) continue;

      const traceMap = new Map<string, Record<string, unknown>>();
      for (const tr of traces) {
        const tid = tr.trace_id as string;
        if (tid) traceMap.set(tid, tr);
      }

      // Group by document_id, collect unique passage_ids with SourceRef
      const docGroups = new Map<string, Array<{ tid: string; pid: string; srTitle: string; srId: string }>>();
      for (const snap of snapshot) {
        const tid = snap.trace_id as string;
        const docId = snap.document_id as string;
        const srTitle = snap.source_ref_title as string;
        const srId = snap.source_ref_id as string;
        const tr = tid ? traceMap.get(tid) : undefined;
        const pid = (tr?.passage_id as string) || '';
        if (docId && pid && srTitle && tid) {
          const entries = docGroups.get(docId) ?? [];
          entries.push({ tid, pid, srTitle, srId });
          docGroups.set(docId, entries);
        }
      }

      for (const [docId, entries] of docGroups) {
        const uniquePids = new Set(entries.map((e) => e.pid));
        if (uniquePids.size >= 2) {
          const seenPids = new Set<string>();
          const pair: DualPassageCandidate['pair'] = [];
          for (const e of entries) {
            if (!seenPids.has(e.pid)) {
              seenPids.add(e.pid);
              pair.push({
                citationTraceId: e.tid,
                passageId: e.pid,
                sourceRefTitle: e.srTitle,
                sourceRefId: e.srId,
              });
              if (pair.length >= 2) break;
            }
          }
          console.log(`C1-2 discovery: doc ${docId.slice(0, 16)}... has ${uniquePids.size} passages`);
          return {
            resultUrl: `/research/${sid}/result/${runEntry.run_id}`,
            sessionId: sid,
            runId: runEntry.run_id as string,
            docId,
            pair,
          };
        }
      }
    }
  }
  return null;
}

// ─── Existing document for RBAC test (real, pre-seeded) ──────────────

/** 针灸甲乙经（四库全书本）— known to have review_status: approved, rag_enabled: true */
const KNOWN_DOC_ID = '378224ae-0325-47f9-80c3-b99c72569bce';
const KNOWN_DOC_TITLE = '鍼灸甲乙經';

// ─── Full suite ───────────────────────────────────────────────────────

test.describe('C1-2 — Citation / Evidence / SourceRef browser closure', () => {

  let candidate: DualPassageCandidate | null = null;

  // ═══════════════════════════════════════════════════════════════════════
  // Discovery — find real dual-passage same-doc pair, or hard-fail
  // ═══════════════════════════════════════════════════════════════════════

  test('C1-2-DISCOVER: find real same-document two-passage citation pair', async ({ request }) => {
    candidate = await discoverDualPassageCandidate(request);
    // Hard-fail: no real data → no test can proceed
    expect(
      candidate,
      'BLOCK_C1_2_EVIDENCE: no real same-document two-passage citation pair found in existing sessions',
    ).not.toBeNull();
  });

  // ═══════════════════════════════════════════════════════════════════════
  // Section 1: Dual-passage chain isolation (only if DISCOVER passed)
  // ═══════════════════════════════════════════════════════════════════════

  test('C1-2-V01: result page loads via real login, shows citation panel', async ({ page }) => {
    expect(candidate, 'BLOCK_C1_2_EVIDENCE: no candidate from DISCOVER').not.toBeNull();
    await loginResearcher(page);
    await page.goto(`${BASE}${candidate!.resultUrl}`);
    await page.waitForSelector('.rrv-report', { state: 'visible', timeout: 15_000 });
    await expect(page.locator('.rcp-citation-item').first()).toBeVisible({ timeout: 5_000 });
  });

  test('C1-2-V02: click citation A shows Evidence with correct trace_id / passage_id', async ({ page }) => {
    expect(candidate, 'BLOCK_C1_2_EVIDENCE: no candidate').not.toBeNull();
    await loginResearcher(page);
    await page.goto(`${BASE}${candidate!.resultUrl}`);
    await page.waitForSelector('.rrv-report', { state: 'visible', timeout: 15_000 });

    const entry = candidate!.pair[0];
    // Find and click the citation item whose trace_id matches entry.citationTraceId
    const citationItems = page.locator('.rcp-citation-item');
    const count = await citationItems.count();
    let clicked = false;
    for (let i = 0; i < count; i++) {
      const text = await citationItems.nth(i).textContent();
      if (text?.includes(entry.citationTraceId.slice(0, 8))) {
        await citationItems.nth(i).click();
        clicked = true;
        break;
      }
    }
    expect(clicked, `Could not find citation with trace_id ${entry.citationTraceId}`).toBe(true);
    await page.waitForTimeout(1000);

    // Evidence must show this trace_id and passage_id
    const evidenceArea = page.locator('.rcp-evidence-area');
    const evText = (await evidenceArea.textContent()) || '';
    expect(evText).toContain(entry.citationTraceId.slice(0, 16));
    expect(evText).toContain(entry.passageId.slice(0, 16));

    // SourceRef must show real title
    const srcCard = page.locator('.esrc-card').first();
    await expect(srcCard).toBeVisible({ timeout: 5_000 });
    const srcText = (await srcCard.textContent()) || '';
    expect(srcText).toContain(entry.sourceRefTitle.slice(0, 8));
    expect(srcText).not.toContain('缺少文献来源信息');
    expect(srcText).not.toContain('document:');
  });

  test('C1-2-V03: Reader link for citation A points to exact /library/{docId}?passage={passageId}', async ({ page }) => {
    expect(candidate, 'BLOCK_C1_2_EVIDENCE: no candidate').not.toBeNull();
    await loginResearcher(page);
    await page.goto(`${BASE}${candidate!.resultUrl}`);
    await page.waitForSelector('.rrv-report', { state: 'visible', timeout: 15_000 });

    const entry = candidate!.pair[0];
    // Click the matching citation
    const citationItems = page.locator('.rcp-citation-item');
    const count = await citationItems.count();
    for (let i = 0; i < count; i++) {
      const text = await citationItems.nth(i).textContent();
      if (text?.includes(entry.citationTraceId.slice(0, 8))) {
        await citationItems.nth(i).click();
        break;
      }
    }
    await page.waitForTimeout(1000);

    // SourceRef internal link must be /library/{docId}?passage={passageId}
    const link = page.locator('.esrc-link').first();
    const linkCount = await link.count();
    expect(linkCount).toBeGreaterThan(0);

    const href = (await link.getAttribute('href')) || '';
    expect(href).toContain(`/library/${candidate!.docId}`);
    expect(href).toContain(`passage=${entry.passageId}`);

    // Navigate via the link — must land on non-login, content-bearing page
    await link.click();
    await page.waitForTimeout(4000);
    expect(page.url()).not.toContain('/login');
    const bodyText = (await page.textContent('body')) || '';
    expect(bodyText.length).toBeGreaterThan(200);
    expect(bodyText).not.toContain('404 Not Found');
  });

  test('C1-2-V04: click citation B shows DIFFERENT passage_id, no cross-contamination', async ({ page }) => {
    expect(candidate, 'BLOCK_C1_2_EVIDENCE: no candidate').not.toBeNull();
    await loginResearcher(page);
    await page.goto(`${BASE}${candidate!.resultUrl}`);
    await page.waitForSelector('.rrv-report', { state: 'visible', timeout: 15_000 });

    const entryB = candidate!.pair[1];
    const citationItems = page.locator('.rcp-citation-item');
    const count = await citationItems.count();
    let clicked = false;
    for (let i = 0; i < count; i++) {
      const text = await citationItems.nth(i).textContent();
      if (text?.includes(entryB.citationTraceId.slice(0, 8))) {
        await citationItems.nth(i).click();
        clicked = true;
        break;
      }
    }
    expect(clicked, `Could not find citation B with trace_id ${entryB.citationTraceId}`).toBe(true);
    await page.waitForTimeout(1000);

    const evidenceArea = page.locator('.rcp-evidence-area');
    const evText = (await evidenceArea.textContent()) || '';

    // Must show passage B's identity
    expect(evText).toContain(entryB.passageId.slice(0, 16));

    // Must NOT contain passage A's identity
    const entryA = candidate!.pair[0];
    expect(evText).not.toContain(entryA.passageId.slice(0, 16));
    expect(evText).not.toContain(entryA.sourceRefTitle);
  });

  test('C1-2-V05: passage A and B are different', async () => {
    expect(candidate, 'BLOCK_C1_2_EVIDENCE: no candidate').not.toBeNull();
    expect(candidate!.pair[0].passageId).not.toBe(candidate!.pair[1].passageId);
  });

  // ═══════════════════════════════════════════════════════════════════════
  // Section 2: Fail-closed — evidence without SourceRef shows missing state
  // ═══════════════════════════════════════════════════════════════════════

  test('C1-2-V06: page body never contains pseudo document: IDs', async ({ page }) => {
    expect(candidate, 'BLOCK_C1_2_EVIDENCE: no candidate').not.toBeNull();
    await loginResearcher(page);
    await page.goto(`${BASE}${candidate!.resultUrl}`);
    await page.waitForSelector('.rrv-report', { state: 'visible', timeout: 15_000 });

    // Click each citation, check SourceRef card never fabricates pseudo IDs
    const citationItems = page.locator('.rcp-citation-item');
    const count = await citationItems.count();
    for (let i = 0; i < count; i++) {
      await citationItems.nth(i).click();
      await page.waitForTimeout(600);

      const srcCards = page.locator('.esrc-card');
      const cardCount = await srcCards.count();
      for (let j = 0; j < cardCount; j++) {
        const text = (await srcCards.nth(j).textContent()) || '';
        expect(text).not.toContain('document:');
      }
    }
  });

  test('C1-2-V07: SourceRef links never contain javascript: or dangerous schemes', async ({ page }) => {
    expect(candidate, 'BLOCK_C1_2_EVIDENCE: no candidate').not.toBeNull();
    await loginResearcher(page);
    await page.goto(`${BASE}${candidate!.resultUrl}`);
    await page.waitForSelector('.rrv-report', { state: 'visible', timeout: 15_000 });

    const citationItems = page.locator('.rcp-citation-item');
    await citationItems.first().click();
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
  // Section 3: Display number consistency
  // ═══════════════════════════════════════════════════════════════════════

  test('C1-2-V08: first report marker number equals first panel citation number', async ({ page }) => {
    expect(candidate, 'BLOCK_C1_2_EVIDENCE: no candidate').not.toBeNull();
    await loginResearcher(page);
    await page.goto(`${BASE}${candidate!.resultUrl}`);
    await page.waitForSelector('.rrv-report', { state: 'visible', timeout: 15_000 });

    const markers = page.locator('.rrv-citation-marker');
    const panels = page.locator('.rcp-citation-item');
    if ((await markers.count()) > 0 && (await panels.count()) > 0) {
      const mText = ((await markers.first().textContent()) || '').replace(/[[\]\s]/g, '').trim();
      const pText = (
        (await panels.first().locator('.rcp-citation-number').textContent()) || ''
      )
        .replace(/[#[\]\s]/g, '')
        .trim();
      // Both should be numbers and equal
      expect(mText).toBe(pText);
    }
  });

  test('C1-2-V09: unique marker set is subset of unique panel number set', async ({ page }) => {
    expect(candidate, 'BLOCK_C1_2_EVIDENCE: no candidate').not.toBeNull();
    await loginResearcher(page);
    await page.goto(`${BASE}${candidate!.resultUrl}`);
    await page.waitForSelector('.rrv-report', { state: 'visible', timeout: 15_000 });

    const markers = page.locator('.rrv-citation-marker');
    const mc = await markers.count();
    const markerSet = new Set<string>();
    for (let i = 0; i < mc; i++) {
      const t = ((await markers.nth(i).textContent()) || '').replace(/[[\]\s]/g, '').trim();
      if (t && t !== 'undefined') markerSet.add(t);
    }

    const panels = page.locator('.rcp-citation-item');
    const pc = await panels.count();
    const panelSet = new Set<string>();
    for (let i = 0; i < pc; i++) {
      const t = (
        (await panels.nth(i).locator('.rcp-citation-number').textContent()) || ''
      )
        .replace(/[#[\]\s]/g, '')
        .trim();
      if (t && t !== '?' && t !== 'undefined') panelSet.add(t);
    }

    for (const n of markerSet) {
      expect(panelSet.has(n), `Marker number ${n} not found in panel`).toBe(true);
    }
    expect(panelSet.size).toBeGreaterThanOrEqual(markerSet.size);
  });

  // ═══════════════════════════════════════════════════════════════════════
  // Section 4: RBAC — sensitive operation via real browser UI
  // ═══════════════════════════════════════════════════════════════════════
  //
  // Sensitive operation: literature document review on /literature/{docId}
  // This page has a real <select> + <button> form that PATCHes review_status.
  // Regular researcher must be rejected; admin must succeed.

  test('C1-2-R01: researcher sees no review form on literature detail page', async ({ page }) => {
    await loginResearcher(page);
    await page.goto(`${BASE}/literature/${KNOWN_DOC_ID}`);
    await page.waitForTimeout(3000);

    // Admin review section is guarded by v-if="auth.canReviewDocuments".
    // Researcher must NOT see the admin-panel section (contains review <select> + submit button).
    const adminPanel = page.locator('.admin-panel');
    await expect(adminPanel).not.toBeVisible({ timeout: 3000 });

    // Double-check: the review status <select> must not exist in DOM at all
    const reviewSelects = page.locator('.action-select');
    await expect(reviewSelects).toHaveCount(0);
  });

  test('C1-2-R02: researcher PATCH to review endpoint returns 403 via browser', async ({ page }) => {
    // Log in via real UI
    await loginResearcher(page);

    // Use page.request (inherits browser cookies) to attempt the PATCH
    const resp = await page.request.patch(`${API}/api/v1/documents/${KNOWN_DOC_ID}/review`, {
      data: { review_status: 'approved', rag_enabled: true },
    });
    // Must be rejected
    expect(resp.status()).toBeGreaterThanOrEqual(400);
    // Specifically 403 or 401
    expect([401, 403]).toContain(resp.status());
  });

  test('C1-2-R03: admin sees review form and can change review status', async ({ page }) => {
    await loginAdmin(page);
    // Intercept the PATCH before navigating so we capture it on submission
    const patchPromise = page.waitForResponse(
      (r) =>
        r.url().includes(`/api/v1/documents/${KNOWN_DOC_ID}/review`) &&
        r.request().method() === 'PATCH',
      { timeout: 15_000 },
    );

    await page.goto(`${BASE}/literature/${KNOWN_DOC_ID}`);
    await page.waitForTimeout(3000);

    // Admin must see the admin panel with review form
    await expect(page.locator('.admin-panel')).toBeVisible({ timeout: 5000 });

    // Read current review status badge
    const pageText = (await page.textContent('body')) || '';
    // Document is already 'approved' — visible as "已通过" badge
    expect(pageText).toContain('已通过');

    // Select "rejected" to toggle state
    await page.locator('.action-select').first().selectOption('rejected');
    await page.waitForTimeout(300);

    // Click submit and capture response
    await page.locator('button.btn-primary').first().click();
    const resp = await patchPromise;
    expect(resp.status()).toBe(200);

    // Page should refresh — wait and verify new status
    await page.waitForTimeout(2000);
    const refreshedText = (await page.textContent('body')) || '';
    expect(refreshedText).toContain('已驳回');

    // ── Restore to "approved" ──
    const patchPromise2 = page.waitForResponse(
      (r) =>
        r.url().includes(`/api/v1/documents/${KNOWN_DOC_ID}/review`) &&
        r.request().method() === 'PATCH',
      { timeout: 15_000 },
    );
    await page.locator('.action-select').first().selectOption('approved');
    await page.waitForTimeout(300);
    await page.locator('button.btn-primary').first().click();
    const resp2 = await patchPromise2;
    expect(resp2.status()).toBe(200);
    await page.waitForTimeout(1000);
    const finalText = (await page.textContent('body')) || '';
    expect(finalText).toContain('已通过');
  });
});
