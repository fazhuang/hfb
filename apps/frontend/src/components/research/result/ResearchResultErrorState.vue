<template>
  <div :class="['rre-state', variantClass]" role="alert">
    <div class="rre-icon" aria-hidden="true">{{ icon }}</div>
    <div class="rre-body">
      <h3 class="rre-title">{{ title }}</h3>
      <p class="rre-message">{{ message }}</p>
      <div v-if="showRetry" class="rre-actions">
        <router-link
          v-if="workspaceLink"
          :to="workspaceLink"
          class="rre-btn rre-btn--secondary"
        >
          返回工作区
        </router-link>
        <router-link
          v-if="workflowLink"
          :to="workflowLink"
          class="rre-btn rre-btn--secondary"
        >
          返回研究流程
        </router-link>
        <button
          v-if="retryAction"
          type="button"
          class="rre-btn rre-btn--primary"
          @click="$emit('retry')"
        >
          重试
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { ResultPageStatus } from '@/composables/useResearchResult';

const props = defineProps<{
  status: ResultPageStatus;
  message: string;
  projectId: string;
}>();

defineEmits<{
  retry: [];
}>();

interface StateView {
  title: string;
  icon: string;
  variantClass: string;
  showRetry: boolean;
  retryAction: boolean;
}

const stateView = computed((): StateView => {
  switch (props.status) {
    case 'not-found':
      return {
        title: '未找到',
        icon: '🔍',
        variantClass: 'rre-state--not-found',
        showRetry: false,
        retryAction: false,
      };
    case 'forbidden':
      return {
        title: '无权限',
        icon: '🔒',
        variantClass: 'rre-state--forbidden',
        showRetry: false,
        retryAction: false,
      };
    case 'run-pending':
      return {
        title: '运行进行中',
        icon: '⏳',
        variantClass: 'rre-state--pending',
        showRetry: true,
        retryAction: true,
      };
    case 'run-failed':
      return {
        title: '流程执行失败',
        icon: '❌',
        variantClass: 'rre-state--failed',
        showRetry: false,
        retryAction: false,
      };
    case 'report-missing':
      return {
        title: '报告缺失',
        icon: '📄',
        variantClass: 'rre-state--missing',
        showRetry: false,
        retryAction: false,
      };
    case 'error':
      return {
        title: '加载出错',
        icon: '⚠️',
        variantClass: 'rre-state--error',
        showRetry: true,
        retryAction: true,
      };
    default:
      return {
        title: '未知状态',
        icon: '❓',
        variantClass: 'rre-state--error',
        showRetry: true,
        retryAction: true,
      };
  }
});

const title = computed(() => stateView.value.title);
const icon = computed(() => stateView.value.icon);
const variantClass = computed(() => stateView.value.variantClass);
const showRetry = computed(() => stateView.value.showRetry);
const retryAction = computed(() => stateView.value.retryAction);
const message = computed(() => props.message);

const workspaceLink = computed(() => `/research/${props.projectId}/workspace`);
const workflowLink = computed(() => `/research/${props.projectId}/workflow`);
</script>

<style scoped>
.rre-state {
  display: flex;
  gap: 20px;
  padding: 40px 32px;
  border-radius: 12px;
  align-items: flex-start;
}

.rre-state--not-found {
  border: 2px solid var(--color-border, #e2e8f0);
  background: var(--color-page-bg, #fafafa);
}

.rre-state--forbidden {
  border: 2px solid #fed7d7;
  background: #fff5f5;
}

.rre-state--pending {
  border: 2px solid #fefcbf;
  background: #fffff0;
}

.rre-state--failed {
  border: 2px solid #fed7d7;
  background: #fff5f5;
}

.rre-state--missing {
  border: 2px solid #d69e2e;
  background: #fffff0;
}

.rre-state--error {
  border: 2px solid #fed7d7;
  background: #fff5f5;
}

.rre-icon {
  font-size: 36px;
  flex-shrink: 0;
}

.rre-body {
  flex: 1;
}

.rre-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--color-text-primary, #1a365d);
  margin: 0 0 8px;
}

.rre-message {
  font-size: 14px;
  color: var(--color-text-secondary, #4a5568);
  margin: 0 0 20px;
  line-height: 1.6;
}

.rre-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.rre-btn {
  display: inline-flex;
  align-items: center;
  padding: 8px 18px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  text-decoration: none;
  transition: all 0.15s;
}

.rre-btn--primary {
  border: none;
  background: var(--color-accent, #4299e1);
  color: #fff;
}

.rre-btn--primary:hover {
  background: var(--color-accent-hover, #3182ce);
}

.rre-btn--secondary {
  border: 1px solid var(--color-border, #e2e8f0);
  background: var(--color-navbar-bg, #fff);
  color: var(--color-text-secondary, #4a5568);
}

.rre-btn--secondary:hover {
  background: var(--color-hover, #edf2f7);
}
</style>
