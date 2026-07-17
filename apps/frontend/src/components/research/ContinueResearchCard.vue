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
  margin-bottom: 28px;
}

.crc-heading {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text-primary, #1a365d);
  margin: 0 0 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--color-border, #e2e8f0);
}

/* Empty — no resumable run */
.crc-empty {
  padding: 24px 16px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 8px;
  background: var(--color-navbar-bg, #fff);
  text-align: center;
}

.crc-empty-text {
  font-size: 14px;
  color: var(--color-text-muted, #718096);
  margin: 0 0 16px;
}

.crc-start-btn {
  display: inline-flex;
  align-items: center;
  padding: 8px 20px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  text-decoration: none;
  background: var(--color-accent, #4299e1);
  color: #fff;
  transition: background 0.15s;
}

.crc-start-btn:hover {
  background: var(--color-accent-hover, #3182ce);
}
</style>
