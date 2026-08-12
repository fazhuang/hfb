<template>
  <div class="dashboard">
    <!-- Page Title -->
    <header class="page-header">
      <div class="title-block">
        <h1 class="page-title">{{ t('dashboard.title') }}</h1>
        <p class="page-subtitle">皇甫谧数字人文平台 · 研究数据总览</p>
      </div>
    </header>

    <!-- Step-guide bar for new users -->
    <div
      v-if="auth.isAuthenticated && !researchStore.hasActiveResearch && allStatsZero"
      class="step-guide"
    >
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
          <span class="rec-label" v-if="researchStore.hasActiveResearch">{{
            t('nav.currentResearch')
          }}</span>
          <span class="rec-label" v-else>{{ t('researchEntry.startNew') }}</span>
          <span class="rec-desc" v-if="researchStore.hasActiveResearch">{{
            researchStore.currentTopic?.name
          }}</span>
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
    <section aria-label="统计概览" class="dashboard-section">
      <h2 class="section-title sr-only">统计概览</h2>
      <div class="stats-grid">
        <div
          v-for="(card, i) in statCards"
          :key="card.key"
          class="stat-card"
          :class="[`stat-card--${card.key}`]"
          :style="{ animationDelay: `${120 + i * 60}ms` }"
        >
          <div class="stat-icon">
            <span>{{ card.icon }}</span>
          </div>
          <div class="stat-info">
            <span class="stat-number">{{ card.value.toLocaleString() }}</span>
            <span class="stat-label">{{ card.label }}</span>
          </div>
        </div>
      </div>
    </section>

    <!-- Charts Row -->
    <section aria-label="数据分析" class="dashboard-section">
      <div class="charts-row">
        <!-- Dynasty Chart -->
        <div class="chart-card">
          <h2 class="section-title">{{ t('dashboard.dynastyDistribution') }}</h2>
          <svg
            v-if="dynastyData.length > 0"
            :viewBox="`0 0 460 ${Math.max(dynastyData.length * 28 + 24, 180)}`"
            role="img"
            :aria-label="t('dashboard.dynastyDistribution')"
            class="chart-svg"
          >
            <!-- Grid lines -->
            <line
              v-for="n in 5"
              :key="n"
              :x1="76"
              :y1="12 + (n - 1) * 36"
              :x2="440"
              :y2="12 + (n - 1) * 36"
              class="chart-grid-line"
            />
            <!-- Bars -->
            <g v-for="(d, i) in dynastyData.slice(0, 8)" :key="d.name">
              <rect
                x="108"
                :y="22 + i * 28"
                :width="barWidthPx(d.count, maxDynasty, 280)"
                height="14"
                rx="2"
                class="chart-bar-fill"
              />
              <text
                x="394"
                :y="32 + i * 28"
                class="chart-bar-value"
              >{{ d.count }}</text>
              <text
                x="104"
                :y="32 + i * 28"
                text-anchor="end"
                class="chart-bar-label"
              >{{ d.name }}</text>
            </g>
          </svg>
          <p v-else class="chart-empty">{{ t('common.noData') }}</p>
        </div>

        <!-- Category Chart -->
        <div class="chart-card">
          <h2 class="section-title">{{ t('dashboard.categoryDistribution') }}</h2>
          <svg
            v-if="categoryData.length > 0"
            :viewBox="`0 0 460 ${Math.max(categoryData.length * 28 + 24, 180)}`"
            role="img"
            :aria-label="t('dashboard.categoryDistribution')"
            class="chart-svg"
          >
            <line
              v-for="n in 5"
              :key="n"
              :x1="76"
              :y1="12 + (n - 1) * 36"
              :x2="440"
              :y2="12 + (n - 1) * 36"
              class="chart-grid-line"
            />
            <g v-for="(c, i) in categoryData.slice(0, 8)" :key="c.name">
              <rect
                x="108"
                :y="22 + i * 28"
                :width="barWidthPx(c.count, maxCategory, 280)"
                height="14"
                rx="2"
                class="chart-bar-fill chart-bar-fill--green"
              />
              <text
                x="394"
                :y="32 + i * 28"
                class="chart-bar-value"
              >{{ c.count }}</text>
              <text
                x="104"
                :y="32 + i * 28"
                text-anchor="end"
                class="chart-bar-label"
              >{{ c.name }}</text>
            </g>
          </svg>
          <p v-else class="chart-empty">{{ t('common.noData') }}</p>
        </div>
      </div>
    </section>

    <!-- Recent Activity -->
    <section aria-label="最近动态" class="dashboard-section">
      <div class="activity-card">
        <h2 class="section-title">{{ t('dashboard.recentActivity') }}</h2>
        <ul v-if="activities.length > 0" class="activity-list">
          <li v-for="(a, i) in activities" :key="i" class="activity-item">
            <div class="activity-icon" :class="[`act-${getActivityCategory(a.entity_type)}`]">
              <span v-if="a.entity_type === 'person'">👤</span>
              <span v-else-if="a.entity_type === 'book'">📚</span>
              <span v-else-if="a.entity_type === 'passage'">📜</span>
              <span v-else-if="a.entity_type === 'version'">📖</span>
              <span v-else-if="a.entity_type === 'paper'">📄</span>
              <span v-else>📌</span>
            </div>
            <div class="activity-main">
              <div class="activity-text">
                <strong>{{ a.title }}</strong>
              </div>
              <div class="activity-detail">{{ getActivityTypeLabel(a.entity_type) }}</div>
            </div>
            <time class="activity-time">{{ formatTime(a.timestamp) }}</time>
          </li>
        </ul>
        <p v-else class="chart-empty">{{ t('common.noData') }}</p>
      </div>
    </section>

    <!-- System Info -->
    <section aria-label="系统信息" class="dashboard-section">
      <h2 class="section-title">{{ t('dashboard.systemInfo') }}</h2>
      <div class="sys-grid">
        <div class="sys-card">
          <div class="sys-label"><span class="sys-dot" />系统版本</div>
          <div class="sys-value sys-value--mono">{{ systemInfo.version }}</div>
        </div>
        <div class="sys-card">
          <div class="sys-label"><span class="sys-dot sys-dot--alt" />{{ t('dashboard.environment') }}</div>
          <div class="sys-value"><span class="sys-tag">{{ systemInfo.environment }}</span></div>
        </div>
        <div class="sys-card">
          <div class="sys-label"><span class="sys-dot sys-dot--warn" />{{ t('dashboard.researchSessions') }}</div>
          <div class="sys-value">{{ systemInfo.research_sessions }}</div>
        </div>
        <div class="sys-card">
          <div class="sys-label"><span class="sys-dot sys-dot--info" />{{ t('dashboard.researchNotes') }}</div>
          <div class="sys-value">{{ systemInfo.research_notes }}</div>
        </div>
      </div>
    </section>
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

const maxDynasty = computed(() => Math.max(...dynastyData.value.map((d) => d.count), 1));
const maxCategory = computed(() => Math.max(...categoryData.value.map((c) => c.count), 1));

const allStatsZero = computed(
  () => statCards.value.length > 0 && statCards.value.every((c) => c.value === 0),
);

function barWidthPx(count: number, max: number, total: number): number {
  return Math.round((count / max) * total);
}

function getActivityCategory(type: string): string {
  const map: Record<string, string> = {
    person: 'person',
    book: 'doc',
    passage: 'report',
    version: 'version',
    paper: 'graph',
  };
  return map[type] || 'other';
}

function getActivityTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    person: t('nav.persons'),
    book: t('nav.books'),
    passage: t('graph.passages'),
    version: t('graph.versions'),
    paper: t('search.papers'),
  };
  return labels[type] || '';
}

function formatTime(ts: string | null): string {
  if (!ts) return '';
  try {
    const d = new Date(ts);
    return d.toLocaleDateString('zh-CN', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return '';
  }
}

async function loadDashboard() {
  try {
    const [statsRes, overviewRes] = await Promise.all([
      api.get('/api/v1/dashboard/stats'),
      api.get('/api/v1/dashboard/overview'),
    ]);

    const stats = statsRes.data.data;
    const overview = overviewRes.data.data;

    const counts = stats.entity_counts || overview.entity_counts || {};
    statCards.value = [
      { key: 'persons', icon: '👤', value: counts.persons || 0, label: t('nav.persons') },
      { key: 'books', icon: '📚', value: counts.books || 0, label: t('nav.books') },
      { key: 'versions', icon: '📖', value: counts.versions || 0, label: t('graph.versions') },
      { key: 'passages', icon: '📜', value: counts.passages || 0, label: t('graph.passages') },
      { key: 'papers', icon: '📄', value: counts.papers || 0, label: t('search.papers') },
      { key: 'users', icon: '👥', value: counts.users || 0, label: t('dashboard.users') },
    ];

    dynastyData.value = stats.dynasty_distribution || [];
    categoryData.value = stats.category_distribution || [];
    activities.value = overview.recent_activity || [];
    systemInfo.value = overview.system || {};
  } catch {
    // Leave empty
  }
}

onMounted(loadDashboard);
</script>

<style scoped>
/* ── Page Shell ── */
.dashboard {
  max-width: 1000px;
  margin: 0 auto;
  padding: var(--space-8) 20px 64px;
}

.page-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  margin-bottom: var(--space-6);
  flex-wrap: wrap;
  gap: var(--space-4);
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--color-text-primary);
  letter-spacing: 0.02em;
  margin: 0;
  line-height: 1.3;
}

.page-subtitle {
  color: var(--color-text-muted);
  font-size: 13px;
  margin: var(--space-1-5) 0 0;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 var(--space-4);
  letter-spacing: 0.01em;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
}

.dashboard-section {
  margin-bottom: var(--space-8);
}

/* ── Step Guide Bar (no gradient) ── */
.step-guide {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  padding: var(--space-3-5) 20px;
  margin-bottom: var(--space-5);
  background: var(--color-accent-alpha-05);
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

.sg-step--active .sg-label {
  color: var(--color-accent);
  font-weight: 600;
  cursor: pointer;
}

.sg-step--active:hover .sg-label {
  text-decoration: underline;
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
  color: var(--color-text-secondary);
}

.sg-sep {
  color: var(--color-text-muted);
  font-size: 14px;
}

/* ── Research Entry Card (no gradient) ── */
.research-entry-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  padding: var(--space-4-5) 22px;
  border: 2px solid var(--color-accent);
  border-radius: var(--radius-2xl);
  background: var(--color-accent-alpha-05);
  box-shadow: var(--shadow-accent-sm);
  margin-bottom: var(--space-6);
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
  background: var(--color-navbar-bg);
  transition: background var(--transition-base), border-color var(--transition-base);
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
  background: var(--color-accent-hover);
}

/* ── Stats Grid ── */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: var(--space-4);
}

.stat-card {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-5) var(--space-4);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-card-xs);
  transition: box-shadow var(--transition-base) var(--ease-out), transform var(--transition-base) var(--ease-out);
  opacity: 0;
  animation: stat-enter var(--transition-slow) var(--ease-out) forwards;
}

.stat-card:hover {
  box-shadow: var(--shadow-card-hover);
  transform: translateY(-1px);
}

.stat-icon {
  width: 44px;
  height: 44px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-lg);
  font-size: 20px;
  background: var(--color-accent-alpha-08);
}

.stat-card--persons .stat-icon { background: var(--color-accent-alpha-08); }
.stat-card--books .stat-icon { background: var(--color-accent-alpha-12); }
.stat-card--versions .stat-icon { background: var(--color-accent-alpha-05); }
.stat-card--passages .stat-icon { background: var(--color-success-bg); }
.stat-card--papers .stat-icon { background: var(--color-warning-bg); }
.stat-card--users .stat-icon { background: var(--color-info-bg); }

.stat-info {
  min-width: 0;
}

.stat-number {
  font-size: 26px;
  font-weight: 700;
  color: var(--color-text-primary);
  line-height: 1.1;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.01em;
}

.stat-label {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin-top: var(--space-1);
}

@keyframes stat-enter {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}

/* ── Charts (inline SVG) ── */
.charts-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-4);
}

.chart-card {
  padding: var(--space-5) var(--space-5) var(--space-6);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-card-xs);
}

.chart-svg {
  width: 100%;
  height: auto;
}

:deep(.chart-grid-line) {
  stroke: var(--color-border);
  opacity: 0.35;
}

:deep(.chart-bar-fill) {
  fill: var(--color-accent);
}

:deep(.chart-bar-fill--green) {
  fill: var(--color-success-text);
}

:deep(.chart-bar-value) {
  fill: var(--color-text-muted);
  font-family: var(--color-text-muted, inherit);
  font-size: 11px;
  font-variant-numeric: tabular-nums;
}

:deep(.chart-bar-label) {
  fill: var(--color-text-secondary);
  font-size: 12px;
}

.chart-empty {
  color: var(--color-text-muted);
  font-size: 13px;
  padding: var(--space-3) 0;
}

/* ── Activity ── */
.activity-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-2xl);
  box-shadow: var(--shadow-card-xs);
  padding: var(--space-5) var(--space-5) var(--space-1);
  overflow: hidden;
}

.activity-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.activity-item {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-3) var(--space-1);
  border-bottom: 1px solid var(--color-border);
  transition: background var(--transition-fast);
}

.activity-item:last-child {
  border-bottom: none;
}

.activity-item:hover {
  background: var(--color-hover);
}

.activity-icon {
  width: 34px;
  height: 34px;
  flex-shrink: 0;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
}

.act-person { background: var(--color-accent-alpha-08); }
.act-doc { background: var(--color-warning-bg); }
.act-report { background: var(--color-success-bg); }
.act-version { background: var(--color-accent-alpha-12); }
.act-graph { background: var(--color-error-bg); }
.act-other { background: var(--color-muted-alpha-12); }

.activity-main {
  flex: 1;
  min-width: 0;
}

.activity-text {
  font-size: 14px;
  color: var(--color-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.activity-text strong {
  font-weight: 600;
  color: var(--color-accent);
}

.activity-detail {
  font-size: 12px;
  color: var(--color-text-muted);
  margin-top: 2px;
}

.activity-time {
  font-size: 12px;
  color: var(--color-text-muted);
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
  flex-shrink: 0;
}

/* ── System Info ── */
.sys-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: var(--space-4);
}

.sys-card {
  padding: var(--space-5) var(--space-4);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-card-xs);
  transition: box-shadow var(--transition-base) var(--ease-out);
}

.sys-card:hover {
  box-shadow: var(--shadow-card-hover);
}

.sys-label {
  font-size: 12px;
  color: var(--color-text-muted);
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
  text-transform: none;
}

.sys-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-accent);
  flex-shrink: 0;
}

.sys-dot--alt { background: var(--color-success-text); }
.sys-dot--warn { background: var(--color-warning); }
.sys-dot--info { background: var(--color-info); }

.sys-value {
  font-size: 20px;
  font-weight: 600;
  color: var(--color-text-primary);
  letter-spacing: -0.01em;
}

.sys-value--mono {
  font-family: var(--font-mono);
  font-size: 17px;
  font-weight: 500;
}

.sys-tag {
  display: inline-block;
  font-size: 13px;
  font-weight: 500;
  color: var(--color-success-text);
  background: var(--color-success-bg);
  padding: var(--space-0-75) var(--space-3);
  border-radius: var(--radius-sm);
}

/* ── Responsive ── */
@media (max-width: 1023px) {
  .charts-row {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .dashboard {
    padding: var(--space-6) 16px 40px;
  }

  .charts-row {
    grid-template-columns: 1fr;
  }

  .stats-grid {
    grid-template-columns: repeat(3, 1fr);
  }

  .sys-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .activity-item {
    flex-wrap: wrap;
    gap: var(--space-2-5);
  }

  .activity-time {
    width: 100%;
    margin-left: 50px;
    margin-top: -4px;
  }

  .activity-text {
    white-space: normal;
  }

  .page-title {
    font-size: 22px;
  }
}

@media (max-width: 480px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }
}
</style>
