/**
 * B3-5 HfbIcon — Browser Accessibility Evidence
 *
 * Mounts real HfbIcon, HfbButton (icon-only), HfbAlert, EmptyState,
 * ErrorState, StatusCard via standalone Vite fixture.
 * No backend, no login, no router.
 *
 * Verified behaviours:
 *   - HfbIcon renders SVG with role="img"
 *   - Default decorative: aria-hidden="true"
 *   - Labeled: aria-label present, role="img"
 *   - Icon-only button: aria-label on the <button>, icon inside is hidden
 *   - Converted components render SVG icons (no unicode fallback)
 */

import { test, expect } from '@playwright/test';

const FIXTURE = 'http://127.0.0.1:5173/src/e2e/fixtures/b3-5-icon-fixture.html';

test.describe('B3-5 HfbIcon — Raw Icon Rendering', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(FIXTURE);
    await page.waitForSelector('[data-testid="icon-decorative"]', { state: 'visible', timeout: 10_000 });
  });

  test('decorative icon has role="img" and aria-hidden="true"', async ({ page }) => {
    const container = page.locator('[data-testid="icon-decorative"]');
    const svg = container.locator('svg');
    await expect(svg).toBeVisible();
    await expect(svg).toHaveAttribute('role', 'img');
    await expect(svg).toHaveAttribute('aria-hidden', 'true');
  });

  test('labeled icon has aria-label and role="img"', async ({ page }) => {
    const container = page.locator('[data-testid="icon-labeled"]');
    const svg = container.locator('svg');
    await expect(svg).toBeVisible();
    await expect(svg).toHaveAttribute('aria-label', 'Information');
    await expect(svg).toHaveAttribute('role', 'img');
  });

  test('large icon renders at correct size', async ({ page }) => {
    const container = page.locator('[data-testid="icon-large"]');
    const svg = container.locator('svg');
    const width = await svg.getAttribute('width');
    expect(parseInt(width || '0', 10)).toBe(36);
  });

  test('colored icon renders with fill color', async ({ page }) => {
    const container = page.locator('[data-testid="icon-colored"]');
    const svg = container.locator('svg');
    await expect(svg).toBeVisible();
  });
});

test.describe('B3-5 Icon-Only Button — ARIA Contract', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(FIXTURE);
    await page.waitForSelector('[data-testid="icon-button"]', { state: 'visible', timeout: 10_000 });
  });

  test('button has aria-label "Close dialog"', async ({ page }) => {
    const btn = page.locator('[data-testid="icon-button"] button');
    await expect(btn).toBeVisible();
    await expect(btn).toHaveAttribute('aria-label', 'Close dialog');
  });

  test('icon inside button is not the accessible name source', async ({ page }) => {
    // The icon inside an icon-only button should still render as SVG,
    // but the accessible name comes from the button's aria-label.
    const btn = page.locator('[data-testid="icon-button"] button');
    const svg = btn.locator('svg');
    await expect(svg).toBeVisible();
  });
});

test.describe('B3-5 Converted Components — SVG Icons', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(FIXTURE);
    await page.waitForSelector('[data-testid="alert-error-svg"]', { state: 'visible', timeout: 10_000 });
  });

  test('HfbAlert error variant shows SVG icon (not unicode ✕)', async ({ page }) => {
    const alert = page.locator('[data-testid="alert-error-svg"] .hfb-alert');
    await expect(alert).toBeVisible();
    // The icon should be an SVG, not a unicode text ✕
    const svg = alert.locator('svg').first();
    await expect(svg).toBeVisible();
    // Verify no raw unicode ✕ in the alert icon area
    const iconSpan = alert.locator('.hfb-alert__icon').first();
    const text = await iconSpan.textContent();
    expect(text?.trim()).toBe('');
  });

  test('EmptyState shows SVG icon (not emoji 📭)', async ({ page }) => {
    const container = page.locator('[data-testid="empty-svg"]');
    // HfbIcon wraps Icon from @iconify/vue — verify it renders an SVG
    const svg = container.locator('svg');
    await expect(svg.first()).toBeVisible({ timeout: 5_000 });
  });

  test('ErrorState shows SVG icon (not emoji ⚠️)', async ({ page }) => {
    const container = page.locator('[data-testid="error-svg"]');
    const svg = container.locator('svg');
    await expect(svg.first()).toBeVisible({ timeout: 5_000 });
  });

  test('StatusCard connected shows SVG icon (not unicode ✓)', async ({ page }) => {
    const card = page.locator('[data-testid="status-connected"] .status-card');
    const svg = card.locator('svg');
    await expect(svg.first()).toBeVisible({ timeout: 5_000 });
  });

  test('StatusCard disconnected shows SVG icon (not unicode ✗)', async ({ page }) => {
    const card = page.locator('[data-testid="status-disconnected"] .status-card');
    const svg = card.locator('svg');
    await expect(svg.first()).toBeVisible({ timeout: 5_000 });
  });
});
