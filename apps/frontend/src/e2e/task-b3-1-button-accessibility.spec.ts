/**
 * B3-1 HfbButton — Browser Accessibility Evidence
 *
 * Mounts the real HfbButton component via a standalone Vite fixture.
 * No backend, no login, no router — only HfbButton.
 *
 * Verified browser behaviours:
 *   - Enter / Space keydown → real click on native <button>
 *   - disabled + loading prevent keyboard activation
 *   - loading → aria-busy="true", disabled, aria-disabled="true", spinner visible
 *   - icon-only → exact aria-label on the native <button>
 *   - Tab → :focus-visible with visible outline
 *   - prefers-reduced-motion: reduce → computed animation-name === "none"
 */

import { test, expect } from '@playwright/test';

const FIXTURE = 'http://127.0.0.1:5173/src/e2e/fixtures/b3-1-button-fixture.html';

// ────────────────────────────────────────────────────────────────────────
// Selector helpers — fail fast if element is missing
// ────────────────────────────────────────────────────────────────────────

const normalBtn = () => '[data-testid="btn-normal"] button';
const disabledBtn = () => '[data-testid="btn-disabled"] button';
const loadingBtn = () => '[data-testid="btn-loading"] button';
const iconOnlyBtn = () => '[data-testid="btn-icon-only"] button';
const clickOutput = () => '[data-testid="click-output"]';

/** Read the serialised click-counts object from the page */
async function getClickCounts(page: any): Promise<Record<string, number>> {
  const text = await page.locator(clickOutput()).textContent();
  return JSON.parse(text || '{}');
}

// ────────────────────────────────────────────────────────────────────────

test.describe('B3-1 HfbButton — Keyboard Activation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(FIXTURE);
    await page.waitForSelector(normalBtn(), { state: 'visible', timeout: 10_000 });
  });

  test('Enter key fires click on native HfbButton', async ({ page }) => {
    const beforeRaw = await getClickCounts(page);
    const before = beforeRaw.normal ?? 0;

    await page.locator(normalBtn()).focus();
    await page.keyboard.press('Enter');

    const afterRaw = await getClickCounts(page);
    expect(afterRaw.normal ?? 0).toBe(before + 1);
  });

  test('Space key fires click on native HfbButton', async ({ page }) => {
    const beforeRaw = await getClickCounts(page);
    const before = beforeRaw.normal ?? 0;

    await page.locator(normalBtn()).focus();
    await page.keyboard.press('Space');

    const afterRaw = await getClickCounts(page);
    expect(afterRaw.normal ?? 0).toBe(before + 1);
  });

  test('disabled HfbButton does not fire click on Enter', async ({ page }) => {
    const beforeRaw = await getClickCounts(page);
    const before = beforeRaw.disabled ?? 0;

    await page.locator(disabledBtn()).focus();
    await page.keyboard.press('Enter');

    const afterRaw = await getClickCounts(page);
    expect(afterRaw.disabled ?? 0).toBe(before);
  });

  test('disabled HfbButton does not fire click on Space', async ({ page }) => {
    const beforeRaw = await getClickCounts(page);
    const before = beforeRaw.disabled ?? 0;

    await page.locator(disabledBtn()).focus();
    await page.keyboard.press('Space');

    const afterRaw = await getClickCounts(page);
    expect(afterRaw.disabled ?? 0).toBe(before);
  });

  test('loading HfbButton does not fire click on Enter', async ({ page }) => {
    const beforeRaw = await getClickCounts(page);
    const before = beforeRaw.loading ?? 0;

    await page.locator(loadingBtn()).focus();
    await page.keyboard.press('Enter');

    const afterRaw = await getClickCounts(page);
    expect(afterRaw.loading ?? 0).toBe(before);
  });

  test('loading HfbButton does not fire click on Space', async ({ page }) => {
    const beforeRaw = await getClickCounts(page);
    const before = beforeRaw.loading ?? 0;

    await page.locator(loadingBtn()).focus();
    await page.keyboard.press('Space');

    const afterRaw = await getClickCounts(page);
    expect(afterRaw.loading ?? 0).toBe(before);
  });
});

// ────────────────────────────────────────────────────────────────────────

test.describe('B3-1 HfbButton — ARIA & DOM State', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(FIXTURE);
    await page.waitForSelector(normalBtn(), { state: 'visible', timeout: 10_000 });
  });

  test('loading button has aria-busy="true", disabled, aria-disabled="true"', async ({
    page,
  }) => {
    const btn = page.locator(loadingBtn());

    await expect(btn).toHaveAttribute('aria-busy', 'true');
    await expect(btn).toHaveAttribute('disabled', '');
    await expect(btn).toHaveAttribute('aria-disabled', 'true');
    await expect(btn.locator('.hfb-button__spinner')).toBeVisible();
  });

  test('disabled button has disabled and aria-disabled="true"', async ({ page }) => {
    const btn = page.locator(disabledBtn());

    await expect(btn).toHaveAttribute('disabled', '');
    await expect(btn).toHaveAttribute('aria-disabled', 'true');
  });

  test('normal button does not have aria-busy and is not disabled', async ({ page }) => {
    const btn = page.locator(normalBtn());

    const busy = await btn.getAttribute('aria-busy');
    expect(busy).toBeNull();

    const disabled = await btn.getAttribute('disabled');
    expect(disabled).toBeNull();
  });

  test('icon-only button has exact aria-label on native <button>', async ({ page }) => {
    const btn = page.locator(iconOnlyBtn());

    await expect(btn).toHaveAttribute('aria-label', 'Close dialog');

    // Icon-only: no default slot text content — accessible name is
    // from aria-label. The "✕" is inside the icon slot (aria-hidden
    // by convention, though HfbButton does not yet enforce that).
    // Verify the button's text content is only the icon character
    // (no extra label text).
    const text = await btn.textContent();
    // Trim to guard against whitespace-only; "✕" is expected from icon slot
    expect(text?.trim()).toBe('✕');
  });

  test('all buttons are native <button> elements', async ({ page }) => {
    const buttons = page.locator('button');
    const count = await buttons.count();
    expect(count).toBeGreaterThanOrEqual(6);

    for (let i = 0; i < count; i++) {
      const tag = await buttons.nth(i).evaluate((el) => el.tagName.toLowerCase());
      expect(tag).toBe('button');
    }
  });
});

// ────────────────────────────────────────────────────────────────────────

test.describe('B3-1 HfbButton — Focus-Visible', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(FIXTURE);
    await page.waitForSelector(normalBtn(), { state: 'visible', timeout: 10_000 });
  });

  test('Tab navigation produces :focus-visible state on HfbButton', async ({ page }) => {
    // Focus-visible via Tab is a desktop keyboard interaction pattern.
    // Mobile browsers do not have a physical Tab key; Playwright's device
    // emulation cannot reliably simulate Tab-based focus-visible on Mobile/Tablet.
    test.skip(
      test.info().project.name.includes('Mobile') ||
        test.info().project.name.includes('Tablet'),
      'Tab → :focus-visible is desktop-only; mobile has no physical keyboard Tab',
    );

    // Tab from anchor button (first in tab order) to btn-normal.
    await page.locator('[data-testid="tab-anchor"]').focus();
    await page.keyboard.press('Tab');

    const focusedId = await page.evaluate(() => {
      const p = document.activeElement?.closest('[data-testid]');
      return p?.getAttribute('data-testid');
    });
    expect(focusedId).toBe('btn-normal');

    // After real Tab key, browser heuristic should set :focus-visible
    const matches = await page.evaluate(() =>
      document.activeElement?.matches(':focus-visible'),
    );
    expect(matches).toBe(true);
  });

  test('focus-visible produces computed outline on HfbButton after Tab', async ({ page }) => {
    test.skip(
      test.info().project.name.includes('Mobile') ||
        test.info().project.name.includes('Tablet'),
      'Tab → focus-visible is desktop-only; mobile has no physical keyboard Tab',
    );

    // Tab from anchor to btn-normal
    await page.locator('[data-testid="tab-anchor"]').focus();
    await page.keyboard.press('Tab');

    const focusedId = await page.evaluate(() => {
      const p = document.activeElement?.closest('[data-testid]');
      return p?.getAttribute('data-testid');
    });
    expect(focusedId).toBe('btn-normal');

    // After Tab, button must match :focus-visible
    const focusVisibleAfterTab = await page.locator(normalBtn()).evaluate((el) =>
      el.matches(':focus-visible'),
    );
    expect(focusVisibleAfterTab).toBe(true);

    // Computed style must show a visible outline (button.css:
    // outline: 2px solid var(--color-accent); outline-offset: 2px)
    const outlineWidth = await page.locator(normalBtn()).evaluate((el) => {
      const style = window.getComputedStyle(el);
      return style.outlineWidth;
    });
    const widthPx = parseFloat(outlineWidth);
    expect(widthPx).toBeGreaterThan(0);
  });
});

// ────────────────────────────────────────────────────────────────────────

test.describe('B3-1 HfbButton — Reduced Motion', () => {
  test('prefers-reduced-motion: reduce disables spinner animation', async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto(FIXTURE);
    await page.waitForSelector(loadingBtn(), { state: 'visible', timeout: 10_000 });

    // Verify spinner element exists
    const spinner = page.locator(loadingBtn() + ' .hfb-button__spinner');
    await expect(spinner).toBeVisible();

    // Verify computed animation-name is "none"
    const animName = await spinner.evaluate((el) => {
      const style = window.getComputedStyle(el);
      return style.animationName;
    });
    expect(animName).toBe('none');
  });
});
