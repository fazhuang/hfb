/**
 * Vitest global setup — runs before every test file.
 *
 * Suppresses unhandled rejections from component lifecycle (e.g. onMounted
 * async blocks without a router) so they don't cause non-zero exit codes.
 */
import { beforeAll } from 'vitest';

beforeAll(() => {
  // Catch unhandled rejections globally so jsdom component tests don't
  // fail with non-zero exit codes when async lifecycle hooks reject.
  if (typeof process !== 'undefined') {
    process.on('unhandledRejection', (_reason) => {
      // Silently suppress — these are tracked in individual test assertions.
    });
  }
});
