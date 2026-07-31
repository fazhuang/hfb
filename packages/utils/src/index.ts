/**
 * @hfb/utils — Shared Utility Functions
 *
 * Common utilities used across frontend and backend.
 */

/**
 * Delay execution for a given number of milliseconds.
 */
export function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Generate a random ID (crypto-safe when available).
 */
export function generateId(length: number = 21): string {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
  const randomValues =
    typeof crypto !== 'undefined'
      ? crypto.getRandomValues(new Uint8Array(length))
      : Array.from({ length }, () => Math.floor(Math.random() * 256));
  return Array.from(randomValues, (v) => chars[v % chars.length]!).join('');
}

export {};
