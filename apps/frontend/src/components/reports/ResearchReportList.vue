<template>
  <ul class="rrl-list" role="list" aria-label="研究报告列表">
    <ResearchReportListItem
      v-for="item in items"
      :key="item.run_id"
      :item="item"
      :exporting="exporting"
      :export-error="exportError"
      @export="$emit('export', $event)"
    />
  </ul>
</template>

<script setup lang="ts">
import type { ReportItem } from '@/composables/useResearchReports';
import ResearchReportListItem from '@/components/reports/ResearchReportListItem.vue';

defineProps<{
  items: ReportItem[];
  exporting: boolean;
  exportError: string;
}>();

defineEmits<{
  export: [item: ReportItem];
}>();
</script>

<style scoped>
.rrl-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2-5);
}
</style>
