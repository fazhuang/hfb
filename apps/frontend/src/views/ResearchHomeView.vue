<template>
  <div class="research-home">
    <header class="rh-header">
      <div>
        <h1>{{ store.currentTopic?.name }}</h1>
        <p v-if="store.currentTopic?.description" class="rh-topic-desc">
          {{ store.currentTopic?.description }}
        </p>
      </div>
      <button class="btn btn--secondary" @click="endResearch">
        {{ t('researchEntry.endResearch') }}
      </button>
    </header>

    <!-- Research tools grid — minimum flow: Search → Workspace → Report -->
    <section class="rh-section">
      <h2 class="rh-section-title">{{ t('researchEntry.toolsTitle') }}</h2>
      <div class="rh-tools-grid">
        <router-link :to="{ name: 'search' }" class="rh-tool-card rh-tool-card--featured">
          <span class="rh-tool-icon">🔍</span>
          <div>
            <span class="rh-tool-name">{{ t('nav.search') }}</span>
            <span class="rh-tool-desc">{{ t('researchEntry.toolSearchDesc') }}</span>
          </div>
        </router-link>

        <router-link :to="{ name: 'research-workspace' }" class="rh-tool-card rh-tool-card--featured">
          <span class="rh-tool-icon">📋</span>
          <div>
            <span class="rh-tool-name">{{ t('researchEntry.researchWorkspace') }}</span>
            <span class="rh-tool-desc">{{ t('researchEntry.toolResearchWorkspaceDesc') }}</span>
          </div>
        </router-link>

        <router-link :to="{ name: 'research-workspace', query: { tab: 'reports' } }" class="rh-tool-card">
          <span class="rh-tool-icon">📊</span>
          <div>
            <span class="rh-tool-name">{{ t('researchWorkspace.reports') }}</span>
            <span class="rh-tool-desc">{{ t('researchEntry.toolReportsDesc') }}</span>
          </div>
        </router-link>

        <router-link :to="{ name: 'books' }" class="rh-tool-card">
          <span class="rh-tool-icon">📚</span>
          <div>
            <span class="rh-tool-name">{{ t('nav.books') }}</span>
            <span class="rh-tool-desc">{{ t('researchEntry.toolBooksDesc') }}</span>
          </div>
        </router-link>

        <router-link :to="{ name: 'graph' }" class="rh-tool-card">
          <span class="rh-tool-icon">🔗</span>
          <div>
            <span class="rh-tool-name">{{ t('nav.graph') }}</span>
            <span class="rh-tool-desc">{{ t('researchEntry.toolGraphDesc') }}</span>
          </div>
        </router-link>

        <router-link :to="{ name: 'research-workspace', query: { tab: 'assistant' } }" class="rh-tool-card">
          <span class="rh-tool-icon">🤖</span>
          <div>
            <span class="rh-tool-name">{{ t('researchWorkspace.assistant') }}</span>
            <span class="rh-tool-desc">{{ t('researchEntry.toolAssistantDesc') }}</span>
          </div>
        </router-link>
      </div>
    </section>

    <!-- Quick nav to Dashboard -->
    <section class="rh-section">
      <router-link :to="{ name: 'dashboard' }" class="rh-dashboard-link">
        <span>📊</span>
        {{ t('dashboard.title') }}
      </router-link>
    </section>
  </div>
</template>

<script setup lang="ts">
import { watch } from 'vue';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { useResearchStore } from '@/stores/research';

const { t } = useI18n();
const router = useRouter();
const store = useResearchStore();

// Redirect to new topic creation if no active research
watch(
  () => store.hasActiveResearch,
  (active) => {
    if (!active) {
      router.replace({ name: 'home' });
    }
  },
  { immediate: true },
);

function endResearch() {
  store.clearTopic();
  router.push({ name: 'home' });
}
</script>

<style scoped>
.research-home {
  max-width: 840px;
  margin: 0 auto;
  padding: 28px 20px 60px;
}

.rh-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 32px;
  padding-bottom: 20px;
  border-bottom: 1px solid var(--color-border, #e2e8f0);
}

.rh-header h1 {
  font-size: 24px;
  font-weight: 700;
  color: var(--color-text-primary, #1a365d);
  margin: 0 0 4px;
}

.rh-topic-desc {
  color: var(--color-text-muted, #718096);
  font-size: 14px;
  margin: 0;
}

.rh-section {
  margin-bottom: 28px;
}

.rh-section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-secondary, #4a5568);
  margin: 0 0 14px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.rh-tools-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 10px;
}

.rh-tool-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px 18px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 10px;
  background: var(--color-navbar-bg, #fff);
  text-decoration: none;
  transition: all 0.15s;
}

.rh-tool-card:hover {
  border-color: var(--color-accent, #4299e1);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  transform: translateY(-1px);
}

.rh-tool-icon {
  font-size: 24px;
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-page-bg, #fafafa);
  border-radius: 8px;
}

.rh-tool-name {
  display: block;
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary, #1a365d);
}

.rh-tool-desc {
  display: block;
  font-size: 12px;
  color: var(--color-text-muted, #a0aec0);
  margin-top: 2px;
}

.rh-dashboard-link {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 18px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 8px;
  background: var(--color-navbar-bg, #fff);
  text-decoration: none;
  font-size: 14px;
  color: var(--color-text-secondary, #4a5568);
  transition: all 0.15s;
}

.rh-dashboard-link:hover {
  border-color: var(--color-accent, #4299e1);
  color: var(--color-text-primary, #1a365d);
}

.btn {
  padding: 8px 18px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  border: none;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  transition: all 0.15s;
  white-space: nowrap;
}

.btn--secondary {
  background: transparent;
  color: var(--color-text-secondary, #4a5568);
  border: 1px solid var(--color-border, #e2e8f0);
}

.btn--secondary:hover {
  background: var(--color-hover, #edf2f7);
  color: var(--color-error-text, #c53030);
}
</style>
