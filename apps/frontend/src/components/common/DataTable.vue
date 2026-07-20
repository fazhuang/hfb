<template>
  <div class="data-table-wrapper">
    <div v-if="loading" class="table-state">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="table-state table-state--error">{{ error }}</div>
    <div v-else-if="rows.length === 0" class="table-state">{{ t('common.noData') }}</div>
    <table v-else class="data-table">
      <thead>
        <tr>
          <th v-for="col in columns" :key="col.key" :style="{ width: col.width }">{{ col.label }}</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="(row, idx) in rows"
          :key="rowKey?.(row, idx) ?? idx"
          :class="{ clickable: !!clickable }"
          @click="clickable ? $emit('rowClick', row) : undefined"
        >
          <td v-for="col in columns" :key="col.key">
            <span v-if="col.render" v-html="col.render(row)"></span>
            <span v-else>{{ row[col.key] ?? '—' }}</span>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n';

const { t } = useI18n();

export interface TableColumn {
  key: string;
  label: string;
  width?: string;
  render?: (row: Record<string, unknown>) => string;
}

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

<style scoped>
.data-table-wrapper {
  width: 100%;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--text-base);
}

.data-table th {
  text-align: left;
  padding: 10px var(--space-3);
  font-weight: var(--font-semibold);
  color: var(--color-text-secondary);
  border-bottom: 2px solid var(--color-border);
  white-space: nowrap;
}

.data-table td {
  padding: 10px var(--space-3);
  border-bottom: 1px solid var(--color-border);
  color: var(--color-text-primary);
  max-width: 320px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.data-table tbody tr.clickable {
  cursor: pointer;
  transition: background var(--transition-fast);
}

.data-table tbody tr.clickable:hover {
  background: var(--color-hover);
}

.table-state {
  text-align: center;
  padding: var(--space-10) var(--space-4);
  color: var(--color-text-muted);
  font-size: var(--text-base);
}

.table-state--error {
  color: var(--color-error-text);
}
</style>
