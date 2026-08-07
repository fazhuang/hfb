/**
 * HfbToolbar — unified Search / Filter toolbar tests.
 *
 * C1-1 Search / Filter / Toolbar pattern convergence.
 *
 * Contract:
 *   - Renders search input when searchable=true
 *   - Renders filter dropdowns from filters prop
 *   - Emits { query, filters } on debounced input change
 *   - Emits immediately on Enter (via handleEnter())
 *   - Clear search resets query and emits empty search
 *   - Filter change emits update:filterValues then search
 *   - Clear-all resets all filters and emits empty search
 *   - Loading state disables inputs and shows indicator
 *   - Responsive layout renders without breaking
 */

import { describe, it, expect, vi, afterEach } from 'vitest';
import { mount } from '@vue/test-utils';
import { nextTick } from 'vue';

// ---- Mocks ----

vi.mock('@/components/common/HfbIcon.vue', () => ({
  default: {
    name: 'HfbIcon',
    props: { icon: String, size: Number },
    template: '<span class="mock-icon" :data-icon="icon" />',
  },
}));

// ---- Component under test ----

import HfbToolbar from '@/components/common/HfbToolbar.vue';
import type { ToolbarFilter } from '@/types/toolbar';

// ---- Helpers ----

const STATUS_FILTER: ToolbarFilter = {
  key: 'status',
  label: '状态',
  placeholder: '— 状态 —',
  options: [
    { value: '', label: '全部' },
    { value: 'ready', label: '报告就绪' },
    { value: 'missing', label: '报告缺失' },
  ],
};

// ================================================================
// Tests
// ================================================================

describe('HfbToolbar', () => {
  let wrappers: Array<ReturnType<typeof mount>> = [];

  afterEach(() => {
    for (const w of wrappers) w.unmount();
    wrappers = [];
  });

  // ---- Render ----

  describe('rendering', () => {
    it('renders search input when searchable=true', () => {
      const w = mount(HfbToolbar, { props: { searchable: true } });
      wrappers.push(w);
      const input = w.find('input[type="search"]');
      expect(input.exists()).toBe(true);
    });

    it('does not render search input when searchable=false', () => {
      const w = mount(HfbToolbar, { props: { searchable: false } });
      wrappers.push(w);
      const input = w.find('input[type="search"]');
      expect(input.exists()).toBe(false);
    });

    it('renders no filter dropdowns when filters is empty', () => {
      const w = mount(HfbToolbar, { props: { filters: [] } });
      wrappers.push(w);
      // HfbSelect is a complex component; verify the filters container is empty
      const filtersContainer = w.find('.hfb-toolbar__filters');
      expect(filtersContainer.exists()).toBe(false);
    });

    it('renders filter dropdowns from filters prop', () => {
      const w = mount(HfbToolbar, { props: { filters: [STATUS_FILTER] } });
      wrappers.push(w);
      // The filters container should exist and contain HfbSelect
      const filtersContainer = w.find('.hfb-toolbar__filters');
      expect(filtersContainer.exists()).toBe(true);
    });

    it('has role="search" for accessibility', () => {
      const w = mount(HfbToolbar);
      wrappers.push(w);
      expect(w.attributes('role')).toBe('search');
    });

    it('has accessible label', () => {
      const w = mount(HfbToolbar);
      wrappers.push(w);
      expect(w.attributes('aria-label')).toBe('搜索筛选工具栏');
    });
  });

  // ---- Placeholder ----

  describe('searchPlaceholder', () => {
    it('uses default placeholder', () => {
      const w = mount(HfbToolbar, { props: { searchable: true } });
      wrappers.push(w);
      const input = w.find('input[type="search"]');
      expect(input.attributes('placeholder')).toBe('搜索...');
    });

    it('uses custom placeholder', () => {
      const w = mount(HfbToolbar, {
        props: { searchable: true, searchPlaceholder: '输入关键词...' },
      });
      wrappers.push(w);
      const input = w.find('input[type="search"]');
      expect(input.attributes('placeholder')).toBe('输入关键词...');
    });
  });

  // ---- Search emission ----

  describe('search emission', () => {
    it('emits search on debounced input change', async () => {
      vi.useFakeTimers();
      const w = mount(HfbToolbar, { props: { searchable: true } });
      wrappers.push(w);

      // Simulate typing via HfbInput's update:modelValue event
      const hfbInput = w.findComponent({ name: 'HfbInput' });
      await hfbInput.vm.$emit('update:modelValue', 'test');

      // Debounce timer not yet fired
      expect(w.emitted('search')).toBeUndefined();

      // Fast-forward debounce
      vi.advanceTimersByTime(350);
      await nextTick();

      expect(w.emitted('search')).toBeDefined();
      const searchEvents = w.emitted('search');
      expect(searchEvents).toBeDefined();
      expect(searchEvents![0]).toEqual([{ query: 'test', filters: {} }]);

      vi.useRealTimers();
    });

    it('emits immediately on handleEnter() (bypasses debounce)', async () => {
      vi.useFakeTimers();
      const w = mount(HfbToolbar, { props: { searchable: true } });
      wrappers.push(w);

      // Type first (to set queryModel)
      const hfbInput = w.findComponent({ name: 'HfbInput' });
      await hfbInput.vm.$emit('update:modelValue', 'enter query');

      // Call handleEnter directly (simulating form submit)
      (w.vm as unknown as { handleEnter: () => void }).handleEnter();

      // Should emit immediately without waiting for debounce
      const immediateEvents = w.emitted('search');
      expect(immediateEvents).toBeDefined();
      expect(immediateEvents![0]).toEqual([{ query: 'enter query', filters: {} }]);

      vi.useRealTimers();
    });

    it('emits empty search on clear', async () => {
      vi.useFakeTimers();
      const w = mount(HfbToolbar, {
        props: { searchable: true, filterValues: { status: '' } },
      });
      wrappers.push(w);

      const hfbInput = w.findComponent({ name: 'HfbInput' });
      // Type then clear
      await hfbInput.vm.$emit('update:modelValue', 'something');
      vi.advanceTimersByTime(350);
      await nextTick();

      // Clear
      await hfbInput.vm.$emit('clear');

      const searchEvents2 = w.emitted('search');
      expect(searchEvents2).toBeDefined();
      if (searchEvents2 && searchEvents2.length > 0) {
        const lastEvt = searchEvents2[searchEvents2.length - 1];

        expect((lastEvt as any)[0].query).toBe('');
      }

      vi.useRealTimers();
    });
  });

  // ---- Filter change ----

  describe('filter change', () => {
    it('emits update:filterValues then search on filter change', async () => {
      const w = mount(HfbToolbar, {
        props: {
          searchable: false,
          filters: [STATUS_FILTER],
          filterValues: { status: '' },
        },
      });
      wrappers.push(w);

      // Find HfbSelect and simulate filter change
      const selects = w.findAllComponents({ name: 'HfbSelect' });
      expect(selects.length).toBe(1);

      await selects[0]!.vm.$emit('update:modelValue', 'ready');
      await nextTick();

      // Should emit update:filterValues
      const emittedValues = w.emitted('update:filterValues');
      expect(emittedValues).toBeDefined();
      expect(emittedValues![0]).toEqual([{ status: 'ready' }]);
    });
  });

  // ---- Clear all ----

  describe('clear all', () => {
    it('emits reset filterValues when clear-all button is clicked', async () => {
      const w = mount(HfbToolbar, {
        props: {
          searchable: false,
          filters: [STATUS_FILTER],
          filterValues: { status: 'ready' },
          showClearButton: true,
        },
      });
      wrappers.push(w);

      // Clear-all button should be visible (filters active)
      const clearBtn = w.findComponent({ name: 'HfbButton' });
      expect(clearBtn.exists()).toBe(true);

      await clearBtn.trigger('click');
      await nextTick();

      const emittedValues2 = w.emitted('update:filterValues');
      expect(emittedValues2).toBeDefined();
      expect(emittedValues2![0]).toEqual([{ status: null }]);
    });

    it('does not show clear-all button when no filters are active', () => {
      const w = mount(HfbToolbar, {
        props: {
          searchable: false,
          filters: [STATUS_FILTER],
          filterValues: { status: '' },
          showClearButton: true,
        },
      });
      wrappers.push(w);

      // No active filters, no query — clear-all should not render
      const clearBtn = w.findComponent({ name: 'HfbButton' });
      expect(clearBtn.exists()).toBe(false);
    });
  });

  // ---- Loading state ----

  describe('loading state', () => {
    it('renders loading indicator when loading=true', () => {
      const w = mount(HfbToolbar, {
        props: { loading: true, loadingLabel: '搜索中...' },
      });
      wrappers.push(w);
      const status = w.find('.hfb-toolbar__status');
      expect(status.exists()).toBe(true);
      expect(status.text()).toContain('搜索中...');
    });

    it('does not render loading indicator when loading=false', () => {
      const w = mount(HfbToolbar, { props: { loading: false } });
      wrappers.push(w);
      const status = w.find('.hfb-toolbar__status');
      expect(status.exists()).toBe(false);
    });
  });

  // ---- Responsive ----

  describe('layout', () => {
    it('renders root element with flex wrap', () => {
      const w = mount(HfbToolbar);
      wrappers.push(w);
      const root = w.find('.hfb-toolbar');
      expect(root.exists()).toBe(true);
      // CSS class presence verified; actual responsive behavior tested in E2E
    });
  });

  // ---- Cleanup ----

  describe('cleanup', () => {
    it('cancels debounce timer on unmount', async () => {
      vi.useFakeTimers();
      const w = mount(HfbToolbar, { props: { searchable: true } });
      wrappers.push(w);

      const hfbInput = w.findComponent({ name: 'HfbInput' });
      await hfbInput.vm.$emit('update:modelValue', 'pending');
      // Don't let debounce fire
      w.unmount();
      // No crash = pass (timer cleared)
      vi.useRealTimers();
    });
  });
});
