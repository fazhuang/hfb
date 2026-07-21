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
}

.rsb-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  font-size: 11px;
  font-weight: var(--font-semibold);
  line-height: var(--leading-normal);
  white-space: nowrap;
}

.rsb-icon {
  font-size: 10px;
  font-weight: var(--font-bold);
}

/* ---- Run status colors ---- */
.rsb-run-completed {
  background: rgba(56, 161, 105, 0.12);
  color: var(--color-success-text);
}

.rsb-run-failed {
  background: rgba(197, 48, 48, 0.1);
  color: var(--color-error-light-text);
}

.rsb-run-running {
  background: rgba(49, 130, 206, 0.12);
  color: var(--color-info-text);
}

.rsb-run-pending {
  background: rgba(160, 174, 192, 0.12);
  color: var(--color-text-muted);
}

/* ---- Report status colors ---- */
.rsb-report-ready {
  background: rgba(56, 161, 105, 0.12);
  color: var(--color-success-text);
}

.rsb-report-missing {
  background: rgba(237, 137, 54, 0.12);
  color: var(--color-warning-text);
}

.rsb-report-failed {
  background: rgba(197, 48, 48, 0.1);
  color: var(--color-error-light-text);
}

.rsb-report-pending {
  background: rgba(160, 174, 192, 0.12);
  color: var(--color-text-muted);
}
</style>
