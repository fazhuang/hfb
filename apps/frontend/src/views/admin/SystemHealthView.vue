<template>
  <div class="system-health-view">
    <div class="page-header">
      <div class="header-content">
        <h1 class="page-title">系统健康诊断 (Infrastructure Diagnostics)</h1>
        <p class="page-subtitle">管理员层级全量基础设施服务运行状态与延迟开销监控</p>
      </div>
      <button class="btn-refresh" :disabled="loading" @click="loadHealthDetails">
        <span v-if="loading" class="spin-icon">↻</span>
        <span v-else>↻ 刷新诊断</span>
      </button>
    </div>

    <!-- Error State -->
    <div v-if="errorMessage" class="error-banner">
      <HfbIcon icon="triangle-alert" :size="18" class="error-icon" />
      <span class="error-text">{{ errorMessage }}</span>
    </div>

    <!-- Overview Card -->
    <div class="overview-card" :class="{ 'is-healthy': isOverallHealthy, 'is-unhealthy': !isOverallHealthy }">
      <div class="overview-header">
        <div class="status-indicator">
          <span class="status-dot" :class="isOverallHealthy ? 'dot-success' : 'dot-danger'"></span>
          <span class="status-title">
            {{ isOverallHealthy ? '整体基础设施运行正常' : '基础设施存在异常服务' }}
          </span>
        </div>
        <span class="readiness-badge" :class="isReady ? 'badge-ready' : 'badge-not-ready'">
          {{ isReady ? 'Ready Probe: OK (200)' : 'Ready Probe: Failed (503)' }}
        </span>
      </div>
      <div class="overview-meta">
        <div class="meta-item">
          <span class="meta-label">诊断服务总数</span>
          <span class="meta-value">{{ servicesList.length }}</span>
        </div>
        <div class="meta-item">
          <span class="meta-label">健康服务数量</span>
          <span class="meta-value text-success">{{ healthyCount }}</span>
        </div>
        <div class="meta-item">
          <span class="meta-label">异常服务数量</span>
          <span class="meta-value text-error">{{ unhealthyCount }}</span>
        </div>
        <div class="meta-item">
          <span class="meta-label">最后更新时间</span>
          <span class="meta-value">{{ formattedLastChecked }}</span>
        </div>
      </div>
    </div>

    <!-- Loading Skeleton -->
    <div v-if="loading && servicesList.length === 0" class="skeleton-grid">
      <div v-for="i in 4" :key="i" class="card-skeleton"></div>
    </div>

    <!-- Service Diagnostic Cards Grid -->
    <div v-else class="services-grid">
      <div
        v-for="svc in servicesList"
        :key="svc.name"
        class="service-card"
        :class="{ 'card-healthy': svc.healthy, 'card-unhealthy': !svc.healthy }"
      >
        <div class="card-header">
          <div class="service-name-group">
            <HfbIcon :icon="getServiceIcon(svc.name)" :size="20" class="service-icon" />
            <h3 class="service-name">{{ svc.name }}</h3>
          </div>
          <span class="badge" :class="svc.healthy ? 'badge-status-healthy' : 'badge-status-unhealthy'">
            {{ svc.healthy ? '正常 Healthy' : '异常 Unhealthy' }}
          </span>
        </div>

        <div class="card-body">
          <div class="info-row">
            <span class="info-label">响应延迟 (Latency)</span>
            <span class="info-value font-mono">
              {{ svc.latency_ms !== null && svc.latency_ms !== undefined ? `${svc.latency_ms} ms` : '—' }}
            </span>
          </div>

          <div v-if="!svc.healthy && svc.error" class="error-detail">
            <span class="error-detail-label">错误日志 / Failure Cause:</span>
            <pre class="error-detail-code">{{ svc.error }}</pre>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { fetchAdminHealthDetails, type ServiceStatus } from '@/api/client';
import HfbIcon from '@/components/common/HfbIcon.vue';
import type { LucideIconName } from '@/components/common/HfbIcon.vue';

interface ServiceDetail extends ServiceStatus {
  name: string;
}

const loading = ref<boolean>(false);
const errorMessage = ref<string | null>(null);
const isReady = ref<boolean>(true);
const overallStatus = ref<string>('healthy');
const lastChecked = ref<string>('');
const servicesMap = ref<Record<string, ServiceStatus>>({});

const servicesList = computed<Array<ServiceDetail>>(() => {
  const result: Array<ServiceDetail> = [];
  const keys: Array<string> = Object.keys(servicesMap.value);
  for (let i = 0; i < keys.length; i += 1) {
    const k = keys[i];
    if (!k) continue;
    const s = servicesMap.value[k];
    if (!s) continue;
    result.push({
      name: s.name || k,
      healthy: s.healthy,
      latency_ms: s.latency_ms,
      error: s.error,
    });
  }
  return result;
});

const healthyCount = computed<number>(() => {
  return servicesList.value.filter((s: ServiceDetail) => s.healthy).length;
});

const unhealthyCount = computed<number>(() => {
  return servicesList.value.filter((s: ServiceDetail) => !s.healthy).length;
});

const isOverallHealthy = computed<boolean>(() => {
  return overallStatus.value === 'healthy' && unhealthyCount.value === 0;
});

const formattedLastChecked = computed<string>(() => {
  if (!lastChecked.value) return '—';
  try {
    return new Date(lastChecked.value).toLocaleString('zh-CN');
  } catch {
    return lastChecked.value;
  }
});

function getServiceIcon(name: string): LucideIconName {
  const n: string = name.toLowerCase();
  if (n.includes('postgres') || n.includes('db')) return 'inbox';
  if (n.includes('redis')) return 'flask-conical';
  if (n.includes('elastic') || n.includes('es')) return 'search';
  if (n.includes('minio') || n.includes('oss') || n.includes('storage')) return 'package-open';
  return 'info';
}

async function loadHealthDetails(): Promise<void> {
  loading.value = true;
  errorMessage.value = null;
  try {
    const res = await fetchAdminHealthDetails();
    const data = res.data;
    isReady.value = data.ready;
    overallStatus.value = data.status || 'healthy';
    servicesMap.value = data.services || {};
    lastChecked.value = data.timestamp || res.timestamp || new Date().toISOString();
  } catch (err: unknown) {
    const e: Error = err as Error;
    errorMessage.value = e.message || '获取基础设施健康诊断数据失败';
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  loadHealthDetails();
});
</script>

<style scoped>
.system-health-view {
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--space-8) 24px;
  color: var(--color-text-primary);
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: var(--space-6);
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0 0 var(--space-1) 0;
}

.page-subtitle {
  font-size: 14px;
  color: var(--color-text-secondary);
  margin: 0;
}

.btn-refresh {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) 16px;
  background: var(--color-accent);
  color: var(--color-surface);
  border: none;
  border-radius: var(--radius-md);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s ease;
}

.btn-refresh:hover:not(:disabled) {
  background: var(--color-accent-hover);
}

.btn-refresh:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.spin-icon {
  animation: spin 1s linear infinite;
  display: inline-block;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.error-banner {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
  background: var(--color-error-bg);
  border: 1px solid var(--color-error);
  border-radius: var(--radius-md);
  color: var(--color-error-text);
  margin-bottom: var(--space-6);
  font-size: 14px;
}

.overview-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
  margin-bottom: var(--space-8);
  box-shadow: var(--shadow-card-sm);
}

.overview-card.is-healthy {
  border-left: 4px solid var(--color-success);
}

.overview-card.is-unhealthy {
  border-left: 4px solid var(--color-error);
}

.overview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-4);
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.status-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  display: inline-block;
}

.dot-success {
  background: var(--color-success);
}

.dot-danger {
  background: var(--color-error);
}

.status-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.readiness-badge {
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-sm);
  font-size: 12px;
  font-weight: 600;
}

.badge-ready {
  background: var(--color-success-bg);
  color: var(--color-success-text);
  border: 1px solid var(--color-success-icon-bg);
}

.badge-not-ready {
  background: var(--color-error-bg);
  color: var(--color-error-text);
  border: 1px solid var(--color-error-icon-bg);
}

.overview-meta {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: var(--space-4);
  padding-top: var(--space-4);
  border-top: 1px solid var(--color-border);
}

.meta-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.meta-label {
  font-size: 12px;
  color: var(--color-text-muted);
}

.meta-value {
  font-size: 18px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.text-success {
  color: var(--color-success-text);
}

.text-error {
  color: var(--color-error-text);
}

.skeleton-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--space-6);
}

.card-skeleton {
  height: 160px;
  background: var(--color-hover);
  border-radius: var(--radius-lg);
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 0.6;
  }
  50% {
    opacity: 0.3;
  }
}

.services-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--space-6);
}

.service-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-5);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.service-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-card-hover);
}

.service-card.card-healthy {
  border-top: 3px solid var(--color-success);
}

.service-card.card-unhealthy {
  border-top: 3px solid var(--color-error);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-4);
}

.service-name-group {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.service-icon {
  font-size: 20px;
}

.service-name {
  font-size: 16px;
  font-weight: 600;
  margin: 0;
  color: var(--color-text-primary);
}

.badge {
  font-size: 12px;
  font-weight: 500;
  padding: var(--space-1) 8px;
  border-radius: var(--radius-sm);
}

.badge-status-healthy {
  background: var(--color-success-bg);
  color: var(--color-success-text);
}

.badge-status-unhealthy {
  background: var(--color-error-bg);
  color: var(--color-error-text);
}

.card-body {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
}

.info-label {
  color: var(--color-text-secondary);
}

.info-value {
  font-weight: 600;
  color: var(--color-text-primary);
}

.font-mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.error-detail {
  margin-top: var(--space-2);
  padding: var(--space-2);
  background: var(--color-error-bg);
  border-radius: var(--radius-sm);
}

.error-detail-label {
  display: block;
  font-size: 11px;
  font-weight: 600;
  color: var(--color-error-text);
  margin-bottom: var(--space-1);
}

.error-detail-code {
  margin: 0;
  font-size: 11px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  color: var(--color-error-text);
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
