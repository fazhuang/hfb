<template>
  <section class="aps-step" aria-labelledby="aps-heading" aria-live="polite">
    <h2 id="aps-heading" class="aps-heading">第三步：AI 分析</h2>

    <LoadingState :message="statusMessage" />

    <p class="aps-hint">
      系统正在检索文献、综合证据并生成研究报告。此过程可能需要一些时间，请耐心等待。
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
 *   - Use setTimeout to create artificial delays
 *   - Claim individual backend steps have completed
 *
 * Shows:
 *   - A spinner via LoadingState
 *   - Generic status message ("正在检索文献并生成研究报告...")
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

const statusMessage = computed(() => {
  if (elapsed.value < 10) return '正在检索文献...';
  if (elapsed.value < 30) return '正在综合证据...';
  return '正在生成研究报告...';
});

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
  color: var(--color-text-primary, #1a365d);
  margin: 0 0 16px;
}

.aps-hint {
  font-size: 14px;
  color: var(--color-text-muted, #718096);
  margin: 16px 0 0;
  line-height: 1.5;
  text-align: center;
  max-width: 480px;
  margin-left: auto;
  margin-right: auto;
}

.aps-elapsed {
  margin-top: 12px;
  font-size: 13px;
  color: var(--color-text-muted, #a0aec0);
  text-align: center;
}
</style>
