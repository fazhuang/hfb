/**
 * fetchWithRetry — cancellable GET retry helper.
 *
 * Only retries on network/5xx/timeout. Never retries 4xx.
 * AbortController support: cancelling aborts in-flight request and stops
 * pending retries.
 *
 * C2-1C: created for session gate and section retry.
 */
import api from '@/api/client';
import type { AxiosResponse } from 'axios';

export interface RetryOptions {
  maxRetries?: number;
  delays?: Array<number>;
  signal?: AbortSignal;
}

type ErrorLike = {
  code?: string;
  name?: string;
  response?: { status?: number };
};

function errCode(e: unknown): string | undefined {
  return (e as ErrorLike).code;
}

function errName(e: unknown): string | undefined {
  return (e as ErrorLike).name;
}

function errStatus(e: unknown): number | undefined {
  return (e as ErrorLike).response?.status;
}

function isAbort(e: unknown): boolean {
  return errCode(e) === 'ERR_CANCELED' || errName(e) === 'AbortError';
}

export async function fetchWithRetry<T = unknown>(
  url: string,
  params?: Record<string, unknown>,
  options?: RetryOptions,
): Promise<AxiosResponse<T>> {
  const maxRetries = options?.maxRetries ?? 3;
  const delays = options?.delays ?? [1000, 2000, 4000];
  const signal = options?.signal;

  let lastError: unknown;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    // Check cancellation before each attempt
    if (signal?.aborted) {
      throw new DOMException('cancelled', 'AbortError');
    }

    try {
      const res = await api.get<T>(url, {
        params,
        signal,
      });

      // 4xx is client error — do not retry
      const status = res.status;
      if (status >= 400 && status < 500) {
        return res;
      }

      return res;
    } catch (e: unknown) {
      lastError = e;

      // AbortError — stop immediately, do not retry
      if (isAbort(e)) {
        throw e;
      }

      // 4xx — do not retry
      const status = errStatus(e);
      if (status && status >= 400 && status < 500) {
        throw e;
      }

      // Last attempt or no more delays — throw
      if (attempt >= maxRetries) {
        throw e;
      }

      // Wait before retry, with cancellation check
      const delay: number = delays[attempt] ?? delays[delays.length - 1] ?? 0;
      if (delay > 0) {
        try {
          await new Promise<void>((resolve, reject) => {
            const timer = setTimeout(resolve, delay);
            if (signal) {
              signal.addEventListener(
                'abort',
                () => {
                  clearTimeout(timer);
                  reject(new DOMException('cancelled', 'AbortError'));
                },
                { once: true },
              );
            }
          });
        } catch (waitErr: unknown) {
          if (errName(waitErr) === 'AbortError') {
            throw waitErr;
          }
          throw e;
        }
      }
    }
  }

  throw lastError;
}
