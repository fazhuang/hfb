<template>
  <div class="dashboard">
    <h1 class="dashboard-title">{{ t('dashboard.title') }}</h1>

    <!-- Step-guide bar for new users -->
    <div v-if="auth.isAuthenticated && !researchStore.hasActiveResearch && allStatsZero" class="step-guide">
      <span class="sg-title">{{ t('onboarding.stepGuideTitle') }}</span>
      <div class="sg-steps">
        <router-link :to="{ name: 'research-project-list' }" class="sg-step sg-step--active">
          <span class="sg-num">1</span>
          <span class="sg-label">{{ t('onboarding.stepGuideCreateTopic') }}</span>
        </router-link>
        <span class="sg-sep">→</span>
        <span class="sg-step">
          <span class="sg-num">2</span>
          <span class="sg-label">{{ t('onboarding.stepGuideExploreTools') }}</span>
        </span>
        <span class="sg-sep">→</span>
        <span class="sg-step">
          <span class="sg-num">3</span>
          <span class="sg-label">{{ t('onboarding.stepGuideRecordNotes') }}</span>
        </span>
      </div>
    </div>

    <!-- Research Entry Card -->
    <div class="research-entry-card">
      <div class="rec-content">
        <span class="rec-icon">🔬</span>
        <div class="rec-text">
          <span class="rec-label" v-if="researchStore.hasActiveResearch">{{ t('nav.currentResearch') }}</span>
          <span class="rec-label" v-else>{{ t('researchEntry.startNew') }}</span>
          <span class="rec-desc" v-if="researchStore.hasActiveResearch">{{ researchStore.currentTopic?.name }}</span>
          <span class="rec-desc" v-else>{{ t('researchEntry.startNewDesc') }}</span>
        </div>
      </div>
      <router-link
        v-if="researchStore.hasActiveResearch"
        :to="{ name: 'research-project-list' }"
        class="rec-action"
      >
        {{ t('dashboard.goToResearch') }}
      </router-link>
      <router-link
        v-else
        :to="{ name: 'research-project-list' }"
        class="rec-action rec-action--primary"
      >
        {{ t('researchEntry.create') }}
      </router-link>
    </div>

    <!-- Stats Grid -->
    <div class="stats-grid">
      <div v-for="card in statCards" :key="card.key" class="stat-card">
        <span class="stat-icon">{{ card.icon }}</span>
        <div class="stat-info">
          <span class="stat-value">{{ card.value.toLocaleString() }}</span>
          <span class="stat-label">{{ card.label }}</span>
        </div>
      </div>
    </div>

    <!-- Zero-data onboarding hint -->
    <div v-if="allStatsZero && !researchStore.hasActiveResearch" class="onboarding-hint">
      <span class="onboarding-icon">📊</span>
      <p class="onboarding-text">{{ t('onboarding.dashboardAllZero') }}</p>
      <p class="onboarding-sub">{{ t('onboarding.dashboardAllZeroHint') }}</p>
      <router-link :to="{ name: 'research-project-list' }" class="onboarding-link">{{ t('onboarding.startExplore') }} →</router-link>
    </div>

    <!-- Charts Row -->
    <div class="charts-row">
      <!-- Dynasty Chart -->
      <div class="chart-card">
        <h3 class="chart-title">{{ t('dashboard.dynastyDistribution') }}</h3>
        <div v-if="dynastyData.length > 0" class="bar-chart">
          <div v-for="d in dynastyData.slice(0, 8)" :key="d.name" class="bar-row">
            <span class="bar-label">{{ d.name }}</span>
            <div class="bar-track">
              <div class="bar-fill" :style="{ width: barWidth(d.count, maxDynasty) }"></div>
            </div>
            <span class="bar-count">{{ d.count }}</span>
          </div>
        </div>
        <p v-else class="muted">{{ t('common.noData') }}</p>
      </div>

      <!-- Category Chart -->
      <div class="chart-card">
        <h3 class="chart-title">{{ t('dashboard.categoryDistribution') }}</h3>
        <div v-if="categoryData.length > 0" class="bar-chart">
          <div v-for="c in categoryData.slice(0, 8)" :key="c.name" class="bar-row">
            <span class="bar-label">{{ c.name }}</span>
            <div class="bar-track">
              <div class="bar-fill bar-fill--green" :style="{ width: barWidth(c.count, maxCategory) }"></div>
            </div>
            <span class="bar-count">{{ c.count }}</span>
          </div>
        </div>
        <p v-else class="muted">{{ t('common.noData') }}</p>
      </div>
    </div>

    <!-- Recent Activity -->
    <div class="activity-section">
      <h3 class="section-title">{{ t('dashboard.recentActivity') }}</h3>
      <div v-if="activities.length > 0" class="activity-list">
        <div v-for="(a, i) in activities" :key="i" class="activity-item">
          <span class="activity-icon">{{ getActivityIcon(a.entity_type) }}</span>
          <span class="activity-text">{{ a.title }}</span>
          <span class="activity-time">{{ formatTime(a.timestamp) }}</span>
        </div>
      </div>
      <p v-else class="muted">{{ t('common.noData') }}</p>
    </div>

    <!-- System Info -->
    <div class="system-section">
      <h3 class="section-title">{{ t('dashboard.systemInfo') }}</h3>
      <div class="system-grid">
        <div class="system-card">
          <span class="system-label">{{ t('system.version') }}</span>
          <span class="system-value">{{ systemInfo.version }}</span>
        </div>
        <div class="system-card">
          <span class="system-label">{{ t('dashboard.environment') }}</span>
          <span class="system-value">{{ systemInfo.environment }}</span>
        </div>
        <div class="system-card">
          <span class="system-label">{{ t('dashboard.researchSessions') }}</span>
          <span class="system-value">{{ systemInfo.research_sessions }}</span>
        </div>
        <div class="system-card">
          <span class="system-label">{{ t('dashboard.researchNotes') }}</span>
          <span class="system-value">{{ systemInfo.research_notes }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import api from '@/api/client';
import { useResearchStore } from '@/stores/research';
import { useAuthStore } from '@/stores/auth';

const { t } = useI18n();

const researchStore = useResearchStore();
const auth = useAuthStore();

interface StatCard {
  key: string;
  icon: string;
  value: number;
  label: string;
}

interface Activity {
  entity_type: string;
  title: string;
  timestamp: string | null;
}

const statCards = ref<StatCard[]>([]);
const activities = ref<Activity[]>([]);
const dynastyData = ref<{ name: string; count: number }[]>([]);
const categoryData = ref<{ name: string; count: number }[]>([]);
const systemInfo = ref<Record<string, unknown>>({});

const maxDynasty = computed(() => Math.max(...dynastyData.value.map(d => d.count), 1));
const maxCategory = computed(() => Math.max(...categoryData.value.map(c => c.count), 1));

const allStatsZero = computed(() => statCards.value.length > 0 && statCards.value.every(c => c.value === 0));

function barWidth(count: number, max: number): string {
  return `${Math.round((count / max) * 100)}%`;
}

function getActivityIcon(type: string): string {
  const icons: Record<string, string> = { person: '👤', book: '📚', passage: '📜', version: '📖', paper: '📄' };
  return icons[type] || '📌';
}

function formatTime(ts: string | null): string {
  if (!ts) return '';
  try {
    const d = new Date(ts);
    return d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  } catch { return ''; }
}

async function loadDashboard() {
  try {
    const [statsRes, overviewRes] = await Promise.all([
      api.get('/api/v1/dashboard/stats'),
      api.get('/api/v1/dashboard/overview'),
    ]);

    const stats = statsRes.data.data;
    const overview = overviewRes.data.data;

    // Stat cards
    const counts = stats.entity_counts || overview.entity_counts || {};
    statCards.value = [
      { key: 'persons', icon: '👤', value: counts.persons || 0, label: t('nav.persons') },
      { key: 'books', icon: '📚', value: counts.books || 0, label: t('nav.books') },
      { key: 'versions', icon: '📖', value: counts.versions || 0, label: t('graph.versions') },
      { key: 'passages', icon: '📜', value: counts.passages || 0, label: t('graph.passages') },
      { key: 'papers', icon: '📄', value: counts.papers || 0, label: t('search.papers') },
      { key: 'users', icon: '👥', value: counts.users || 0, label: t('dashboard.users') },
    ];

    // Charts
    dynastyData.value = stats.dynasty_distribution || [];
    categoryData.value = stats.category_distribution || [];

    // Activity
    activities.value = overview.recent_activity || [];

    // System info
    systemInfo.value = overview.system || {};
  } catch {
    // Leave empty
  }
}

onMounted(loadDashboard);
</script>

<style scoped>
.dashboard {
  max-width: 1000px;
  margin: 0 auto;
  padding: var(--space-6) 20px 60px;
}

.dashboard-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0 0 var(--space-4-5);
}

/* --- Step Guide Bar --- */
.step-guide {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  padding: var(--space-3-5) 20px;
  margin-bottom: 18px;
  background: linear-gradient(135deg, var(--color-accent-light), var(--color-success-bg));
  border: 1px solid var(--color-accent-alpha-15);
  border-radius: var(--radius-xl);
  flex-wrap: wrap;
}

.sg-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
  white-space: nowrap;
}

.sg-steps {
  display: flex;
  align-items: center;
  gap: var(--space-2-5);
}

.sg-step {
  display: flex;
  align-items: center;
  gap: var(--space-1-5);
  text-decoration: none;
}

.sg-step--active {
  color: var(--color-accent);
  font-weight: 600;
}

.sg-step--active .sg-num {
  background: var(--color-accent);
}

.sg-num {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--color-text-muted);
  color: var(--color-surface);
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
}

.sg-step--active .sg-num {
  background: var(--color-accent);
}

.sg-label {
  font-size: 13px;
  color: var(--color-text-secondary, var(--color-text-muted));
}

.sg-step--active .sg-label {
  color: var(--color-accent);
  cursor: pointer;
}

.sg-step--active:hover .sg-label {
  text-decoration: underline;
}

.sg-sep {
  color: var(--color-text-muted);
  font-size: 14px;
}

/* --- Research Entry Card --- */
.research-entry-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  padding: var(--space-4-5) 22px;
  border: 1px solid var(--color-accent);
  border-radius: var(--radius-2xl);
  background: linear-gradient(135deg, var(--color-accent-light), var(--color-success-bg));
  margin-bottom: 24px;
}

.rec-content {
  display: flex;
  align-items: center;
  gap: var(--space-3-5);
}

.rec-icon {
  font-size: 28px;
  flex-shrink: 0;
}

.rec-text {
  display: flex;
  flex-direction: column;
}

.rec-label {
  font-size: 15px;
  font-weight: 700;
  color: var(--color-text-primary);
}

.rec-desc {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin-top: 2px;
}

.rec-action {
  padding: var(--space-2) 18px;
  border-radius: var(--radius-lg);
  font-size: 13px;
  font-weight: 600;
  text-decoration: none;
  border: 1px solid var(--color-border);
  color: var(--color-text-secondary);
  background: var(--color-navbar-bg, var(--color-surface));
  transition: all var(--transition-base);
}

.rec-action:hover {
  background: var(--color-hover);
}

.rec-action--primary {
  background: var(--color-accent);
  color: var(--color-surface);
  border-color: transparent;
}

.rec-action--primary:hover {
  background: var(--color-accent-hover, var(--color-info));
}

/* --- Stats Grid --- */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: var(--space-3-5);
  margin-bottom: 28px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-4-5) 16px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  background: var(--color-navbar-bg, var(--color-surface));
  transition: box-shadow var(--transition-base);
}

.stat-card:hover {
  box-shadow: var(--shadow-card-xs);
}

.stat-icon {
  font-size: 28px;
  flex-shrink: 0;
}

.stat-info {
  display: flex;
  flex-direction: column;
}

.stat-value {
  font-size: 22px;
  font-weight: 700;
  color: var(--color-text-primary);
}

.stat-label {
  font-size: 12px;
  color: var(--color-text-muted);
}

/* --- Charts --- */
.charts-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-5);
  margin-bottom: 28px;
}

.chart-card {
  padding: var(--space-4-5) 20px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  background: var(--color-navbar-bg, var(--color-surface));
}

.chart-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 var(--space-3-5);
}

.bar-chart {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.bar-row {
  display: grid;
  grid-template-columns: 60px 1fr 30px;
  align-items: center;
  gap: var(--space-2-5);
}

.bar-label {
  font-size: 12px;
  color: var(--color-text-secondary, var(--color-text-muted));
  text-align: right;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.bar-track {
  height: 8px;
  background: var(--color-page-bg);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  background: var(--color-accent);
  border-radius: var(--radius-sm);
  min-width: 4px;
  transition: width var(--transition-slow) var(--ease-out);
}

.bar-fill--green {
  background: var(--color-success-text);
}

.bar-count {
  font-size: 11px;
  color: var(--color-text-muted);
  text-align: right;
}

/* --- Activity --- */
.activity-section,
.system-section {
  margin-bottom: 28px;
}

.section-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 var(--space-3-5);
}

.activity-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-0-5);
}

.activity-item {
  display: grid;
  grid-template-columns: 32px 1fr auto;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2-5) 14px;
  border-radius: var(--radius-md);
  transition: background var(--transition-fast);
}

.activity-item:hover {
  background: var(--color-hover);
}

.activity-icon {
  font-size: 18px;
  text-align: center;
}

.activity-text {
  font-size: 13px;
  color: var(--color-text-secondary, var(--color-text-muted));
}

.activity-time {
  font-size: 12px;
  color: var(--color-text-muted);
}

/* --- System --- */
.system-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: var(--space-3);
}

.system-card {
  padding: var(--space-3-5) 16px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-navbar-bg, var(--color-surface));
}

.system-label {
  display: block;
  font-size: 11px;
  color: var(--color-text-muted);
  text-transform: uppercase;
  margin-bottom: 4px;
}

.system-value {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.muted {
  color: var(--color-text-muted);
  font-size: 13px;
  padding: var(--space-3) 0;
}

/* --- Onboarding hint (zero data) --- */
.onboarding-hint {
  text-align: center;
  padding: var(--space-7) 20px;
  margin-bottom: 24px;
  background: linear-gradient(135deg, var(--color-accent-light), var(--color-accent-light));
  border: 1px solid var(--color-accent-alpha-12);
  border-radius: var(--radius-2xl);
}

.onboarding-icon {
  font-size: 36px;
  display: block;
  margin-bottom: 8px;
}

.onboarding-text {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 var(--space-1);
}

.onboarding-sub {
  font-size: 13px;
  color: var(--color-text-muted);
  margin: 0 0 var(--space-3-5);
}

.onboarding-link {
  display: inline-block;
  padding: var(--space-2) 20px;
  background: linear-gradient(135deg, var(--color-accent), var(--color-accent));
  color: var(--color-surface);
  border-radius: var(--radius-lg);
  font-size: 13px;
  font-weight: 600;
  text-decoration: none;
  transition: all var(--transition-base);
}

.onboarding-link:hover {
  opacity: 0.9;
  transform: translateY(-1px);
}

@media (max-width: 768px) {
  .charts-row {
    grid-template-columns: 1fr;
  }
  .stats-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}
</style>
