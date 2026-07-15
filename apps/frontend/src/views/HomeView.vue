<template>
  <div class="system-status">
    <!-- Welcome Hero -->
    <div class="welcome-hero">
      <template v-if="auth.isAuthenticated && auth.user">
        <h1>{{ t('onboarding.welcomeNewUser', { name: auth.user.display_name || auth.user.username }) }}</h1>
        <p class="hero-subtitle">{{ t('onboarding.welcomeNewUserHint') }}</p>
        <router-link
          v-if="!store.hasActiveResearch"
          :to="{ name: 'research-new' }"
          class="hero-cta"
        >{{ t('onboarding.createFirstTopic') }}</router-link>
        <router-link
          v-else
          :to="{ name: 'research-home' }"
          class="hero-cta"
        >{{ t('researchEntry.backToResearch') }}</router-link>
      </template>
      <template v-else>
        <h1>{{ t('onboarding.welcomeTitle') }}</h1>
        <p class="hero-subtitle">{{ t('onboarding.welcomeAnonymous') }}</p>
        <div class="hero-actions">
          <router-link :to="{ name: 'register' }" class="hero-cta">{{ t('onboarding.startExplore') }}</router-link>
          <router-link :to="{ name: 'about' }" class="hero-link">{{ t('onboarding.learnMore') }}</router-link>
        </div>
      </template>
    </div>

    <div class="status-header">
      <h2 class="section-label">{{ t('system.title') }}</h2>
    </div>

    <!-- Primary Research Entry -->
    <div class="research-entry">
      <router-link
        v-if="auth.isAuthenticated"
        :to="{ name: store.hasActiveResearch ? 'research-home' : 'research-new' }"
        class="research-entry-btn"
      >
        <span class="entry-icon">🔬</span>
        <span class="entry-text">
          <span class="entry-label">{{ store.hasActiveResearch ? t('researchEntry.backToResearch') : t('researchEntry.startNew') }}</span>
          <span class="entry-desc" v-if="!store.hasActiveResearch">{{ t('researchEntry.startNewDesc') }}</span>
          <span class="entry-desc" v-else>{{ store.currentTopic?.name }}</span>
        </span>
      </router-link>
      <router-link
        v-else
        :to="{ name: 'login' }"
        class="research-entry-btn"
      >
        <span class="entry-icon">🔬</span>
        <span class="entry-text">
          <span class="entry-label">{{ t('researchEntry.startNew') }}</span>
          <span class="entry-desc">{{ t('auth.loginSubtitle') }}</span>
        </span>
      </router-link>
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
import { useAuthStore } from '@/stores/auth';
import { useResearchStore } from '@/stores/research';
import StatusCard from '@/components/common/StatusCard.vue';

const { t } = useI18n();
const system = useSystemStore();
const auth = useAuthStore();
const store = useResearchStore();

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

/* --- Welcome Hero --- */
.welcome-hero {
  margin-bottom: 40px;
  padding: 36px 28px;
  background: linear-gradient(135deg, #f0f4ff 0%, #faf5ff 100%);
  border-radius: 16px;
  border: 1px solid rgba(43, 108, 176, 0.12);
}

.welcome-hero h1 {
  font-size: 26px;
  font-weight: 700;
  color: var(--color-text-primary, #1a365d);
  margin: 0 0 8px;
}

.hero-subtitle {
  color: var(--color-text-secondary, #4a5568);
  font-size: 15px;
  margin: 0 0 20px;
  line-height: 1.6;
}

.hero-actions {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
}

.hero-cta {
  display: inline-block;
  padding: 10px 24px;
  background: linear-gradient(135deg, #2b6cb0, #4299e1);
  border: none;
  border-radius: 10px;
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  text-decoration: none;
  transition: all 0.2s;
  box-shadow: 0 4px 14px rgba(43, 108, 176, 0.3);
}

.hero-cta:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(43, 108, 176, 0.4);
}

.hero-link {
  display: inline-block;
  padding: 10px 24px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 10px;
  color: var(--color-text-secondary, #4a5568);
  font-size: 15px;
  font-weight: 500;
  text-decoration: none;
  transition: all 0.15s;
  background: var(--color-navbar-bg, #fff);
}

.hero-link:hover {
  border-color: var(--color-accent, #2b6cb0);
  color: var(--color-accent, #2b6cb0);
}

.status-header h2 {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-muted, #a0aec0);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin: 0 0 16px;
}

/* --- Research Entry CTA --- */
.research-entry {
  margin-bottom: 32px;
}

.research-entry-btn {
  display: inline-flex;
  align-items: center;
  gap: 16px;
  padding: 18px 28px;
  background: linear-gradient(135deg, #2b6cb0, #4299e1);
  border: none;
  border-radius: 12px;
  color: #fff;
  text-decoration: none;
  transition: all 0.2s;
  box-shadow: 0 4px 14px rgba(43, 108, 176, 0.3);
}

.research-entry-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(43, 108, 176, 0.4);
}

.entry-icon {
  font-size: 32px;
  flex-shrink: 0;
}

.entry-text {
  display: flex;
  flex-direction: column;
  text-align: left;
}

.entry-label {
  font-size: 16px;
  font-weight: 700;
}

.entry-desc {
  font-size: 12px;
  opacity: 0.85;
  margin-top: 2px;
  max-width: 280px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
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
