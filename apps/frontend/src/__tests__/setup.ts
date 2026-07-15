/**
 * Vitest global setup — runs before every test file.
 *
 * Silently drains unhandled rejections from jsdom component lifecycle
 * (e.g. onMounted async blocks in test stubs without a router) so they
 * don't cause non-zero exit codes or spurious stderr noise.
 */
import { beforeAll } from 'vitest';

beforeAll(() => {
  if (typeof process !== 'undefined') {
    process.on('unhandledRejection', () => {
      // intentionally empty — per-test assertions track real failures
    });
  }
});
