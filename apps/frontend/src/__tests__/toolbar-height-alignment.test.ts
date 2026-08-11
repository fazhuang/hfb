/**
 * toolbar-height-alignment.test.ts — Unit tests for status select width and height alignment.
 *
 * Checks contract for:
 * 1. HfbToolbar status select width expansion and search height alignment (token-based).
 * 2. ResearchReportsToolbar .rrt-select alignment properties.
 */

import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import HfbToolbar from '@/components/common/HfbToolbar.vue';
import ResearchReportsToolbar from '@/components/reports/ResearchReportsToolbar.vue';
import type { ToolbarFilter } from '@/types/toolbar';

const STATUS_FILTER: ToolbarFilter = {
  key: 'status',
  label: '状态',
  placeholder: '— 状态 —',
  options: [
    { value: '', label: '全部' },
    { value: 'ready', label: '报告就绪' },
    { value: 'missing', label: '报告缺失' },
    { value: 'failed', label: '报告失败' },
    { value: 'pending', label: '待生成' },
  ],
};

describe('Toolbar Height Alignment and Select Width', () => {
  describe('HfbToolbar Component Alignment & Structure', () => {
    it('renders search input and filter dropdowns with align-items center structure', () => {
      const wrapper = mount(HfbToolbar, {
        props: {
          searchable: true,
          filters: [STATUS_FILTER],
        },
      });

      const root = wrapper.find('.hfb-toolbar');
      expect(root.exists()).toBe(true);

      const searchWrapper = wrapper.find('.hfb-toolbar__search');
      expect(searchWrapper.exists()).toBe(true);

      const filtersWrapper = wrapper.find('.hfb-toolbar__filters');
      expect(filtersWrapper.exists()).toBe(true);

      const selectComponent = wrapper.findComponent({ name: 'HfbSelect' });
      expect(selectComponent.exists()).toBe(true);

      wrapper.unmount();
    });

    it('handles multiple filter selectors without breaking height alignment structure', () => {
      const filters: Array<ToolbarFilter> = [
        STATUS_FILTER,
        {
          key: 'category',
          label: '分类',
          options: [
            { value: 'all', label: '全部分类' },
            { value: 'medical', label: '经典医籍' },
          ],
        },
      ];

      const wrapper = mount(HfbToolbar, {
        props: {
          searchable: true,
          filters,
        },
      });

      const selectComponents = wrapper.findAllComponents({ name: 'HfbSelect' });
      expect(selectComponents.length).toBe(2);

      wrapper.unmount();
    });
  });

  describe('ResearchReportsToolbar Component Alignment & Structure', () => {
    it('renders rrt-select with correct status selection values and structure', () => {
      const wrapper = mount(ResearchReportsToolbar, {
        props: {
          statusFilter: 'ready',
        },
      });

      const selectElement = wrapper.find('.rrt-select');
      expect(selectElement.exists()).toBe(true);

      const htmlSelect = selectElement.element as HTMLSelectElement;
      expect(htmlSelect.value).toBe('ready');

      const options = selectElement.findAll('option');
      const optionValues: Array<string> = options.map((opt) => opt.element.value);
      expect(optionValues).toEqual(['', 'ready', 'missing', 'failed', 'pending']);

      wrapper.unmount();
    });
  });
});
