<template>
  <nav class="hfb-pagination" role="navigation" aria-label="Pagination">
    <!-- Prev -->
    <button
      class="hfb-pagination__btn"
      :disabled="page <= 1 || disabled"
      aria-label="Previous page"
      @click="$emit('update:page', page - 1)"
    >
      ‹
    </button>

    <!-- Page buttons -->
    <button
      v-for="p in visiblePages"
      :key="p"
      :class="['hfb-pagination__btn', p === page ? 'hfb-pagination__btn--active' : '']"
      :disabled="disabled"
      :aria-current="p === page ? 'page' : undefined"
      :aria-label="`Page ${p}`"
      @click="$emit('update:page', p)"
    >
      {{ p }}
    </button>

    <!-- Next -->
    <button
      class="hfb-pagination__btn"
      :disabled="page >= totalPages || disabled"
      aria-label="Next page"
      @click="$emit('update:page', page + 1)"
    >
      ›
    </button>
  </nav>
</template>

<script setup lang="ts">
import { computed } from 'vue';

const props = withDefaults(defineProps<{
  page: number;
  totalPages: number;
  disabled?: boolean;
}>(), {
  disabled: false,
});

defineEmits<{
  'update:page': [page: number];
}>();

const visiblePages = computed(() => {
  const total = props.totalPages;
  const current = props.page;
  const pages: number[] = [];

  if (total <= 7) {
    for (let i = 1; i <= total; i++) pages.push(i);
  } else {
    // Always show first page
    pages.push(1);

    if (current > 3) pages.push(-1); // ellipsis

    // Pages around current
    const start = Math.max(2, current - 1);
    const end = Math.min(total - 1, current + 1);
    for (let i = start; i <= end; i++) pages.push(i);

    if (current < total - 2) pages.push(-1); // ellipsis

    // Always show last page
    pages.push(total);
  }

  return pages;
});
</script>

<style scoped>
@import '../../styles/base/pagination.css';
</style>
