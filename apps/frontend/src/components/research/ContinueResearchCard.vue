<template>
  <section class="crc-section" aria-labelledby="crc-heading">
    <h2 id="crc-heading" class="crc-heading">开始研究</h2>

    <!-- Loading -->
    <LoadingState v-if="loading" message="正在加载..." />

    <!-- Error -->
    <ErrorState
      v-else-if="error"
      :message="error"
      title="加载失败"
      @retry="$emit('retry')"
    />

    <!-- Start New Research — always shown since no resume API exists -->
    <div v-else class="crc-empty">
      <p class="crc-empty-text">
        开始新的研究工作流，系统将自动检索文献并生成证据报告。
      </p>
      <router-link
        :to="`/research/${projectId}/workflow`"
        class="crc-start-btn"
      >
        开始新研究
      </router-link>
    </div>
  </section>
</template>

<script setup lang="ts">
/**
 * ContinueResearchCard — 开始新研究入口
 *
 * There is NO resume API. The backend executes workflows synchronously —
 * runs are either fully completed or failed. No partial execution state
 * exists on the server. This component ALWAYS shows "开始新研究".
 *
 * Runs data is received from the parent page (shared, single-request).
 * This component does NOT make its own API calls.
 *
 * ref: docs/20-product/2013-research-workspace-migration.md
 */
import LoadingState from '@/components/common/LoadingState.vue';
import ErrorState from '@/components/common/ErrorState.vue';

defineProps<{
  projectId: string;
  loading?: boolean;
  error?: string | null;
}>();

defineEmits<{
  retry: [];
}>();
</script>

<style scoped>
.crc-section {
  margin-bottom: var(--space-7);
}

.crc-heading {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
  margin: 0 0 var(--space-4);
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--color-border);
}

/* Empty — no resumable run */
.crc-empty {
  padding: var(--space-6) var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  text-align: center;
}

.crc-empty-text {
  font-size: var(--text-base);
  color: var(--color-text-muted);
  margin: 0 0 var(--space-4);
}

.crc-start-btn {
  display: inline-flex;
  align-items: center;
  padding: var(--btn-padding-md);
  border-radius: var(--btn-radius);
  font-size: var(--btn-font-md);
  font-weight: var(--font-semibold);
  text-decoration: none;
  background: var(--color-accent);
  color: #fff;
  transition: background var(--transition-base);
}

.crc-start-btn:hover {
  background: var(--color-accent-hover);
}

.crc-start-btn:focus-visible {
  background: var(--color-accent-hover);
}
</style>
