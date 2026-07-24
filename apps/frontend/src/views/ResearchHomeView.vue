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
  padding: var(--space-7) 20px 60px;
}

.rh-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--space-4);
  margin-bottom: 32px;
  padding-bottom: 20px;
  border-bottom: 1px solid var(--color-border);
}

.rh-header h1 {
  font-size: 24px;
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0 0 var(--space-1);
}

.rh-topic-desc {
  color: var(--color-text-muted);
  font-size: 14px;
  margin: 0;
}

.rh-section {
  margin-bottom: 28px;
}

.rh-section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-secondary);
  margin: 0 0 var(--space-3-5);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.rh-tools-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: var(--space-2-5);
}

.rh-tool-card {
  display: flex;
  align-items: center;
  gap: var(--space-3-5);
  padding: var(--space-4) 18px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  background: var(--color-navbar-bg, var(--color-surface));
  text-decoration: none;
  transition: all var(--transition-base);
}

.rh-tool-card:hover {
  border-color: var(--color-accent);
  box-shadow: var(--shadow-card-xs);
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
  background: var(--color-page-bg);
  border-radius: var(--radius-lg);
}

.rh-tool-name {
  display: block;
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.rh-tool-desc {
  display: block;
  font-size: 12px;
  color: var(--color-text-muted);
  margin-top: 2px;
}

.rh-dashboard-link {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2-5) 18px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-navbar-bg, var(--color-surface));
  text-decoration: none;
  font-size: 14px;
  color: var(--color-text-secondary);
  transition: all var(--transition-base);
}

.rh-dashboard-link:hover {
  border-color: var(--color-accent);
  color: var(--color-text-primary);
}

.btn {
  padding: var(--space-2) 18px;
  border-radius: var(--radius-lg);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  border: none;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  transition: all var(--transition-base);
  white-space: nowrap;
}

.btn--secondary {
  background: transparent;
  color: var(--color-text-secondary);
  border: 1px solid var(--color-border);
}

.btn--secondary:hover {
  background: var(--color-hover);
  color: var(--color-error-text);
}
</style>
