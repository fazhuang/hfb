<template>
  <li class="rrli-root" role="listitem">
    <div class="rrli-main">
      <h3 class="rrli-session-title">{{ item.session_title || '未命名研究' }}</h3>
      <p v-if="item.topic" class="rrli-topic" :title="item.topic">{{ item.topic }}</p>
      <div class="rrli-meta">
        <time :datetime="item.created_at" class="rrli-time">
          {{ formattedDate }}
        </time>
      </div>
    </div>

    <div class="rrli-badges">
      <ResearchReportStatusBadge
        :status="item.run_status"
        type="run"
      />
      <ResearchReportStatusBadge
        :status="item.report_status"
        type="report"
      />
    </div>

    <div class="rrli-actions">
      <router-link
        v-if="item.report_status === 'ready'"
        :to="`/research/${item.session_id}/result/${item.run_id}`"
        class="rrli-view-link"
      >
        查看报告
      </router-link>
      <button
        v-if="item.report_status === 'ready'"
        class="rrli-export-btn"
        :disabled="exporting"
        @click="$emit('export', item)"
      >
        {{ exportButtonLabel }}
      </button>
      <p v-if="exportErrorItem" class="rrli-export-error" role="alert">
        {{ exportErrorItem }}
      </p>
    </div>
  </li>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { ReportItem } from '@/composables/useResearchReports';
import ResearchReportStatusBadge from '@/components/reports/ResearchReportStatusBadge.vue';

const props = defineProps<{
  item: ReportItem;
  exporting: boolean;
  exportError: string;
}>();

defineEmits<{
  export: [item: ReportItem];
}>();

const formattedDate = computed(() => {
  const iso = props.item.created_at;
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return iso;
  }
});

const exportErrorItem = computed(() => {
  // Only show export error for this specific item if it matches
  return props.exportError || '';
});

const exportButtonLabel = computed(() => {
  return props.exporting ? '导出中...' : '导出';
});
</script>

<style scoped>
.rrli-root {
  padding: 14px var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  display: flex;
  align-items: flex-start;
  gap: var(--space-4);
  flex-wrap: wrap;
}

.rrli-main {
  flex: 1;
  min-width: 0;
}

.rrli-session-title {
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
  margin: 0 0 var(--space-1);
  line-height: 1.4;
}

.rrli-topic {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  margin: 0 0 6px;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rrli-meta {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.rrli-time {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  white-space: nowrap;
}

.rrli-badges {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.rrli-actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-shrink: 0;
}

.rrli-view-link {
  display: inline-flex;
  align-items: center;
  padding: 5px 14px;
  border: 1px solid var(--color-accent);
  border-radius: var(--radius-md);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--color-accent);
  text-decoration: none;
  white-space: nowrap;
  transition: all var(--transition-base);
}

.rrli-view-link:hover {
  background: var(--color-accent);
  color: #fff;
}

.rrli-view-link:focus-visible {
  background: var(--color-accent);
  color: #fff;
}

.rrli-export-btn {
  display: inline-flex;
  align-items: center;
  padding: 5px 14px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--color-text-secondary);
  background: var(--color-surface);
  cursor: pointer;
  white-space: nowrap;
  transition: all var(--transition-base);
}

.rrli-export-btn:hover:not(:disabled) {
  background: var(--color-hover);
  border-color: var(--color-text-muted);
}

.rrli-export-btn:focus-visible:not(:disabled) {
  background: var(--color-hover);
  border-color: var(--color-text-muted);
}

.rrli-export-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.rrli-export-error {
  margin: 0;
  font-size: 11px;
  color: var(--color-error-text);
}

/* ---- Responsive ---- */
@media (max-width: 768px) {
  .rrli-root {
    flex-direction: column;
    gap: var(--space-3);
  }

  .rrli-actions {
    width: 100%;
    justify-content: flex-end;
  }
}
</style>
