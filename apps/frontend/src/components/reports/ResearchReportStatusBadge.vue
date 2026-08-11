<template>
  <div class="rsb-root" role="status" :aria-label="`报告状态: ${label}`">
    <span class="rsb-badge" :class="badgeClass">
      <span class="rsb-icon" aria-hidden="true">{{ statusIcon }}</span>
      {{ label }}
    </span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';

const props = withDefaults(
  defineProps<{
    status: string;
    type: 'run' | 'report';
  }>(),
  {},
);

const RUN_LABELS: Record<string, string> = {
  completed: '已完成',
  failed: '失败',
  running: '运行中',
  pending: '待处理',
};

const REPORT_LABELS: Record<string, string> = {
  ready: '报告就绪',
  missing: '报告缺失',
  failed: '报告失败',
  pending: '待生成',
};

const STATUS_ICONS: Record<string, string> = {
  completed: '✓',
  ready: '✓',
  running: '↻',
  failed: '✗',
  missing: '—',
  pending: '○',
};

const label = computed(() => {
  const map = props.type === 'run' ? RUN_LABELS : REPORT_LABELS;
  return map[props.status] || props.status;
});

const statusIcon = computed(() => STATUS_ICONS[props.status] || '');

const badgeClass = computed(() => {
  const prefix = props.type === 'run' ? 'rsb-run-' : 'rsb-report-';
  return `${prefix}${props.status}`;
});
</script>

<style scoped>
.rsb-root {
  display: inline-flex;
  align-items: center;
  flex-shrink: 0;
}

.rsb-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-1);
  padding: var(--space-0-5) var(--space-2);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  line-height: 1.2;
  white-space: nowrap;
  flex-shrink: 0;
  height: fit-content;
  align-self: center;
}

.rsb-icon {
  font-size: var(--text-xs);
  font-weight: var(--font-bold);
  flex-shrink: 0;
  line-height: 1;
  margin-right: 2px;
}

/* ---- Run status colors ---- */
.rsb-run-completed {
  background: var(--color-success-bg);
  color: var(--color-success-text);
}

.rsb-run-failed {
  background: var(--color-error-bg);
  color: var(--color-error-light-text);
}

.rsb-run-running {
  background: var(--color-info-bg);
  color: var(--color-info-text);
}

.rsb-run-pending {
  background: var(--color-tag-bg);
  color: var(--color-text-muted);
}

/* ---- Report status colors ---- */
.rsb-report-ready {
  background: var(--color-success-bg);
  color: var(--color-success-text);
}

.rsb-report-missing {
  background: var(--color-warning-bg);
  color: var(--color-warning-text);
}

.rsb-report-failed {
  background: var(--color-error-bg);
  color: var(--color-error-light-text);
}

.rsb-report-pending {
  background: var(--color-tag-bg);
  color: var(--color-text-muted);
}
</style>
