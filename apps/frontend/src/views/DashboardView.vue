<template>
  <div class="dashboard">
    <h1 class="dashboard-title">{{ t('dashboard.title') }}</h1>

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
        :to="{ name: 'research-home' }"
        class="rec-action"
      >
        {{ t('dashboard.goToResearch') }}
      </router-link>
      <router-link
        v-else
        :to="{ name: 'research-new' }"
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

const { t } = useI18n();

const researchStore = useResearchStore();

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
  padding: 24px 20px 60px;
}

.dashboard-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--color-text-primary, #1a365d);
  margin: 0 0 18px;
}

/* --- Research Entry Card --- */
.research-entry-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 22px;
  border: 1px solid var(--color-accent, #4299e1);
  border-radius: 12px;
  background: linear-gradient(135deg, #ebf8ff, #f0fff4);
  margin-bottom: 24px;
}

.rec-content {
  display: flex;
  align-items: center;
  gap: 14px;
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
  color: var(--color-text-primary, #1a365d);
}

.rec-desc {
  font-size: 13px;
  color: var(--color-text-secondary, #4a5568);
  margin-top: 2px;
}

.rec-action {
  padding: 8px 18px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  text-decoration: none;
  border: 1px solid var(--color-border, #e2e8f0);
  color: var(--color-text-secondary, #4a5568);
  background: var(--color-navbar-bg, #fff);
  transition: all 0.15s;
}

.rec-action:hover {
  background: var(--color-hover, #edf2f7);
}

.rec-action--primary {
  background: var(--color-accent, #4299e1);
  color: #fff;
  border-color: transparent;
}

.rec-action--primary:hover {
  background: var(--color-accent-hover, #3182ce);
}

/* --- Stats Grid --- */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 14px;
  margin-bottom: 28px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 18px 16px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 10px;
  background: var(--color-navbar-bg, #fff);
  transition: box-shadow 0.15s;
}

.stat-card:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
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
  color: var(--color-text-primary, #1a365d);
}

.stat-label {
  font-size: 12px;
  color: var(--color-text-muted, #a0aec0);
}

/* --- Charts --- */
.charts-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-bottom: 28px;
}

.chart-card {
  padding: 18px 20px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 10px;
  background: var(--color-navbar-bg, #fff);
}

.chart-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary, #1a365d);
  margin: 0 0 14px;
}

.bar-chart {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.bar-row {
  display: grid;
  grid-template-columns: 60px 1fr 30px;
  align-items: center;
  gap: 10px;
}

.bar-label {
  font-size: 12px;
  color: var(--color-text-secondary, #718096);
  text-align: right;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.bar-track {
  height: 8px;
  background: var(--color-page-bg, #fafafa);
  border-radius: 4px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  background: var(--color-accent, #2b6cb0);
  border-radius: 4px;
  min-width: 4px;
  transition: width 0.5s ease;
}

.bar-fill--green {
  background: #38a169;
}

.bar-count {
  font-size: 11px;
  color: var(--color-text-muted, #a0aec0);
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
  color: var(--color-text-primary, #1a365d);
  margin: 0 0 14px;
}

.activity-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.activity-item {
  display: grid;
  grid-template-columns: 32px 1fr auto;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  border-radius: 6px;
  transition: background 0.1s;
}

.activity-item:hover {
  background: var(--color-hover, #edf2f7);
}

.activity-icon {
  font-size: 18px;
  text-align: center;
}

.activity-text {
  font-size: 13px;
  color: var(--color-text-secondary, #718096);
}

.activity-time {
  font-size: 12px;
  color: var(--color-text-muted, #a0aec0);
}

/* --- System --- */
.system-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
}

.system-card {
  padding: 14px 16px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 8px;
  background: var(--color-navbar-bg, #fff);
}

.system-label {
  display: block;
  font-size: 11px;
  color: var(--color-text-muted, #a0aec0);
  text-transform: uppercase;
  margin-bottom: 4px;
}

.system-value {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary, #1a365d);
}

.muted {
  color: var(--color-text-muted, #a0aec0);
  font-size: 13px;
  padding: 12px 0;
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
