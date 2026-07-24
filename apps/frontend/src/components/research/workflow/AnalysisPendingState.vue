<template>
  <section class="aps-step" aria-labelledby="aps-heading" aria-live="polite">
    <h2 id="aps-heading" class="aps-heading">第三步：AI 分析</h2>

    <LoadingState :message="statusMessage" />

    <p class="aps-hint">
      研究工作流正在执行中，包含文献检索、证据综合和报告生成等步骤。此过程可能需要一些时间，请耐心等待。
    </p>

    <div v-if="elapsed > 0" class="aps-elapsed">
      已等待 {{ formatElapsed }}
    </div>
  </section>
</template>

<script setup lang="ts">
/**
 * AnalysisPendingState — shows a true loading indicator while the single
 * synchronous workflow request is in-flight.
 *
 * Does NOT:
 *   - Display fake percentages
 *   - Simulate step-by-step progress
 *   - Use setInterval to infer backend step completion
 *   - Claim individual backend steps have completed based on elapsed time
 *
 * Shows:
 *   - A spinner via LoadingState
 *   - Unified status message (no per-step inference)
 *   - Real elapsed wall-clock time
 */
import { ref, computed, onBeforeUnmount, onMounted } from 'vue';
import LoadingState from '@/components/common/LoadingState.vue';

const props = withDefaults(defineProps<{
  /** Whether submission is still active */
  active?: boolean;
}>(), {
  active: true,
});

const elapsed = ref(0);
let timer: ReturnType<typeof setInterval> | null = null;

/** Single unified status message — backend is synchronous, no step-by-step progress. */
const statusMessage = '正在执行研究工作流，请稍候。';

const formatElapsed = computed(() => {
  const m = Math.floor(elapsed.value / 60);
  const s = elapsed.value % 60;
  if (m > 0) return `${m} 分 ${s} 秒`;
  return `${s} 秒`;
});

onMounted(() => {
  timer = setInterval(() => {
    if (props.active) {
      elapsed.value += 1;
    }
  }, 1000);
});

onBeforeUnmount(() => {
  if (timer) clearInterval(timer);
});
</script>

<style scoped>
.aps-step {
  padding: 0;
}

.aps-heading {
  font-size: 18px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 var(--space-4);
}

.aps-hint {
  font-size: 14px;
  color: var(--color-text-muted);
  margin: var(--space-4) 0 0;
  line-height: 1.5;
  text-align: center;
  max-width: 480px;
  margin-left: auto;
  margin-right: auto;
}

.aps-elapsed {
  margin-top: 12px;
  font-size: 13px;
  color: var(--color-text-muted);
  text-align: center;
}
</style>
