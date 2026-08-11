/**
 * Unit tests for report status badges and layout deformity fixes
 *
 * Covers:
 *   1. ResearchReportStatusBadge rendering root, badge, icon elements and status classes
 *   2. ResearchRunSummary status badge (.rrs-status) and step badges (.rrs-step-badge)
 *   3. ResearchReportListItem meta container (.rrli-meta) holding badges
 *   4. ProjectReports step badges (.pr-step-badge) rendering
 *   5. ResearchResultErrorState (.rre-state) error state container
 */

import { describe, it, expect, vi } from 'vitest';
import { mount } from '@vue/test-utils';
import ResearchReportStatusBadge from '@/components/reports/ResearchReportStatusBadge.vue';
import ResearchRunSummary from '@/components/research/result/ResearchRunSummary.vue';
import ResearchReportListItem from '@/components/reports/ResearchReportListItem.vue';
import ProjectReports from '@/components/research/ProjectReports.vue';
import ResearchResultErrorState from '@/components/research/result/ResearchResultErrorState.vue';

// Mock API client for components that make network requests
const mockApiGet = vi.fn();
vi.mock('@/api/client', () => ({
  default: {
    get: (...args: Array<unknown>) => mockApiGet(...args),
  },
}));

describe('Report Status Badges and Container Deformity Repairs', () => {
  describe('ResearchReportStatusBadge.vue', () => {
    it('renders rsb-root, rsb-badge and rsb-icon with run status labels', () => {
      const wrapper = mount(ResearchReportStatusBadge, {
        props: {
          status: 'completed',
          type: 'run',
        },
      });

      expect(wrapper.find('.rsb-root').exists()).toBe(true);
      expect(wrapper.find('.rsb-badge').exists()).toBe(true);
      expect(wrapper.find('.rsb-badge').classes()).toContain('rsb-run-completed');
      expect(wrapper.find('.rsb-icon').exists()).toBe(true);
      expect(wrapper.find('.rsb-icon').text()).toBe('✓');
      expect(wrapper.text()).toContain('已完成');
    });

    it('renders report status badges with ready label', () => {
      const wrapper = mount(ResearchReportStatusBadge, {
        props: {
          status: 'ready',
          type: 'report',
        },
      });

      expect(wrapper.find('.rsb-badge').classes()).toContain('rsb-report-ready');
      expect(wrapper.find('.rsb-icon').text()).toBe('✓');
      expect(wrapper.text()).toContain('报告就绪');
    });

    it('renders fallback label and icon for unknown status', () => {
      const wrapper = mount(ResearchReportStatusBadge, {
        props: {
          status: 'unknown_status',
          type: 'run',
        },
      });

      expect(wrapper.find('.rsb-badge').classes()).toContain('rsb-run-unknown_status');
      expect(wrapper.find('.rsb-icon').text()).toBe('');
      expect(wrapper.text()).toContain('unknown_status');
    });
  });

  describe('ResearchRunSummary.vue', () => {
    it('renders rrs-status and rrs-step-badge elements properly', () => {
      const runData = {
        run_id: 'run-1234567890abcdef',
        step_execution_trace: [
          { name: 'topic_selection', status: 'completed' },
          { name: 'literature_retrieval', status: 'completed' },
        ],
      };

      const wrapper = mount(ResearchRunSummary, {
        props: {
          run: runData,
          report: null,
        },
      });

      const statusBadge = wrapper.find('.rrs-status');
      expect(statusBadge.exists()).toBe(true);
      expect(statusBadge.classes()).toContain('rrs-status--completed');
      expect(statusBadge.text()).toBe('已完成');

      const stepBadges = wrapper.findAll('.rrs-step-badge');
      expect(stepBadges.length).toBe(2);
      const firstStep = stepBadges[0];
      if (!firstStep) throw new Error('No step badge found');
      expect(firstStep.classes()).toContain('rrs-step-badge--completed');
      expect(firstStep.text()).toBe('主题选择');
    });

    it('shows failed status when steps fail', () => {
      const runData = {
        run_id: 'run-987654321',
        step_execution_trace: [
          { name: 'topic_selection', status: 'completed' },
          { name: 'literature_retrieval', status: 'failed' },
        ],
      };

      const wrapper = mount(ResearchRunSummary, {
        props: {
          run: runData,
          report: null,
        },
      });

      const statusBadge = wrapper.find('.rrs-status');
      expect(statusBadge.classes()).toContain('rrs-status--failed');
      expect(statusBadge.text()).toBe('失败');
    });
  });

  describe('ResearchReportListItem.vue', () => {
    it('renders rrli-meta container with status badges', () => {
      const item = {
        session_id: 'session-1',
        session_title: 'Title',
        run_id: 'run-1',
        topic: 'Topic',
        run_status: 'completed',
        report_status: 'ready',
        created_at: '2026-08-01T00:00:00Z',
        completed_at: '2026-08-01T00:01:00Z',
        workflow_type: 'full_research_flow',
      };

      const wrapper = mount(ResearchReportListItem, {
        props: {
          item,
          exporting: false,
          exportError: '',
        },
        global: {
          stubs: {
            RouterLink: true,
          },
        },
      });

      const meta = wrapper.find('.rrli-meta');
      expect(meta.exists()).toBe(true);
      const badges = meta.findAllComponents(ResearchReportStatusBadge);
      expect(badges.length).toBe(2);
    });
  });

  describe('ProjectReports.vue', () => {
    it('renders pr-step-badge elements for reports step trace', async () => {
      mockApiGet.mockResolvedValueOnce({
        data: {
          data: {
            runs: [
              {
                run_id: 'run-1',
                topic: 'Report Title',
                started_at: '2026-08-01T00:00:00Z',
                completed_at: '2026-08-01T00:01:00Z',
                step_execution_trace: [
                  { name: 'topic_selection', status: 'completed' },
                  { name: 'evidence_synthesis', status: 'pending' },
                ],
              },
            ],
          },
        },
      });

      const wrapper = mount(ProjectReports, {
        props: {
          projectId: 'project-1',
        },
        global: {
          stubs: {
            RouterLink: true,
          },
        },
      });

      // Wait for fetchReports async call
      await new Promise((resolve) => setTimeout(resolve, 10));

      const stepBadges = wrapper.findAll('.pr-step-badge');
      expect(stepBadges.length).toBe(2);
      const prStep0 = stepBadges[0];
      const prStep1 = stepBadges[1];
      if (!prStep0 || !prStep1) throw new Error('Missing project step badge');
      expect(prStep0.classes()).toContain('pr-step--completed');
      expect(prStep0.text()).toBe('选题');
      expect(prStep1.classes()).toContain('pr-step--pending');
      expect(prStep1.text()).toBe('证据综合');
    });
  });

  describe('ResearchResultErrorState.vue', () => {
    it('renders rre-state container with appropriate variant classes', () => {
      const wrapper = mount(ResearchResultErrorState, {
        props: {
          status: 'run-failed',
          message: 'Process failed to complete',
          projectId: 'project-100',
        },
        global: {
          stubs: {
            RouterLink: true,
          },
        },
      });

      const container = wrapper.find('.rre-state');
      expect(container.exists()).toBe(true);
      expect(container.classes()).toContain('rre-state--failed');
      expect(wrapper.find('.rre-title').text()).toBe('流程执行失败');
      expect(wrapper.find('.rre-message').text()).toBe('Process failed to complete');
    });
  });
});
