<template>
  <!--
    DataTable — backward-compatible alias for HfbTable.
    Preserves the same props/emits/slots API for existing consumers.
    New code should import HfbTable directly.
  -->
  <HfbTable
    :columns="columns"
    :rows="rows"
    :loading="loading"
    :error="error"
    :clickable="clickable"
    :row-key="rowKey"
    @row-click="$emit('rowClick', $event)"
  />
</template>

<script lang="ts">
export type { TableColumn } from './HfbTable.vue';
</script>

<script setup lang="ts">
import HfbTable from './HfbTable.vue';
import type { TableColumn } from './HfbTable.vue';

defineProps<{
  columns: TableColumn[];
  rows: Record<string, unknown>[];
  loading?: boolean;
  error?: string | null;
  clickable?: boolean;
  rowKey?: (row: Record<string, unknown>, index: number) => string;
}>();

defineEmits<{
  rowClick: [row: Record<string, unknown>];
}>();
</script>
