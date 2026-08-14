<template>
  <div :class="['rre-state', variantClass]" role="alert">
    <HfbIcon :icon="icon" :size="36" class="rre-icon" />
    <div class="rre-body">
      <h3 class="rre-title">{{ title }}</h3>
      <p class="rre-message">{{ message }}</p>
      <div v-if="showRetry" class="rre-actions">
        <router-link v-if="workspaceLink" :to="workspaceLink" class="rre-btn rre-btn--secondary">
          返回工作区
        </router-link>
        <router-link v-if="workflowLink" :to="workflowLink" class="rre-btn rre-btn--secondary">
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
import HfbIcon from '@/components/common/HfbIcon.vue';
import type { LucideIconName } from '@/components/common/HfbIcon.vue';

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
  icon: LucideIconName;
  variantClass: string;
  showRetry: boolean;
  retryAction: boolean;
}

const stateView = computed((): StateView => {
  switch (props.status) {
    case 'not-found':
      return {
        title: '未找到',
        icon: 'search',
        variantClass: 'rre-state--not-found',
        showRetry: false,
        retryAction: false,
      };
    case 'forbidden':
      return {
        title: '无权限',
        icon: 'lock',
        variantClass: 'rre-state--forbidden',
        showRetry: false,
        retryAction: false,
      };
    case 'run-pending':
      return {
        title: '运行进行中',
        icon: 'circle-alert',
        variantClass: 'rre-state--pending',
        showRetry: true,
        retryAction: true,
      };
    case 'run-failed':
      return {
        title: '流程执行失败',
        icon: 'x-circle',
        variantClass: 'rre-state--failed',
        showRetry: false,
        retryAction: false,
      };
    case 'report-pending':
      return {
        title: '报告生成中',
        icon: 'pen-line',
        variantClass: 'rre-state--pending',
        showRetry: true,
        retryAction: true,
      };
    case 'report-failed':
      return {
        title: '报告生成失败',
        icon: 'file-text',
        variantClass: 'rre-state--failed',
        showRetry: false,
        retryAction: false,
      };
    case 'report-missing':
      return {
        title: '报告缺失',
        icon: 'file-text',
        variantClass: 'rre-state--missing',
        showRetry: false,
        retryAction: false,
      };
    case 'error':
      return {
        title: '加载出错',
        icon: 'triangle-alert',
        variantClass: 'rre-state--error',
        showRetry: true,
        retryAction: true,
      };
    default:
      return {
        title: '未知状态',
        icon: 'circle-alert',
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
  gap: var(--space-5);
  padding: var(--space-10) 32px;
  border-radius: var(--radius-2xl);
  align-items: flex-start;
  max-width: 100%;
  box-sizing: border-box;
  flex-shrink: 0;
}

.rre-state--not-found {
  border: 2px solid var(--color-border);
  background: var(--color-page-bg);
}

.rre-state--forbidden {
  border: 2px solid var(--color-error-icon-bg);
  background: var(--color-error-bg);
}

.rre-state--pending {
  border: 2px solid var(--color-warning-bg);
  background: var(--color-warning-bg);
}

.rre-state--failed {
  border: 2px solid var(--color-error-icon-bg);
  background: var(--color-error-bg);
}

.rre-state--missing {
  border: 2px solid var(--color-warning);
  background: var(--color-warning-bg);
}

.rre-state--error {
  border: 2px solid var(--color-error-icon-bg);
  background: var(--color-error-bg);
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
  color: var(--color-text-primary);
  margin: 0 0 var(--space-2);
}

.rre-message {
  font-size: 14px;
  color: var(--color-text-secondary);
  margin: 0 0 var(--space-5);
  line-height: 1.6;
}

.rre-actions {
  display: flex;
  gap: var(--space-2-5);
  flex-wrap: wrap;
}

.rre-btn {
  display: inline-flex;
  align-items: center;
  padding: var(--space-2) 18px;
  border-radius: var(--radius-lg);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  text-decoration: none;
  transition: all var(--transition-base);
}

.rre-btn--primary {
  border: none;
  background: var(--color-accent);
  color: var(--color-surface);
}

.rre-btn--primary:hover {
  background: var(--color-accent-hover, var(--color-info));
}

.rre-btn--primary:focus-visible {
  background: var(--color-accent-hover, var(--color-info));
}

.rre-btn--secondary {
  border: 1px solid var(--color-border);
  background: var(--color-navbar-bg, var(--color-surface));
  color: var(--color-text-secondary);
}

.rre-btn--secondary:hover {
  background: var(--color-hover);
}

.rre-btn--secondary:focus-visible {
  background: var(--color-hover);
}
</style>
