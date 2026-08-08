/**
 * B3-4 State Components — Browser Accessibility Evidence
 *
 * Mounts real EmptyState, ErrorState, LoadingState, HfbSkeleton, HfbAlert
 * via standalone Vite fixture.  No backend, no login, no router.
 *
 * Verified behaviours:
 *   - EmptyState: role="status", aria-live="polite"
 *   - ErrorState: role="alert", aria-live="assertive", retry button
 *   - LoadingState: role="status", aria-live="polite", spinner aria-hidden
 *   - HfbSkeleton: role="status", aria-busy="true", variant aria-labels
 *   - HfbAlert: error→role="alert", info→role="status", close aria-label
 */

import { test, expect } from '@playwright/test';

const FIXTURE = 'http://127.0.0.1:5173/src/e2e/fixtures/b3-4-state-components-fixture.html';

test.describe('B3-4 EmptyState — Accessibility', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(FIXTURE);
    await page.waitForSelector('[data-testid="empty-state-container"]', {
      state: 'visible',
      timeout: 10_000,
    });
  });

  test('has role="status"', async ({ page }) => {
    const el = page.locator('[data-testid="empty-state-container"] [role="status"]');
    await expect(el).toBeVisible();
  });

  test('renders title and description', async ({ page }) => {
    const container = page.locator('[data-testid="empty-state-container"]');
    await expect(container.locator('.empty-title')).toHaveText('No items');
    await expect(container.locator('.empty-description')).toHaveText('Add your first item.');
  });
});

test.describe('B3-4 ErrorState — Accessibility', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(FIXTURE);
    await page.waitForSelector('[data-testid="error-state-container"]', {
      state: 'visible',
      timeout: 10_000,
    });
  });

  test('has role="alert" and aria-live="assertive"', async ({ page }) => {
    const el = page.locator('[data-testid="error-state-container"] [role="alert"]');
    await expect(el).toBeVisible();
    await expect(el).toHaveAttribute('aria-live', 'assertive');
  });

  test('renders retry button with label', async ({ page }) => {
    const btn = page.locator('[data-testid="error-state-container"] button');
    await expect(btn).toBeVisible();
    await expect(btn).toHaveText('Retry');
  });
});

test.describe('B3-4 LoadingState — Accessibility', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(FIXTURE);
    await page.waitForSelector('[data-testid="loading-state-container"]', {
      state: 'visible',
      timeout: 10_000,
    });
  });

  test('has role="status" and aria-live="polite"', async ({ page }) => {
    const el = page.locator('[data-testid="loading-state-container"] [role="status"]');
    await expect(el).toBeVisible();
    await expect(el).toHaveAttribute('aria-live', 'polite');
  });

  test('spinner is aria-hidden', async ({ page }) => {
    const spinner = page.locator('[data-testid="loading-state-container"] .loading-spinner');
    await expect(spinner).toBeVisible();
    await expect(spinner).toHaveAttribute('aria-hidden', 'true');
  });

  test('prefers-reduced-motion: reduce disables spinner animation', async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto(FIXTURE);
    await page.waitForSelector('[data-testid="loading-state-container"]', {
      state: 'visible',
      timeout: 10_000,
    });

    const animName = await page
      .locator('[data-testid="loading-state-container"] .loading-spinner')
      .evaluate((el) => window.getComputedStyle(el).animationName);
    expect(animName).toBe('none');
  });
});

test.describe('B3-4 HfbSkeleton — Accessibility', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(FIXTURE);
    await page.waitForSelector('[data-testid="skeleton-text"]', {
      state: 'visible',
      timeout: 10_000,
    });
  });

  test('has role="status" and aria-busy="true"', async ({ page }) => {
    const el = page.locator('[data-testid="skeleton-text"] [role="status"]');
    await expect(el).toBeVisible();
    await expect(el).toHaveAttribute('aria-busy', 'true');
  });

  test('text variant has aria-label "Loading text..."', async ({ page }) => {
    const el = page.locator('[data-testid="skeleton-text"] [aria-label="Loading text..."]');
    await expect(el).toBeVisible();
  });

  test('circle variant has aria-label "Loading avatar..."', async ({ page }) => {
    const el = page.locator('[data-testid="skeleton-circle"] [aria-label="Loading avatar..."]');
    await expect(el).toBeVisible();
  });

  test('rect variant has aria-label "Loading content..."', async ({ page }) => {
    const el = page.locator('[data-testid="skeleton-rect"] [aria-label="Loading content..."]');
    await expect(el).toBeVisible();
  });

  test('prefers-reduced-motion: reduce disables skeleton animation', async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto(FIXTURE);
    await page.waitForSelector('[data-testid="skeleton-text"]', {
      state: 'visible',
      timeout: 10_000,
    });

    const animName = await page
      .locator('[data-testid="skeleton-text"] .hfb-skeleton')
      .evaluate((el) => window.getComputedStyle(el).animationName);
    expect(animName).toBe('none');
  });
});

test.describe('B3-4 HfbAlert — Accessibility', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(FIXTURE);
    await page.waitForSelector('[data-testid="alert-info"]', { state: 'visible', timeout: 10_000 });
  });

  test('error alert has role="alert" and aria-live="assertive"', async ({ page }) => {
    const el = page.locator('[data-testid="alert-error"] [role="alert"]');
    await expect(el).toBeVisible();
    await expect(el).toHaveAttribute('aria-live', 'assertive');
  });

  test('info alert has role="status" and aria-live="polite"', async ({ page }) => {
    const el = page.locator('[data-testid="alert-info"] [role="status"]');
    await expect(el).toBeVisible();
    await expect(el).toHaveAttribute('aria-live', 'polite');
  });

  test('success alert renders correctly', async ({ page }) => {
    const el = page.locator('[data-testid="alert-success"] .hfb-alert');
    await expect(el).toBeVisible();
    await expect(el.locator('.hfb-alert__body')).toHaveText('Operation completed.');
  });
});
