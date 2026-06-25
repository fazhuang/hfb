<template>
  <div class="system-status">
    <div class="status-header">
      <h1>{{ t('system.title') }}</h1>
      <p class="subtitle">{{ t('system.subtitle') }}</p>
    </div>

    <div v-if="system.checking" class="status-checking">
      <span class="spinner"></span> {{ t('system.checking') }}
    </div>

    <div v-else class="status-grid">
      <StatusCard
        :label="system.backendConnected ? t('system.backendConnected') : t('system.backendDisconnected')"
        :connected="system.backendConnected"
      />
      <StatusCard
        :label="system.dbConnected ? t('system.dbConnected') : t('system.dbDisconnected')"
        :connected="system.dbConnected"
      />
      <StatusCard
        :label="system.redisConnected ? t('system.redisConnected') : t('system.redisDisconnected')"
        :connected="system.redisConnected"
      />
      <StatusCard
        :label="system.esConnected ? t('system.esConnected') : t('system.esDisconnected')"
        :connected="system.esConnected"
      />
      <StatusCard
        :label="system.minioConnected ? t('system.minioConnected') : t('system.minioDisconnected')"
        :connected="system.minioConnected"
      />
    </div>

    <div class="system-ready" v-if="allConnected && !system.checking">
      <span class="ready-badge">{{ t('system.allReady') }}</span>
    </div>

    <div class="version-info" v-if="system.version">
      <span>{{ t('system.version') }} {{ system.version }}</span>
      <span class="env-tag">{{ system.environment }}</span>
    </div>

    <div v-if="system.error" class="error-banner">
      {{ system.error }}
    </div>

    <button class="refresh-btn" @click="refresh" :disabled="system.checking">
      {{ system.checking ? t('system.checking') : t('system.refresh') }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { useSystemStore } from '@/stores/system';
import StatusCard from '@/components/common/StatusCard.vue';

const { t } = useI18n();
const system = useSystemStore();

const allConnected = computed(
  () =>
    system.backendConnected &&
    system.dbConnected &&
    system.redisConnected &&
    system.esConnected &&
    system.minioConnected,
);

function refresh() {
  system.checkHealth();
}

onMounted(() => {
  system.checkHealth();
});
</script>

<style scoped>
.system-status {
  max-width: 640px;
  margin: 80px auto;
  padding: 40px 32px;
  text-align: center;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

.status-header h1 {
  font-size: 28px;
  font-weight: 700;
  color: var(--color-text-primary, #1a365d);
  margin: 0 0 4px;
}

.subtitle {
  color: var(--color-text-muted, #718096);
  font-size: 14px;
  margin: 0 0 40px;
}

.status-checking {
  color: var(--color-text-secondary, #4a5568);
  font-size: 16px;
  padding: 40px 0;
}

.spinner {
  display: inline-block;
  width: 18px;
  height: 18px;
  border: 2px solid var(--color-border, #e2e8f0);
  border-top-color: var(--color-accent, #4299e1);
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
  vertical-align: middle;
  margin-right: 8px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.status-grid {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.system-ready {
  margin: 24px 0 16px;
}

.ready-badge {
  display: inline-block;
  padding: 6px 24px;
  background: #22543d;
  color: #fff;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 600;
}

.version-info {
  color: var(--color-text-muted, #a0aec0);
  font-size: 13px;
  margin-bottom: 8px;
}

.env-tag {
  display: inline-block;
  margin-left: 8px;
  padding: 1px 8px;
  background: var(--color-tag-bg, #edf2f7);
  border-radius: 4px;
  font-size: 12px;
  text-transform: uppercase;
}

.error-banner {
  background: var(--color-error-bg, #fff5f5);
  color: var(--color-error-text, #c53030);
  padding: 12px 20px;
  border-radius: 8px;
  margin: 16px 0;
  font-size: 14px;
}

.refresh-btn {
  margin-top: 24px;
  padding: 10px 28px;
  background: var(--color-accent, #4299e1);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.2s;
}

.refresh-btn:hover:not(:disabled) {
  background: var(--color-accent-hover, #3182ce);
}

.refresh-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
