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
          <div v-if="doc.withdrawn_at" class="lib-withdrawn-alert" role="alert">
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
            <div class="lib-field"><span class="lib-field-label">版本</span><span class="lib-mono">版本信息不可用</span></div>
            <div class="lib-field"><span class="lib-field-label">内容校验</span><span class="lib-mono">{{ doc.content_checksum ? doc.content_checksum.slice(0, 16) : '—' }}</span></div>
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
  // Navigate to the canonical Reader route (Task 009 standalone route)
  router.push(`/reader/${doc.value.id}`);
}

onMounted(() => fetch());
</script>

<style scoped>
.lib-detail-page {
  min-height: 100%;
}

.lib-detail-body {
  padding: var(--space-6) var(--space-8);
  max-width: 900px;
}

/* Meta row */
.lib-detail-meta {
  display: flex;
  gap: var(--space-2);
  flex-wrap: wrap;
  margin-bottom: var(--space-5);
}

.lib-meta-tag {
  font-size: var(--text-sm);
  padding: 3px 10px;
  background: var(--color-accent);
  color: white;
  border-radius: var(--radius-sm);
}

.lib-meta-tag--source {
  background: var(--color-tag-bg);
  color: var(--color-text-secondary);
}

/* Panels */
.lib-panel {
  margin-bottom: var(--space-6);
  padding: var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  background: var(--color-surface);
}

.lib-panel h3 {
  font-size: 15px;
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
  margin: 0 0 var(--space-3);
  padding-bottom: var(--space-2);
  border-bottom: 2px solid var(--color-accent);
}

.lib-panel--cta {
  text-align: center;
  border-color: var(--color-accent);
}

/* Compliance grid */
.lib-compliance-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: var(--space-2);
}

/* Metadata grid */
.lib-meta-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: var(--space-2);
}

.lib-field {
  display: flex;
  align-items: baseline;
  gap: var(--space-2);
  font-size: var(--text-base);
  color: var(--color-text-secondary);
}

.lib-field-label {
  font-weight: var(--font-semibold);
  min-width: 64px;
  color: var(--color-text-muted);
  font-size: var(--text-sm);
  white-space: nowrap;
}

.lib-truncate {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 300px;
}

.lib-mono {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
}

/* Badges */
.lib-badge {
  font-size: var(--text-xs);
  padding: 2px 8px;
  border-radius: var(--radius-sm);
}

.lib-badge-copyright {
  background: var(--color-tag-bg);
  color: var(--color-text-secondary);
}

.lib-badge-review-pending_review { background: var(--color-warning-bg); color: var(--color-warning-text); }
.lib-badge-review-under_review { background: var(--color-info-bg); color: var(--color-info-text); }
.lib-badge-review-approved { background: var(--color-success-bg); color: var(--color-success-text); }
.lib-badge-review-rejected { background: var(--color-error-bg); color: var(--color-error-text); }

/* Withdrawn alert */
.lib-withdrawn-alert {
  margin-top: var(--space-3);
  padding: 10px 14px;
  background: var(--color-error-bg);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  color: var(--color-error-text);
}

/* Abstract */
.lib-abstract-text {
  font-size: var(--text-base);
  line-height: 1.8;
  color: var(--color-text-secondary);
}

/* Links */
.lib-external-link {
  color: var(--color-accent);
  text-decoration: underline;
}

/* Reader CTA */
.lib-cta-text {
  font-size: var(--text-base);
  color: var(--color-text-muted);
  margin-bottom: var(--space-3);
}

.lib-read-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: var(--btn-padding-lg);
  border: 1px solid var(--color-accent);
  border-radius: var(--btn-radius);
  background: var(--color-surface);
  color: var(--color-accent);
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  cursor: pointer;
  transition: all var(--transition-base);
}

.lib-read-btn:hover {
  background: var(--color-accent);
  color: white;
}

.lib-read-btn:focus-visible {
  background: var(--color-accent);
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
    padding: var(--space-4) var(--space-5);
  }
}
</style>
