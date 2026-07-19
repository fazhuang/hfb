<template>
  <li class="rrli-root" role="listitem">
    <div class="rrli-main">
      <h3 class="rrli-session-title">{{ item.session_title || '未命名研究' }}</h3>
      <p v-if="item.topic" class="rrli-topic">{{ item.topic }}</p>
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
  padding: 14px 16px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 8px;
  background: var(--color-navbar-bg, #fff);
  display: flex;
  align-items: flex-start;
  gap: 16px;
  flex-wrap: wrap;
}

.rrli-main {
  flex: 1;
  min-width: 0;
}

.rrli-session-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary, #1a365d);
  margin: 0 0 4px;
  line-height: 1.4;
}

.rrli-topic {
  font-size: 13px;
  color: var(--color-text-secondary, #4a5568);
  margin: 0 0 6px;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rrli-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.rrli-time {
  font-size: 12px;
  color: var(--color-text-muted, #a0aec0);
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
  gap: 8px;
  flex-shrink: 0;
}

.rrli-view-link {
  display: inline-flex;
  align-items: center;
  padding: 5px 14px;
  border: 1px solid var(--color-accent, #2b6cb0);
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  color: var(--color-accent, #2b6cb0);
  text-decoration: none;
  white-space: nowrap;
  transition: all 0.15s;
}

.rrli-view-link:hover {
  background: var(--color-accent, #2b6cb0);
  color: #fff;
}

.rrli-export-btn {
  display: inline-flex;
  align-items: center;
  padding: 5px 14px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-secondary, #4a5568);
  background: var(--color-navbar-bg, #fff);
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.15s;
}

.rrli-export-btn:hover:not(:disabled) {
  background: var(--color-hover, #edf2f7);
  border-color: var(--color-text-muted, #a0aec0);
}

.rrli-export-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.rrli-export-error {
  margin: 0;
  font-size: 11px;
  color: var(--color-error-text, #c53030);
}

/* ---- Responsive ---- */
@media (max-width: 768px) {
  .rrli-root {
    flex-direction: column;
    gap: 10px;
  }

  .rrli-actions {
    width: 100%;
    justify-content: flex-end;
  }
}
</style>
