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
  margin: var(--space-20) auto;
  padding: var(--space-10) 32px;
  text-align: center;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

/* --- Welcome Hero --- */
.welcome-hero {
  margin-bottom: 40px;
  padding: var(--space-9) 28px;
  background: linear-gradient(135deg, var(--color-accent-light) 0%, var(--color-accent-light) 100%);
  border-radius: var(--radius-3xl);
  border: 1px solid var(--color-accent-alpha-12);
}

.welcome-hero h1 {
  font-size: 26px;
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0 0 var(--space-2);
}

.hero-subtitle {
  color: var(--color-text-secondary);
  font-size: 15px;
  margin: 0 0 var(--space-5);
  line-height: 1.6;
}

.hero-actions {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-4);
}

.hero-cta {
  display: inline-block;
  padding: var(--space-2-5) 24px;
  background: linear-gradient(135deg, var(--color-accent), var(--color-accent));
  border: none;
  border-radius: var(--radius-xl);
  color: var(--color-surface);
  font-size: 15px;
  font-weight: 600;
  text-decoration: none;
  transition: all var(--transition-slow);
  box-shadow: var(--shadow-accent-lg);
}

.hero-cta:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-accent-xl);
}

.hero-link {
  display: inline-block;
  padding: var(--space-2-5) 24px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  color: var(--color-text-secondary);
  font-size: 15px;
  font-weight: 500;
  text-decoration: none;
  transition: all var(--transition-base);
  background: var(--color-navbar-bg, var(--color-surface));
}

.hero-link:hover {
  border-color: var(--color-accent);
  color: var(--color-accent);
}

.status-header h2 {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin: 0 0 var(--space-4);
}

/* --- Research Entry CTA --- */
.research-entry {
  margin-bottom: 32px;
}

.research-entry-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-4-5) 28px;
  background: linear-gradient(135deg, var(--color-accent), var(--color-accent));
  border: none;
  border-radius: var(--radius-2xl);
  color: var(--color-surface);
  text-decoration: none;
  transition: all var(--transition-slow);
  box-shadow: var(--shadow-accent-lg);
}

.research-entry-btn:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-accent-xl);
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
  color: var(--color-text-secondary);
  font-size: 16px;
  padding: var(--space-10) 0;
}

.spinner {
  display: inline-block;
  width: 18px;
  height: 18px;
  border: 2px solid var(--color-border);
  border-top-color: var(--color-accent);
  border-radius: 50%;
  animation: spin var(--transition-spinner) var(--ease-linear) infinite;
  vertical-align: middle;
  margin-right: 8px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.status-grid {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.system-ready {
  margin: var(--space-6) 0 16px;
}

.ready-badge {
  display: inline-block;
  padding: var(--space-1-5) 24px;
  background: var(--color-success-text);
  color: var(--color-surface);
  border-radius: var(--radius-xl);
  font-size: 14px;
  font-weight: 600;
}

.version-info {
  color: var(--color-text-muted);
  font-size: 13px;
  margin-bottom: 8px;
}

.env-tag {
  display: inline-block;
  margin-left: 8px;
  padding: var(--space-0-25) 8px;
  background: var(--color-hover);
  border-radius: var(--radius-sm);
  font-size: 12px;
  text-transform: uppercase;
}

.error-banner {
  background: var(--color-error-bg);
  color: var(--color-error-text);
  padding: var(--space-3) 20px;
  border-radius: var(--radius-lg);
  margin: var(--space-4) 0;
  font-size: 14px;
}

.refresh-btn {
  margin-top: 24px;
  padding: var(--space-2-5) 28px;
  background: var(--color-accent);
  color: white;
  border: none;
  border-radius: var(--radius-lg);
  font-size: 14px;
  cursor: pointer;
  transition: background var(--transition-slow);
}

.refresh-btn:hover:not(:disabled) {
  background: var(--color-accent-hover, var(--color-info));
}

.refresh-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
