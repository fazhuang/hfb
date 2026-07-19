<template>
  <div class="lib-detail-page">
    <ResearchPageHeader
      :title="doc?.title || '文献详情'"
      :description="doc?.dynasty || ''"
      :breadcrumbs="breadcrumbs"
    >
      <template v-if="doc" #actions>
        <button
          class="lib-read-btn"
          @click="openReader"
        >
          📖 全文阅读
        </button>
      </template>
    </ResearchPageHeader>

    <div class="lib-detail-body">
      <!-- Loading -->
      <LoadingState
        v-if="loading"
        :message="t('common.loading')"
      />

      <!-- Error -->
      <ErrorState
        v-else-if="error"
        :message="error"
        @retry="fetch"
      />

      <!-- Content -->
      <template v-else-if="doc">
        <!-- Meta tags -->
        <div class="lib-detail-meta">
          <span v-if="doc.dynasty" class="lib-meta-tag">{{ doc.dynasty }}</span>
          <span v-if="doc.category" class="lib-meta-tag">{{ doc.category }}</span>
          <span v-if="doc.source_name" class="lib-meta-tag lib-meta-tag--source">{{ doc.source_name }}</span>
          <span v-if="doc.language" class="lib-meta-tag lib-meta-tag--source">{{ doc.language }}</span>
          <span v-if="doc.year" class="lib-meta-tag lib-meta-tag--source">{{ doc.year }}</span>
        </div>

        <!-- Compliance panel -->
        <section class="lib-panel">
          <h3>合规信息</h3>
          <div class="lib-compliance-grid">
            <div class="lib-field">
              <span class="lib-field-label">版权状态</span>
              <span class="lib-badge lib-badge-copyright">{{ COPYRIGHT_LABELS[doc.copyright_status] || doc.copyright_status }}</span>
            </div>
            <div class="lib-field">
              <span class="lib-field-label">许可类型</span>
              <span>{{ doc.license_type || '—' }}</span>
            </div>
            <div class="lib-field">
              <span class="lib-field-label">授权依据</span>
              <span class="lib-truncate">{{ doc.authorization_basis || '—' }}</span>
            </div>
            <div class="lib-field">
              <span class="lib-field-label">审核状态</span>
              <span class="lib-badge" :class="`lib-badge-review-${doc.review_status}`">{{ REVIEW_LABELS[doc.review_status] || doc.review_status }}</span>
            </div>
            <div class="lib-field">
              <span class="lib-field-label">智能检索</span>
              <span>{{ doc.rag_enabled ? '✅ 已启用' : '⛔ 未启用' }}</span>
            </div>
          </div>
          <div v-if="doc.withdrawn_at" class="lib-withdrawn-alert">
            ⚠️ 该文献已于 {{ new Date(doc.withdrawn_at).toLocaleString('zh-CN') }} 撤回 — {{ doc.withdraw_reason || '未提供原因' }}
          </div>
        </section>

        <!-- Stats panel: version info, OCR, citations, evidence -->
        <LibraryDocumentStatsPanel v-if="stats" :stats="stats" />

        <!-- Abstract -->
        <section v-if="doc.abstract" class="lib-panel">
          <h3>摘要</h3>
          <p class="lib-abstract-text">{{ doc.abstract }}</p>
        </section>

        <!-- Additional metadata -->
        <section class="lib-panel">
          <h3>详细元数据</h3>
          <div class="lib-meta-grid">
            <div class="lib-field"><span class="lib-field-label">拼音</span><span>{{ doc.title_pinyin || '—' }}</span></div>
            <div class="lib-field"><span class="lib-field-label">英文</span><span>{{ doc.title_english || '—' }}</span></div>
            <div class="lib-field"><span class="lib-field-label">页数</span><span>{{ doc.page_count || '—' }}</span></div>
            <div class="lib-field"><span class="lib-field-label">Checksum</span><span class="lib-mono">{{ doc.content_checksum || '—' }}</span></div>
            <div class="lib-field">
              <span class="lib-field-label">来源链接</span>
              <a v-if="safeSourceUrl" :href="safeSourceUrl" target="_blank" rel="noopener noreferrer" class="lib-external-link">查看来源</a>
              <span v-else>—</span>
            </div>
            <div class="lib-field"><span class="lib-field-label">创建时间</span><span>{{ doc.created_at ? new Date(doc.created_at).toLocaleString('zh-CN') : '—' }}</span></div>
            <div class="lib-field"><span class="lib-field-label">更新时间</span><span>{{ doc.updated_at ? new Date(doc.updated_at).toLocaleString('zh-CN') : '—' }}</span></div>
          </div>
        </section>

        <!-- Reader jump CTA -->
        <section class="lib-panel lib-panel--cta">
          <h3>全文阅读</h3>
          <p class="lib-cta-text">查看《{{ doc.title }}》的完整全文内容。</p>
          <button class="lib-read-btn lib-read-btn--block" @click="openReader">
            📖 进入全文阅读
          </button>
        </section>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * LibraryDetailPage — 文献详情页
 *
 * Data sources:
 *   GET /api/v1/documents/{id}        → document detail
 *   GET /api/v1/documents/{id}/stats   → citation/evidence/OCR stats
 *
 * Route: /library/:id
 *
 * Full text reading → redirects to /literature/:id (existing LiteratureDetailView)
 * which has the full reader experience (content_text, chapters, etc.)
 *
 * ref: docs/20-product/2010-task008-library-migration.md
 */
import { computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute, useRouter } from 'vue-router';
import ResearchPageHeader from '@/components/layout/ResearchPageHeader.vue';
import LoadingState from '@/components/common/LoadingState.vue';
import ErrorState from '@/components/common/ErrorState.vue';
import LibraryDocumentStatsPanel from '@/components/library/LibraryDocumentStatsPanel.vue';
import { useLibraryDetail } from '@/composables/useLibrary';
import { COPYRIGHT_LABELS, REVIEW_LABELS } from '@/types/library';
import type { Breadcrumb } from '@/components/layout/ResearchPageHeader.vue';

const { t } = useI18n();
const route = useRoute();
const router = useRouter();

const docId = computed(() => route.params.id as string);
const { doc, stats, loading, error, fetch } = useLibraryDetail(docId);

const breadcrumbs = computed<Breadcrumb[]>(() => [
  { label: 'Library', to: { name: 'library-search' } },
  { label: doc.value?.title || '文献详情' },
]);

const safeSourceUrl = computed(() => {
  const url = doc.value?.source_url;
  if (!url) return null;
  try {
    const parsed = new URL(url);
    if (['http:', 'https:'].includes(parsed.protocol)) return url;
  } catch {
    // invalid URL — reject
  }
  return null;
});

function openReader() {
  if (!doc.value) return;
  // Redirect to the existing LiteratureDetailView for full-text reading
  router.push(`/literature/${doc.value.id}`);
}

onMounted(() => fetch());
</script>

<style scoped>
.lib-detail-page {
  min-height: 100%;
}

.lib-detail-body {
  padding: 24px 32px;
  max-width: 900px;
}

/* Meta row */
.lib-detail-meta {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 20px;
}

.lib-meta-tag {
  font-size: 13px;
  padding: 3px 10px;
  background: var(--color-accent, #2b6cb0);
  color: white;
  border-radius: 4px;
}

.lib-meta-tag--source {
  background: var(--color-tag-bg, #edf2f7);
  color: var(--color-text-secondary, #4a5568);
}

/* Panels */
.lib-panel {
  margin-bottom: 24px;
  padding: 20px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 10px;
  background: var(--color-navbar-bg, #fff);
}

.lib-panel h3 {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary, #1a365d);
  margin: 0 0 12px;
  padding-bottom: 8px;
  border-bottom: 2px solid var(--color-accent, #2b6cb0);
}

.lib-panel--cta {
  text-align: center;
  border-color: var(--color-accent, #2b6cb0);
}

/* Compliance grid */
.lib-compliance-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 8px;
}

/* Metadata grid */
.lib-meta-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 8px;
}

.lib-field {
  display: flex;
  align-items: baseline;
  gap: 8px;
  font-size: 14px;
  color: var(--color-text-secondary, #4a5568);
}

.lib-field-label {
  font-weight: 600;
  min-width: 64px;
  color: var(--color-text-muted, #a0aec0);
  font-size: 13px;
  white-space: nowrap;
}

.lib-truncate {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 300px;
}

.lib-mono {
  font-family: monospace;
  font-size: 12px;
}

/* Badges */
.lib-badge {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 4px;
}

.lib-badge-copyright {
  background: var(--color-tag-bg, #edf2f7);
  color: var(--color-text-secondary, #4a5568);
}

.lib-badge-review-pending_review { background: #fefcbf; color: #975a16; }
.lib-badge-review-under_review { background: #bee3f8; color: #2a4365; }
.lib-badge-review-approved { background: #c6f6d5; color: #276749; }
.lib-badge-review-rejected { background: #fed7d7; color: #c53030; }

/* Withdrawn alert */
.lib-withdrawn-alert {
  margin-top: 12px;
  padding: 10px 14px;
  background: #fed7d7;
  border-radius: 6px;
  font-size: 13px;
  color: #c53030;
}

/* Abstract */
.lib-abstract-text {
  font-size: 14px;
  line-height: 1.8;
  color: var(--color-text-secondary, #4a5568);
}

/* Links */
.lib-external-link {
  color: var(--color-accent, #2b6cb0);
  text-decoration: underline;
}

/* Reader CTA */
.lib-cta-text {
  font-size: 14px;
  color: var(--color-text-muted, #718096);
  margin-bottom: 12px;
}

.lib-read-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 10px 24px;
  border: 1px solid var(--color-accent, #2b6cb0);
  border-radius: 8px;
  background: var(--color-navbar-bg, #fff);
  color: var(--color-accent, #2b6cb0);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}

.lib-read-btn:hover {
  background: var(--color-accent, #2b6cb0);
  color: white;
}

.lib-read-btn--block {
  display: flex;
  justify-content: center;
  width: 100%;
}

/* ---- Responsive ---- */
@media (max-width: 768px) {
  .lib-detail-body {
    padding: 16px 20px;
  }
}
</style>
