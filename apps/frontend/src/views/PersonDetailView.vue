<template>
  <div class="person-detail-page">
    <div v-if="loading" class="loading-state">
      {{ t('common.loading', '正在加载人物详情...') }}
    </div>
    <div v-else-if="error" class="error-state">
      <p class="error-text">{{ error }}</p>
      <button v-if="isAuthError" class="login-redirect-btn" @click="goToLogin">
        {{ t('auth.login', '前往登录') }}
      </button>
    </div>
    <div v-else-if="person" class="person-content">
      <!-- 待考资料 Alert -->
      <div v-if="person.domain_status === 'pending'" class="pending-alert-banner">
        <span class="alert-icon">⚠️</span>
        <div class="alert-content">
          <strong>待考资料：</strong>
          该人物文献记载与皇甫谧学术域关联尚处于考察研判阶段，需结合进一步古籍出处校验。
        </div>
      </div>

      <!-- 详情页头部 -->
      <div class="detail-header">
        <div class="header-top-row">
          <div class="title-wrap">
            <h1>{{ person.name }}</h1>
            <span v-if="person.name_zh" class="name-alt">{{ person.name_zh }}</span>
            <span v-if="person.name_pinyin" class="name-pinyin">({{ person.name_pinyin }})</span>
          </div>

          <div class="header-badges">
            <PersonRoleBadge :role="person.research_relation_role" />
            <span
              class="domain-status-badge"
              :class="person.domain_status === 'verified' ? 'status-verified' : 'status-pending'"
            >
              {{ person.domain_status === 'verified' ? '已验证研究域' : '待考资料' }}
            </span>
          </div>
        </div>

        <div class="header-meta">
          <span v-if="person.dynasty" class="meta-tag">{{ person.dynasty }}</span>
          <span v-if="lifeSpan" class="meta-tag">{{ lifeSpan }}</span>
          <span v-if="person.expertise" class="meta-tag expertise-tag">{{ person.expertise }}</span>
        </div>

        <!-- 皇甫谧研究域关系摘要 -->
        <div v-if="person.domain_relation_summary" class="domain-relation-card">
          <div class="relation-card-header">
            <span class="card-icon">📜</span>
            <span class="card-title">皇甫谧研究域关系摘要</span>
          </div>
          <p class="relation-card-content">{{ person.domain_relation_summary }}</p>
        </div>
      </div>

      <!-- 【皇甫谧研究域回溯链】区块 -->
      <section v-if="person.anchor_path" class="detail-section backtrace-section">
        <h2 class="section-title">
          <span class="section-icon">🔗</span>
          皇甫谧研究域回溯链
        </h2>
        <AnchorPathBreadcrumb :anchor-path="person.anchor_path" />
      </section>

      <!-- 【基本信息与生平】区块 -->
      <section class="detail-section bio-section">
        <h2 class="section-title">
          <span class="section-icon">👤</span>
          基本信息与生平
        </h2>
        <div class="info-grid">
          <div v-if="person.courtesy_name" class="info-row">
            <span class="info-label">{{ t('person.courtesyName', '字') }}</span>
            <span>{{ person.courtesy_name }}</span>
          </div>
          <div v-if="person.pseudonym" class="info-row">
            <span class="info-label">{{ t('person.pseudonym', '号') }}</span>
            <span>{{ person.pseudonym }}</span>
          </div>
          <div v-if="person.birth_place" class="info-row">
            <span class="info-label">{{ t('person.birthPlace', '籍贯/出生地') }}</span>
            <span>{{ person.birth_place }}</span>
          </div>
        </div>

        <div v-if="person.biography" class="person-bio-box">
          <h3>{{ t('person.biography', '生平述要') }}</h3>
          <p>{{ person.biography }}</p>
          <span v-if="person.biography_source" class="bio-source">
            出处来源：{{ person.biography_source }}
          </span>
        </div>
      </section>

      <!-- 【古籍证据与考据出处】区块 -->
      <section class="detail-section evidence-section">
        <h2 class="section-title">
          <span class="section-icon">📚</span>
          古籍证据与考据出处
        </h2>
        <div class="evidence-content">
          <div v-if="workList.length > 0" class="evidence-block">
            <h3>代表著作</h3>
            <div class="works-list">
              <span v-for="work in workList" :key="work" class="work-item">《{{ work }}》</span>
            </div>
          </div>

          <div v-if="person.biography_source" class="evidence-block">
            <h3>史料文献源</h3>
            <p class="source-detail">{{ person.biography_source }}</p>
          </div>

          <div v-if="person.external_ref" class="evidence-block">
            <h3>外部权威考据参考</h3>
            <a :href="person.external_ref" target="_blank" rel="noopener" class="external-link">
              {{ person.external_ref }} ↗
            </a>
          </div>

          <div class="evidence-block domain-evidence-status">
            <h3>研究域考据评定</h3>
            <div class="status-summary">
              <span class="status-dot" :class="person.domain_status === 'verified' ? 'dot-verified' : 'dot-pending'"></span>
              <span>
                {{ person.domain_status === 'verified' ? '已通过皇甫谧数字人文课题文献关联校验' : '尚在考据研判中，属于待考资料' }}
              </span>
            </div>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute, useRouter } from 'vue-router';
import { useEntityDetail } from '@/composables/useApi';
import PersonRoleBadge from '@/components/person/PersonRoleBadge.vue';
import AnchorPathBreadcrumb from '@/components/person/AnchorPathBreadcrumb.vue';

export interface PersonDetail {
  id: string;
  name: string;
  name_zh: string | null;
  name_pinyin: string | null;
  courtesy_name: string | null;
  pseudonym: string | null;
  dynasty: string | null;
  birth_year: number | null;
  death_year: number | null;
  birth_place: string | null;
  biography: string | null;
  biography_source: string | null;
  notable_works: string | null;
  expertise: string | null;
  external_ref: string | null;
  domain_status: 'verified' | 'pending' | string;
  research_relation_role: string | null;
  domain_relation_summary: string | null;
  anchor_path: string | null;
}

const { t } = useI18n();
const route = useRoute();
const router = useRouter();

const {
  entity: person,
  loading,
  error,
  fetch,
} = useEntityDetail<PersonDetail>((id) => `/api/v1/persons/${id}`);

const isAuthError = computed<boolean>(() => {
  if (!error.value) return false;
  return (
    error.value.includes('未登录') ||
    error.value.includes('登录会话已过期') ||
    error.value.includes('401')
  );
});

function goToLogin(): void {
  router.push({ name: 'login', query: { redirect: route.fullPath } });
}

const lifeSpan = computed<string | null>(() => {
  if (!person.value) return null;
  const b = person.value.birth_year;
  const d = person.value.death_year;
  if (b && d) return `${b} - ${d}`;
  if (b) return `${b} - ?`;
  return null;
});

const workList = computed<Array<string>>(() => {
  if (!person.value?.notable_works) return [];
  return person.value.notable_works
    .split(',')
    .map((w: string) => w.trim().replace(/^《|》$/g, ''))
    .filter(Boolean);
});

onMounted(() => {
  if (route.params.id) {
    fetch(route.params.id as string);
  }
});
</script>

<style scoped>
.person-detail-page {
  max-width: 900px;
  margin: 0 auto;
  padding: var(--space-8, 32px) var(--space-6, 24px);
}

/* 待考Alert */
.pending-alert-banner {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3, 12px);
  padding: var(--space-4, 16px);
  background: var(--color-warning-bg);
  border: 1px solid var(--color-warning);
  border-radius: var(--radius-lg, 8px);
  color: var(--color-warning-text);
  margin-bottom: var(--space-6, 24px);
}

.alert-icon {
  font-size: var(--text-xl, 20px);
}

.alert-content {
  font-size: var(--text-sm, 14px);
  line-height: 1.5;
}

/* 详情头部 */
.detail-header {
  margin-bottom: var(--space-8, 32px);
}

.header-top-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--space-3, 12px);
}

.title-wrap {
  display: flex;
  align-items: baseline;
  gap: var(--space-2, 8px);
}

.title-wrap h1 {
  font-size: var(--text-3xl, 28px);
  font-weight: var(--font-bold, 700);
  color: var(--color-text-primary);
  margin: 0;
}

.name-alt {
  font-size: var(--text-lg, 18px);
  color: var(--color-text-secondary);
}

.name-pinyin {
  font-size: var(--text-sm, 14px);
  color: var(--color-text-muted);
}

.header-badges {
  display: flex;
  align-items: center;
  gap: var(--space-2, 8px);
}

.domain-status-badge {
  font-size: var(--text-xs, 12px);
  padding: var(--space-0-5, 2px) var(--space-2, 8px);
  border-radius: var(--radius-sm, 4px);
  font-weight: var(--font-semibold, 600);
}

.status-verified {
  background: var(--color-success-bg);
  color: var(--color-success-text);
  border: 1px solid var(--color-success);
}

.status-pending {
  background: var(--color-warning-bg);
  color: var(--color-warning-text);
  border: 1px solid var(--color-warning);
}

.header-meta {
  display: flex;
  gap: var(--space-2, 8px);
  margin-top: var(--space-3, 12px);
}

.meta-tag {
  font-size: var(--text-xs, 12px);
  padding: var(--space-1, 4px) var(--space-3, 12px);
  background: var(--color-tag-bg);
  color: var(--color-text-secondary);
  border-radius: var(--radius-sm, 4px);
}

.expertise-tag {
  background: var(--color-accent-light);
  color: var(--color-accent);
}

/* 关系摘要卡片 */
.domain-relation-card {
  margin-top: var(--space-4, 16px);
  padding: var(--space-4, 16px);
  background: var(--color-surface);
  border: 1px solid var(--color-accent);
  border-radius: var(--radius-lg, 8px);
}

.relation-card-header {
  display: flex;
  align-items: center;
  gap: var(--space-2, 8px);
  margin-bottom: var(--space-2, 8px);
}

.card-title {
  font-size: var(--text-sm, 14px);
  font-weight: var(--font-bold, 700);
  color: var(--color-accent);
}

.relation-card-content {
  font-size: var(--text-base, 14px);
  color: var(--color-text-primary);
  line-height: 1.6;
  margin: 0;
}

/* 详情区块通用 */
.detail-section {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl, 12px);
  padding: var(--space-6, 24px);
  margin-bottom: var(--space-6, 24px);
}

.section-title {
  display: flex;
  align-items: center;
  gap: var(--space-2, 8px);
  font-size: var(--text-lg, 18px);
  font-weight: var(--font-bold, 700);
  color: var(--color-text-primary);
  margin: 0 0 var(--space-4, 16px);
}

.section-icon {
  font-size: var(--text-lg, 18px);
}

/* 生平区块 */
.info-grid {
  margin-bottom: var(--space-4, 16px);
}

.info-row {
  display: flex;
  gap: var(--space-3, 12px);
  padding: var(--space-2, 8px) 0;
  font-size: var(--text-sm, 14px);
  color: var(--color-text-secondary);
}

.info-label {
  font-weight: var(--font-semibold, 600);
  min-width: 80px;
  color: var(--color-text-muted);
}

.person-bio-box {
  padding: var(--space-4, 16px);
  background: var(--color-page-bg);
  border-radius: var(--radius-lg, 8px);
}

.person-bio-box h3 {
  font-size: var(--text-sm, 14px);
  font-weight: var(--font-semibold, 600);
  margin: 0 0 var(--space-2, 8px);
  color: var(--color-text-primary);
}

.person-bio-box p {
  font-size: var(--text-sm, 14px);
  line-height: 1.8;
  color: var(--color-text-secondary);
  margin: 0 0 var(--space-2, 8px);
}

.bio-source {
  font-size: var(--text-xs, 12px);
  color: var(--color-text-muted);
  display: block;
}

/* 古籍证据区块 */
.evidence-content {
  display: flex;
  flex-direction: column;
  gap: var(--space-4, 16px);
}

.evidence-block h3 {
  font-size: var(--text-sm, 14px);
  font-weight: var(--font-semibold, 600);
  color: var(--color-text-primary);
  margin: 0 0 var(--space-2, 8px);
}

.works-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2, 8px);
}

.work-item {
  padding: var(--space-1-5, 6px) var(--space-3, 12px);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md, 6px);
  font-size: var(--text-xs, 12px);
  color: var(--color-text-secondary);
  background: var(--color-page-bg);
}

.source-detail {
  font-size: var(--text-sm, 14px);
  color: var(--color-text-secondary);
  margin: 0;
}

.external-link {
  font-size: var(--text-sm, 14px);
  color: var(--color-accent);
  text-decoration: none;
}

.external-link:hover {
  text-decoration: underline;
}

.domain-evidence-status {
  padding-top: var(--space-3, 12px);
  border-top: 1px dashed var(--color-border);
}

.status-summary {
  display: flex;
  align-items: center;
  gap: var(--space-2, 8px);
  font-size: var(--text-sm, 14px);
  color: var(--color-text-secondary);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}

.dot-verified {
  background: var(--color-success);
}

.dot-pending {
  background: var(--color-warning);
}

.loading-state,
.error-state {
  text-align: center;
  padding: var(--space-20, 80px) var(--space-5, 20px);
  color: var(--color-text-muted);
  font-size: var(--text-base, 16px);
}

.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-3, 12px);
}

.error-text {
  margin: 0;
}

.login-redirect-btn {
  padding: var(--space-2, 8px) var(--space-4, 16px);
  background: var(--color-accent);
  color: var(--color-surface);
  border: none;
  border-radius: var(--radius-lg, 8px);
  cursor: pointer;
  font-size: var(--text-sm, 14px);
  font-weight: var(--font-semibold, 600);
  transition: background var(--transition-base, 0.2s);
}

.login-redirect-btn:hover {
  background: var(--color-accent-hover);
}
</style>
