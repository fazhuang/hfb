/**
 * @hfb/types — Shared TypeScript type definitions
 *
 * Common types used across frontend and backend services.
 */

// ============================================================
// API Types
// ============================================================

/** Standard API response envelope */
export interface ApiResponse<T> {
  data: T;
  meta: ApiMeta;
}

/** Pagination metadata */
export interface ApiMeta {
  page: number;
  limit: number;
  total: number;
  total_pages: number;
}

/** Generic paginated list */
export interface PaginatedList<T> {
  items: Array<T>;
  meta: ApiMeta;
}

// ============================================================
// Domain Types (Sprint 3 scope: Document, Person)
// ============================================================

/** 文献 (Document) base type */
export interface Document {
  id: string;
  title: string;
  author?: string;
  dynasty?: string;
  category?: string;
  created_at: string;
  updated_at: string;
}

/** 人物 (Person) base type */
export interface Person {
  id: string;
  name: string;
  name_zh?: string;
  dynasty?: string;
  birth_year?: number;
  death_year?: number;
}

// ============================================================
// Utility Types
// ============================================================

/** Make all properties in T deeply partial */
export type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P];
};

/** Extract the resolved value from a Promise */
export type Await<T> = T extends Promise<infer U> ? U : T;

/** Non-nullable array element */
export type NonNullableArray<T> = Array<NonNullable<T>>;
