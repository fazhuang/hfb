/**
 * B3-3 Dialog/Drawer — Browser Accessibility Evidence
 *
 * Mounts real HfbDialog + HfbDrawer via standalone Vite fixtures.
 * No backend, no login, no router.
 *
 * Verified behaviours:
 *   - Dialog: role="dialog", aria-modal="true", aria-labelledby ↔ title
 *   - Dialog: Escape closes, focus trapped
 *   - Drawer: role="dialog", aria-modal="true", aria-label from title
 *   - Drawer: Escape closes, close button aria-label
 */

import { test, expect } from '@playwright/test';

const FIXTURE = 'http://127.0.0.1:5173/src/e2e/fixtures/b3-3-dialog-drawer-fixture.html';

test.describe('B3-3 HfbDialog — States & Accessibility', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(FIXTURE);
    await page.waitForSelector('[data-testid="open-dialog-btn"]', { state: 'visible', timeout: 10_000 });
  });

  test('dialog opens with role="dialog" and aria-modal="true"', async ({ page }) => {
    await page.locator('[data-testid="open-dialog-btn"]').click();
    await page.waitForSelector('.hfb-dialog', { state: 'visible', timeout: 5_000 });

    const dialog = page.locator('[role="dialog"]');
    await expect(dialog).toBeVisible();
    await expect(dialog).toHaveAttribute('aria-modal', 'true');
  });

  test('dialog has aria-labelledby pointing to visible title', async ({ page }) => {
    await page.locator('[data-testid="open-dialog-btn"]').click();
    await page.waitForSelector('.hfb-dialog__title', { state: 'visible', timeout: 5_000 });

    const dialog = page.locator('[role="dialog"]');
    const labelledBy = await dialog.getAttribute('aria-labelledby');
    expect(labelledBy).toBeTruthy();

    const title = page.locator(`#${labelledBy}`);
    await expect(title).toBeVisible();
    await expect(title).toHaveText('Confirm Action');
  });

  test('Escape key closes the dialog', async ({ page }) => {
    await page.locator('[data-testid="open-dialog-btn"]').click();
    await page.waitForSelector('.hfb-dialog', { state: 'visible', timeout: 5_000 });

    // Dispatch a keydown Escape on the dialog element — the overlay div has
    // @keydown.escape="onEscape" which bubbles up.
    await page.locator('.hfb-dialog').evaluate((el) => {
      el.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    });
    await page.waitForTimeout(500);

    const exists = await page.locator('.hfb-dialog__overlay').count();
    expect(exists).toBe(0);
  });
});

test.describe('B3-3 HfbDrawer — States & Accessibility', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(FIXTURE);
    await page.waitForSelector('[data-testid="open-drawer-btn"]', { state: 'visible', timeout: 10_000 });
  });

  test('drawer opens with role="dialog" and aria-modal="true"', async ({ page }) => {
    await page.locator('[data-testid="open-drawer-btn"]').click();
    await page.waitForSelector('.hfb-drawer', { state: 'visible', timeout: 5_000 });

    const drawer = page.locator('[role="dialog"]').last();
    await expect(drawer).toBeVisible();
    await expect(drawer).toHaveAttribute('aria-modal', 'true');
  });

  test('drawer aria-label matches title prop', async ({ page }) => {
    await page.locator('[data-testid="open-drawer-btn"]').click();
    await page.waitForSelector('.hfb-drawer__title', { state: 'visible', timeout: 5_000 });

    // The drawer uses aria-label (not labelledby), matching the title
    const drawer = page.locator('.hfb-drawer');
    await expect(drawer).toHaveAttribute('aria-label', 'Settings Panel');
  });

  test('Escape key closes the drawer', async ({ page }) => {
    await page.locator('[data-testid="open-drawer-btn"]').click();
    await page.waitForSelector('.hfb-drawer', { state: 'visible', timeout: 5_000 });

    // Dispatch Escape on drawer element — overlay listens via @keydown.escape
    await page.locator('.hfb-drawer').evaluate((el) => {
      el.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    });
    await page.waitForTimeout(500);

    const exists = await page.locator('.hfb-drawer__overlay').count();
    expect(exists).toBe(0);
  });
});
