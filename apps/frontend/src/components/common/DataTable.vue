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
  font-size: 14px;
}

.data-table th {
  text-align: left;
  padding: 10px 12px;
  font-weight: 600;
  color: var(--color-text-secondary, #4a5568);
  border-bottom: 2px solid var(--color-border, #e2e8f0);
  white-space: nowrap;
}

.data-table td {
  padding: 10px 12px;
  border-bottom: 1px solid var(--color-border, #e2e8f0);
  color: var(--color-text-primary, #1a365d);
  max-width: 320px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.data-table tbody tr.clickable {
  cursor: pointer;
  transition: background 0.1s;
}

.data-table tbody tr.clickable:hover {
  background: var(--color-hover, #edf2f7);
}

.table-state {
  text-align: center;
  padding: 40px 16px;
  color: var(--color-text-muted, #a0aec0);
  font-size: 14px;
}

.table-state--error {
  color: var(--color-error-text, #c53030);
}
</style>
