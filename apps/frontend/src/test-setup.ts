/**
 * Vitest global setup — jsdom polyfills.
 *
 * Injected before every test file via vitest.config.ts setupFiles.
 * `window` is available because environment: 'jsdom' initializes before setupFiles.
 * Guard in case jsdom initialization fails (CI memory pressure).
 */
import { vi } from 'vitest';

// ---- matchMedia ----
// jsdom does not implement window.matchMedia. Provide a stub that reports
// no media-query matches. Individual tests can override via vi.fn().
if (typeof window !== 'undefined') {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  });
}
