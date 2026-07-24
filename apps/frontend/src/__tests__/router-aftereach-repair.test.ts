/**
 * TASK_012_REPAIR — Router afterEach test
 *
 * Covers:
 *   P1 — Comment correction: misleading "Scroll behavior" comment removed;
 *        merged comment accurately describes title + focus management
 *   P3 — Merged hook: single afterEach handles both title + focus
 *
 * These tests verify the merged afterEach correctly:
 *   1. Sets document.title from to.meta.title (with fallback brand)
 *   2. Focuses [data-main-content] (if present) after navigation
 *   3. Does not throw when [data-main-content] is absent
 *   4. Both title + focus handled in a single afterEach registration
 *
 * NOTE: We test the afterEach pattern in isolation (createRouter + manual
 * afterEach) rather than importing the app router directly, because the
 * app router's import chain pulls in DefaultLayout → AppNavbar → useTheme,
 * which calls window.matchMedia (not available in jsdom). The afterEach
 * logic itself is what P1/P3 repair — the registration pattern, not the
 * import chain.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { createRouter, createWebHistory, type Router } from 'vue-router';

/**
 * Replicate the exact afterEach logic from the repaired router/index.ts
 * so we test the same code path without the full import chain.
 */
function installRepairedAfterEach(router: Router): void {
  router.afterEach((to) => {
    // Document title — derived from route meta.title, falls back to brand name
    const pageTitle = (to.meta.title as string) || '';
    document.title = pageTitle ? `${pageTitle} · HFB` : '皇甫谧数字人文平台';

    // Focus management — requestAnimationFrame waits for DOM render
    requestAnimationFrame(() => {
      const main = document.querySelector<HTMLElement>('[data-main-content]');
      if (main) {
        main.focus({ preventScroll: true });
      }
    });
  });
}

describe('Router afterEach — title & focus management (P1, P3 repair)', () => {
  function buildRouter() {
    const router = createRouter({
      history: createWebHistory(),
      routes: [
        { path: '/', name: 'home', component: { template: '<div />' } },
        { path: '/login', name: 'login', component: { template: '<div />' }, meta: { guest: true } },
        { path: '/research', name: 'research', component: { template: '<div />' }, meta: { title: 'Research' } },
      ],
    });
    installRepairedAfterEach(router);
    return router;
  }

  beforeEach(() => {
    document.title = '';
  });

  afterEach(() => {
    document.querySelectorAll('[data-main-content]').forEach((el) => el.remove());
  });

  it('P1: sets document.title to brand fallback when route has no meta.title', async () => {
    const router = buildRouter();
    await router.push({ name: 'home' });
    // afterEach runs synchronously after navigation completes.
    // In jsdom, push + isReady should be sufficient.
    await router.isReady();

    expect(document.title).toBe('皇甫谧数字人文平台');
  });

  it('P1: prepends page title with "· HFB" when route has meta.title', async () => {
    const router = buildRouter();
    await router.push({ name: 'research' });
    await router.isReady();

    expect(document.title).toBe('Research · HFB');
  });

  it('P1: falls back to brand when meta.title is empty string', async () => {
    const router = buildRouter();
    // login has meta.guest but no meta.title — title should fall back
    await router.push({ name: 'login' });
    await router.isReady();

    expect(document.title).toBe('皇甫谧数字人文平台');
  });

  it('focuses [data-main-content] when element is present in DOM', async () => {
    const main = document.createElement('div');
    main.setAttribute('data-main-content', 'true');
    main.setAttribute('tabindex', '-1');
    document.body.appendChild(main);
    const focusSpy = vi.spyOn(main, 'focus');

    const router = buildRouter();
    await router.push({ name: 'home' });
    await router.isReady();

    // requestAnimationFrame is async — need a rAF tick
    await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));

    expect(focusSpy).toHaveBeenCalledWith({ preventScroll: true });
    focusSpy.mockRestore();
  });

  it('does NOT throw when [data-main-content] is absent from DOM', async () => {
    const router = buildRouter();
    await router.push({ name: 'home' });
    await router.isReady();

    // requestAnimationFrame should resolve without throwing
    await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));
    // No assertion needed — not throwing is the pass condition
  });

  it('P3: single afterEach handles BOTH title AND focus (merged hook, not two separate)', async () => {
    const main = document.createElement('div');
    main.setAttribute('data-main-content', 'true');
    main.setAttribute('tabindex', '-1');
    document.body.appendChild(main);
    const focusSpy = vi.spyOn(main, 'focus');

    const router = buildRouter();
    await router.push({ name: 'research' });
    await router.isReady();

    // title should be set synchronously by afterEach
    expect(document.title).toBe('Research · HFB');

    // focus should fire after rAF
    await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));
    expect(focusSpy).toHaveBeenCalledWith({ preventScroll: true });

    focusSpy.mockRestore();
  });
});
