/**
 * HfbToolbar — unified Search / Filter toolbar types.
 *
 * Part of C1-1: Search / Filter / Toolbar pattern convergence.
 */

import type { HfbSelectOption } from '@/components/common/HfbSelect.vue';

/** Definition of a single filter dropdown in the toolbar. */
export interface ToolbarFilter {
  /** Unique key for this filter (used as key in filterValues record). */
  key: string;
  /** Visible label for the filter (used as HfbSelect label). */
  label: string;
  /** Options for the dropdown. */
  options: HfbSelectOption[];
  /** Placeholder text when no value is selected. */
  placeholder?: string;
}

/** Payload emitted on search (Enter or debounced input). */
export interface ToolbarSearchPayload {
  /** Current trimmed search query. */
  query: string;
  /** Current filter values keyed by filter.key. */
  filters: Record<string, string | number | null>;
}

/** Default empty filter values record. */
export type ToolbarFilterValues = Record<string, string | number | null>;
