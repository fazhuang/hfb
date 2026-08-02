<template>
  <div class="hfb-table-wrapper">
    <!-- Loading state -->
    <div v-if="loading" class="hfb-table__state" role="status">
      {{ loadingMessage }}
    </div>

    <!-- Error state -->
    <div v-else-if="error" class="hfb-table__state hfb-table__state--error" role="alert">
      {{ error }}
    </div>

    <!-- Empty state -->
    <div v-else-if="rows.length === 0" class="hfb-table__state">
      {{ emptyMessage }}
    </div>

    <!-- Table -->
    <table v-else :class="tableClass">
      <thead>
        <tr>
          <th v-if="selectable" class="hfb-table__th--checkbox">
            <input
              type="checkbox"
              class="hfb-table__checkbox"
              :checked="allSelected"
              :aria-label="allSelected ? 'Deselect all rows' : 'Select all rows'"
              @change="toggleAll"
            />
          </th>
          <th
            v-for="col in columns"
            :key="col.key"
            :class="thClass(col)"
            :style="{ width: col.width, minWidth: col.minWidth }"
            :aria-sort="getAriaSort(col.key)"
            @click="sortable && col.sortable !== false ? onSort(col.key) : undefined"
          >
            {{ col.label }}
            <HfbIcon
              v-if="sortKey === col.key"
              :icon="sortDirection === 'asc' ? 'lucide:chevron-up' : 'lucide:chevron-down'"
              :size="14"
              class="hfb-table__sort-icon"
            />
          </th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="(row, idx) in rows"
          :key="rowKey?.(row, idx) ?? idx"
          :class="rowClass(row)"
          @click="clickable ? $emit('rowClick', row) : undefined"
        >
          <td v-if="selectable" class="hfb-table__td--checkbox">
            <input
              type="checkbox"
              class="hfb-table__checkbox"
              :checked="isSelected(row)"
              :aria-label="`Select row ${idx + 1}`"
              @click.stop
              @change="toggleRow(row)"
            />
          </td>
          <td v-for="col in columns" :key="col.key">
            <template v-if="col.render && htmlRender">
              <!-- eslint-disable-next-line vue/no-v-html -->
              <span v-html="col.render(row)"></span>
            </template>
            <span v-else-if="col.render">{{ col.render(row) }}</span>
            <span v-else>{{ row[col.key] ?? '—' }}</span>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import HfbIcon from './HfbIcon.vue';

export interface TableColumn {
  key: string;
  label: string;
  width?: string;
  minWidth?: string;
  sortable?: boolean;
  render?: (row: Record<string, unknown>) => string;
}

const props = withDefaults(
  defineProps<{
    columns: TableColumn[];
    rows: Record<string, unknown>[];
    loading?: boolean;
    error?: string | null;
    clickable?: boolean;
    rowKey?: (row: Record<string, unknown>, index: number) => string | number;
    /** Enhanced props */
    sortable?: boolean;
    sortKey?: string;
    sortDirection?: 'asc' | 'desc';
    selectable?: boolean;
    selectedRows?: Array<string | number>;
    striped?: boolean;
    hoverable?: boolean;
    bordered?: boolean;
    dense?: boolean;
    /**
     * Allow render() to output raw HTML. Default false for safety.
     * Enable ONLY for pre-existing consumers that return <span> badge markup.
     * New code should use text-only render() with :html-render="false".
     */
    htmlRender?: boolean;
    emptyMessage?: string;
    loadingMessage?: string;
  }>(),
  {
    hoverable: true,
    sortDirection: undefined,
    selectedRows: () => [],
    emptyMessage: 'No data',
    loadingMessage: 'Loading...',
  },
);

const emit = defineEmits<{
  rowClick: [row: Record<string, unknown>];
  sort: [key: string];
  'update:selectedRows': [rows: Array<string | number>];
  'update:sortKey': [key: string];
  'update:sortDirection': [dir: 'asc' | 'desc' | undefined];
}>();

const tableClass = computed(() =>
  [
    'hfb-table',
    props.striped ? 'hfb-table--striped' : '',
    props.hoverable ? 'hfb-table--hoverable' : '',
    props.clickable ? 'hfb-table--clickable' : '',
    props.bordered ? 'hfb-table--bordered' : '',
    props.dense ? 'hfb-table--dense' : '',
  ]
    .filter(Boolean)
    .join(' '),
);

function thClass(col: TableColumn) {
  return [
    props.sortable && col.sortable !== false ? 'hfb-table__th--sortable' : '',
    col.key === props.sortKey ? 'hfb-table__th--sorted' : '',
  ]
    .filter(Boolean)
    .join(' ');
}

function getAriaSort(key: string): 'none' | 'ascending' | 'descending' | undefined {
  if (key !== props.sortKey) return undefined;
  return props.sortDirection === 'asc' ? ('ascending' as const) : ('descending' as const);
}

function onSort(key: string) {
  if (props.sortKey === key) {
    const next =
      props.sortDirection === 'asc' ? 'desc' : props.sortDirection === 'desc' ? undefined : 'asc';
    emit('update:sortDirection', next);
    if (!next) emit('update:sortKey', '');
  } else {
    emit('update:sortKey', key);
    emit('update:sortDirection', 'asc');
  }
  emit('sort', key);
}

// Selection
const allSelected = computed(() => props.rows.length > 0 && props.rows.every((r) => isSelected(r)));

function isSelected(row: Record<string, unknown>): boolean {
  const key = getRowKey(row);
  return props.selectedRows!.includes(key);
}

function getRowKey(row: Record<string, unknown>): string | number {
  if (props.rowKey) {
    const idx = props.rows.indexOf(row);
    return props.rowKey(row, idx);
  }
  return props.rows.indexOf(row);
}

function toggleRow(row: Record<string, unknown>) {
  const key = getRowKey(row);
  const updated = isSelected(row)
    ? props.selectedRows!.filter((r) => r !== key)
    : [...props.selectedRows!, key];
  emit('update:selectedRows', updated);
}

function toggleAll() {
  if (allSelected.value) {
    emit('update:selectedRows', []);
  } else {
    emit(
      'update:selectedRows',
      props.rows.map((_r, _i) => getRowKey(_r)),
    );
  }
}

function rowClass(row: Record<string, unknown>) {
  return [isSelected(row) ? 'hfb-table__row--selected' : ''].filter(Boolean).join(' ');
}
</script>

<style scoped>
@import '../../styles/base/table.css';
</style>
