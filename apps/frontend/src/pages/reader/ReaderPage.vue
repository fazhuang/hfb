<template>
  <div class="reader-page">
    <!-- Loading -->
    <LoadingState
      v-if="loading"
      message="正在加载全文..."
    />

    <!-- Error -->
    <ErrorState
      v-else-if="error"
      :message="error"
      @retry="fetchReaderData"
    />

    <!-- Document not found / empty -->
    <EmptyState
      v-else-if="!doc"
      title="文献未找到"
      description="无法加载该文献，可能已被撤回或您没有访问权限。"
      icon="📄"
    >
      <template #action>
        <button class="reader-back-btn" @click="backToLibrary">← 返回 Library</button>
      </template>
    </EmptyState>

    <!-- Reader content -->
    <template v-else>
      <!-- Header -->
      <ResearchPageHeader
        :title="doc.title"
        :description="headerDescription"
        :breadcrumbs="breadcrumbs"
      >
        <template #actions>
          <button class="reader-back-btn" @click="backToLibrary">
            ← 返回 Library
          </button>
        </template>
      </ResearchPageHeader>

      <div class="reader-body">
        <!-- Document Header: meta tags -->
        <div class="reader-meta-row">
          <span v-if="doc.dynasty" class="reader-meta-tag">{{ doc.dynasty }}</span>
          <span v-if="doc.category" class="reader-meta-tag">{{ doc.category }}</span>
          <span v-if="doc.source_name" class="reader-meta-tag reader-meta-tag--source">{{ doc.source_name }}</span>
        </div>

        <!-- Section: Metadata -->
        <section class="reader-panel">
          <h3>元数据</h3>
          <div class="reader-meta-grid">
            <div class="reader-field">
              <span class="reader-field-label">作者</span>
              <span>{{ doc.author_id || '—' }}</span>
            </div>
            <div class="reader-field">
              <span class="reader-field-label">朝代</span>
              <span>{{ doc.dynasty || '—' }}</span>
            </div>
            <div class="reader-field">
              <span class="reader-field-label">分类</span>
              <span>{{ doc.category || '—' }}</span>
            </div>
            <div class="reader-field">
              <span class="reader-field-label">年份</span>
              <span>{{ doc.year || '—' }}</span>
            </div>
            <div class="reader-field">
              <span class="reader-field-label">语言</span>
              <span>{{ doc.language }}</span>
            </div>
            <div class="reader-field">
              <span class="reader-field-label">页数</span>
              <span>{{ doc.page_count || '—' }}</span>
            </div>
            <div class="reader-field">
              <span class="reader-field-label">来源</span>
              <a v-if="safeSourceUrl" :href="safeSourceUrl" target="_blank" rel="noopener noreferrer" class="reader-external-link">查看来源</a>
              <span v-else>—</span>
            </div>
            <div class="reader-field">
              <span class="reader-field-label">拼音</span>
              <span>{{ doc.title_pinyin || '—' }}</span>
            </div>
            <div class="reader-field">
              <span class="reader-field-label">英文</span>
              <span>{{ doc.title_english || '—' }}</span>
            </div>
            <div class="reader-field">
              <span class="reader-field-label">版本来源</span>
              <span>{{ doc.source_name || '—' }}</span>
            </div>
          </div>
        </section>

        <!-- Section: Abstract -->
        <section v-if="doc.abstract" class="reader-panel">
          <h3>摘要</h3>
          <p class="reader-abstract-text">{{ doc.abstract }}</p>
        </section>

        <!-- Section: Original Text -->
        <section v-if="doc.content_text" class="reader-panel">
          <h3>原文</h3>
          <div class="reader-text-controls">
            <button
              class="reader-expand-btn"
              @click="textExpanded = !textExpanded"
            >
              {{ textExpanded ? '收起全文' : '展开全文' }}
            </button>
          </div>
          <div
            ref="textContainerRef"
            :class="['reader-content-text', { 'reader-content-text--expanded': textExpanded }]"
          >{{ doc.content_text }}</div>
        </section>

        <!-- Section: Paragraph Navigation (parsed from content_text) -->
        <section v-if="paragraphs.length > 0" class="reader-panel">
          <h3>段落导航</h3>
          <div class="reader-paragraph-list">
            <div
              v-for="(para, idx) in paragraphs"
              :key="idx"
              class="reader-paragraph-item"
              :class="{ 'reader-paragraph-item--active': activeParagraph === idx }"
              @click="jumpToParagraph(idx)"
            >
              <span class="reader-paragraph-label">{{ para.label }}</span>
              <span class="reader-paragraph-preview">{{ para.preview }}</span>
            </div>
          </div>
        </section>

        <!-- Section: OCR Text -->
        <section v-if="ocrChunks.length > 0" class="reader-panel">
          <h3>OCR 文本</h3>
          <p class="reader-section-hint">
            OCR 分块: {{ ocrChunks.length }} 段 ·
            平均可信度: {{ avgOcrConfidence }}%
          </p>
          <div
            v-for="chunk in ocrChunks"
            :key="chunk.chunk_index"
            :id="`ocr-chunk-${chunk.chunk_index}`"
            class="reader-ocr-chunk"
            :class="{ 'reader-highlight': highlightedOcrChunk === chunk.chunk_index }"
          >
            <div class="reader-ocr-chunk-header">
              <span class="reader-ocr-chunk-idx">#{{ chunk.chunk_index }}</span>
              <span v-if="chunk.page_number" class="reader-ocr-chunk-page">页 {{ chunk.page_number }}</span>
              <span v-if="chunk.ocr_confidence != null" class="reader-ocr-chunk-confidence">
                可信度 {{ (chunk.ocr_confidence * 100).toFixed(1) }}%
              </span>
            </div>
            <div class="reader-ocr-chunk-text">{{ chunk.content }}</div>
          </div>
        </section>

        <!-- Section: Translation (from linked passages) -->
        <section v-if="passagesWithTranslation.length > 0" class="reader-panel">
          <h3>现代汉语翻译</h3>
          <div
            v-for="passage in passagesWithTranslation"
            :key="passage.id"
            :id="`passage-${passage.id}`"
            class="reader-translation-item"
            :class="{ 'reader-highlight': highlightedPassageId === passage.id }"
          >
            <div class="reader-translation-header">
              <span class="reader-translation-order">#{{ passage.order }}</span>
            </div>
            <div class="reader-translation-original">{{ passage.content_text }}</div>
            <div class="reader-translation-text">{{ passage.translation }}</div>
          </div>
        </section>

        <!-- Section: Citations -->
        <section v-if="citations.length > 0" class="reader-panel">
          <h3>引文定位</h3>
          <div
            v-for="citation in citations"
            :key="citation.id"
            :id="`citation-${citation.id}`"
            class="reader-citation-item"
            :class="{ 'reader-highlight': highlightedCitationId === citation.id }"
          >
            <div v-if="citation.quote_text" class="reader-citation-quote">
              "{{ citation.quote_text }}"
            </div>
            <div v-if="citation.note" class="reader-citation-note">
              {{ citation.note }}
            </div>
            <div class="reader-citation-meta">
              <span class="reader-citation-target">{{ citation.target_type }}</span>
            </div>
          </div>
        </section>
        <EmptyState
          v-else
          title="暂无引文"
          description="该文献尚未被任何研究引用。"
          icon="📎"
        />

        <!-- Section: Evidence -->
        <section v-if="evidences.length > 0" class="reader-panel">
          <h3>证据定位</h3>
          <div
            v-for="evidence in evidences"
            :key="evidence.id"
            :id="`evidence-${evidence.id}`"
            class="reader-evidence-item"
            :class="{ 'reader-highlight': highlightedEvidenceId === evidence.id }"
          >
            <div class="reader-evidence-level">
              证据等级: L{{ evidence.evidence_level }}
            </div>
            <div class="reader-evidence-desc">{{ evidence.description }}</div>
            <div v-if="evidence.source_passage_id" class="reader-evidence-passage">
              关联段落: {{ evidence.source_passage_id }}
            </div>
          </div>
        </section>
        <EmptyState
          v-else
          title="暂无证据"
          description="该文献尚未绑定学术论据。"
          icon="🔍"
        />
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
/**
 * ReaderPage — 全文阅读页面
 *
 * Route: /library/:id/reader
 *
 * Aggregates all reader data from GET /api/v1/documents/{id}/reader:
 *   - Document metadata
 *   - Original text (content_text)
 *   - OCR chunks
 *   - Linked passages with translation
 *   - Citations
 *   - Evidence
 *
 * ref: docs/20-product/2011-task009-reader-refactor.md
 */
import { computed, ref, onMounted, nextTick } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import ResearchPageHeader from '@/components/layout/ResearchPageHeader.vue';
import LoadingState from '@/components/common/LoadingState.vue';
import ErrorState from '@/components/common/ErrorState.vue';
import EmptyState from '@/components/common/EmptyState.vue';
import api from '@/api/client';
import type { Breadcrumb } from '@/components/layout/ResearchPageHeader.vue';

const route = useRoute();
const router = useRouter();

// ---- Types ----

interface ReaderDocument {
  id: string;
  title: string;
  title_pinyin?: string | null;
  title_english?: string | null;
  author_id?: string | null;
  dynasty?: string | null;
  year?: number | null;
  category?: string | null;
  abstract?: string | null;
  content_text?: string | null;
  source_url?: string | null;
  page_count?: number | null;
  language: string;
  source_name?: string | null;
}

interface OcrChunk {
  chunk_index: number;
  content: string;
  page_number?: number | null;
  paragraph_index?: number | null;
  ocr_confidence?: number | null;
}

interface ReaderPassage {
  id: string;
  content_text: string;
  translation?: string | null;
  notes?: string | null;
  order: number;
  tags?: string | null;
}

interface ReaderCitation {
  id: string;
  quote_text?: string | null;
  note?: string | null;
  target_type: string;
  target_id: string;
  evidence_id: string;
}

interface ReaderEvidence {
  id: string;
  description: string;
  evidence_level: number;
  source_passage_id?: string | null;
  source_ref_id?: string | null;
}

interface ReaderData {
  document: ReaderDocument;
  ocr_chunks: OcrChunk[];
  passages: ReaderPassage[];
  citations: ReaderCitation[];
  evidences: ReaderEvidence[];
}

// ---- Paragraph navigation ----

interface ParagraphNavItem {
  label: string;
  preview: string;
  offset: number;
}

// ---- State ----

const loading = ref(false);
const error = ref<string | null>(null);
const doc = ref<ReaderDocument | null>(null);
const ocrChunks = ref<OcrChunk[]>([]);
const passages = ref<ReaderPassage[]>([]);
const citations = ref<ReaderCitation[]>([]);
const evidences = ref<ReaderEvidence[]>([]);

const textExpanded = ref(false);
const textContainerRef = ref<HTMLElement | null>(null);
const activeParagraph = ref(-1);
const highlightedOcrChunk = ref(-1);
const highlightedPassageId = ref<string | null>(null);
const highlightedCitationId = ref<string | null>(null);
const highlightedEvidenceId = ref<string | null>(null);

// ---- Computed ----

const docId = computed(() => route.params.id as string);

const breadcrumbs = computed<Breadcrumb[]>(() => [
  { label: 'Library', to: { name: 'library-search' } },
  { label: doc.value?.title || '文献详情', to: { name: 'library-detail', params: { id: docId.value } } },
  { label: '全文阅读' },
]);

const headerDescription = computed(() => {
  const parts: string[] = [];
  if (doc.value?.dynasty) parts.push(doc.value.dynasty);
  if (doc.value?.category) parts.push(doc.value.category);
  return parts.join(' · ') || '';
});

const safeSourceUrl = computed(() => {
  const url = doc.value?.source_url;
  if (!url) return null;
  try {
    const parsed = new URL(url);
    if (['http:', 'https:'].includes(parsed.protocol)) return url;
  } catch {
    // invalid URL
  }
  return null;
});

const avgOcrConfidence = computed(() => {
  if (ocrChunks.value.length === 0) return '—';
  const total = ocrChunks.value.reduce(
    (sum, c) => sum + (c.ocr_confidence ?? 0), 0,
  );
  return ((total / ocrChunks.value.length) * 100).toFixed(1);
});

const passagesWithTranslation = computed(() =>
  passages.value.filter((p) => p.translation),
);

const paragraphs = computed<ParagraphNavItem[]>(() => {
  const text = doc.value?.content_text;
  if (!text) return [];
  return parseParagraphNav(text);
});

// ---- Data fetching ----

async function fetchReaderData() {
  loading.value = true;
  error.value = null;
  try {
    const { data } = await api.get(`/api/v1/documents/${docId.value}/reader`);
    const body: ReaderData = data.data ?? data;
    doc.value = body.document;
    ocrChunks.value = body.ocr_chunks ?? [];
    passages.value = body.passages ?? [];
    citations.value = body.citations ?? [];
    evidences.value = body.evidences ?? [];
  } catch (e: unknown) {
    const errMsg =
      (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
      (e as Error).message ??
      '加载失败';
    error.value = errMsg;
  } finally {
    loading.value = false;
  }
}

// ---- Paragraph navigation ----

function parseParagraphNav(contentText: string): ParagraphNavItem[] {
  // Match 卷 markers for classical Chinese texts
  const re = /(?:^|\n)\s*[鍼灸甲乙經]*\s*(卷[一二三四五六七八九十百]+)(?:·([^\n]{2,40}))?/g;
  const items: ParagraphNavItem[] = [];
  let m: RegExpExecArray | null;
  while ((m = re.exec(contentText)) !== null) {
    const label = m[1] + (m[2] ? `·${m[2]}` : '');
    const start = Math.max(0, m.index + m[0].length);
    const preview = contentText.substring(start, start + 40).replace(/\s+/g, '');
    if (!items.find((it) => it.label === label)) {
      items.push({ label, preview, offset: m.index });
    }
  }
  return items.slice(0, 50);
}

function jumpToParagraph(idx: number) {
  activeParagraph.value = idx;
  textExpanded.value = true;
  const el = textContainerRef.value;
  if (!el) return;
  const para = paragraphs.value[idx];
  if (!para) return;
  // Use offset ratio for scroll position
  const total = (el.textContent || '').length || el.scrollHeight;
  const ratio = Math.min(para.offset / Math.max(total, 1), 1);
  el.scrollTop = ratio * el.scrollHeight;
}

// ---- Citation/Evidence highlight ----

function scrollToElement(elementId: string) {
  nextTick(() => {
    const el = window.document.getElementById(elementId);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  });
}

function highlightCitation(citationId: string) {
  highlightedCitationId.value = citationId;
  scrollToElement(`citation-${citationId}`);
  // Clear highlight after 3s
  setTimeout(() => { highlightedCitationId.value = null; }, 3000);
}

function highlightEvidence(evidenceId: string) {
  highlightedEvidenceId.value = evidenceId;
  scrollToElement(`evidence-${evidenceId}`);
  setTimeout(() => { highlightedEvidenceId.value = null; }, 3000);
}

function highlightOcrChunk(chunkIndex: number) {
  highlightedOcrChunk.value = chunkIndex;
  scrollToElement(`ocr-chunk-${chunkIndex}`);
  setTimeout(() => { highlightedOcrChunk.value = -1; }, 3000);
}

function highlightPassage(passageId: string) {
  highlightedPassageId.value = passageId;
  scrollToElement(`passage-${passageId}`);
  setTimeout(() => { highlightedPassageId.value = null; }, 3000);
}

// ---- Navigation ----

function backToLibrary() {
  if (doc.value) {
    router.push({ name: 'library-detail', params: { id: doc.value.id } });
  } else {
    router.push({ name: 'library-search' });
  }
}

// ---- Lifecycle ----

onMounted(() => {
  fetchReaderData();
});

// Expose highlight functions for external use (e.g. from Library page)
defineExpose({
  highlightCitation,
  highlightEvidence,
  highlightOcrChunk,
  highlightPassage,
});
</script>

<style scoped>
.reader-page {
  min-height: 100%;
}

.reader-body {
  padding: 24px 32px;
  max-width: 900px;
}

/* Meta row */
.reader-meta-row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 20px;
}

.reader-meta-tag {
  font-size: 13px;
  padding: 3px 10px;
  background: var(--color-accent, #2b6cb0);
  color: white;
  border-radius: 4px;
}

.reader-meta-tag--source {
  background: var(--color-tag-bg, #edf2f7);
  color: var(--color-text-secondary, #4a5568);
}

/* Panels */
.reader-panel {
  margin-bottom: 24px;
  padding: 20px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 10px;
  background: var(--color-navbar-bg, #fff);
}

.reader-panel h3 {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary, #1a365d);
  margin: 0 0 12px;
  padding-bottom: 8px;
  border-bottom: 2px solid var(--color-accent, #2b6cb0);
}

.reader-section-hint {
  font-size: 12px;
  color: var(--color-text-muted, #718096);
  margin: -8px 0 12px;
}

/* Metadata grid */
.reader-meta-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 8px;
}

.reader-field {
  display: flex;
  align-items: baseline;
  gap: 8px;
  font-size: 14px;
  color: var(--color-text-secondary, #4a5568);
}

.reader-field-label {
  font-weight: 600;
  min-width: 56px;
  color: var(--color-text-muted, #a0aec0);
  font-size: 13px;
  white-space: nowrap;
}

/* Abstract */
.reader-abstract-text {
  font-size: 14px;
  line-height: 1.8;
  color: var(--color-text-secondary, #4a5568);
}

/* Original text */
.reader-text-controls {
  margin-bottom: 12px;
}

.reader-expand-btn {
  padding: 4px 12px;
  font-size: 12px;
  border: 1px solid var(--color-accent, #2b6cb0);
  color: var(--color-accent, #2b6cb0);
  background: transparent;
  border-radius: 4px;
  cursor: pointer;
}

.reader-expand-btn:hover {
  background: var(--color-active, #ebf8ff);
}

.reader-content-text {
  font-size: 16px;
  line-height: 2;
  color: var(--color-text-primary, #1a365d);
  white-space: pre-wrap;
  max-height: 400px;
  overflow-y: auto;
  border-top: 1px solid var(--color-border, #e2e8f0);
  padding-top: 12px;
}

.reader-content-text--expanded {
  max-height: none;
  overflow-y: visible;
}

/* Paragraph navigation */
.reader-paragraph-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-height: 400px;
  overflow-y: auto;
}

.reader-paragraph-item {
  display: flex;
  gap: 12px;
  padding: 8px 12px;
  border-bottom: 1px solid var(--color-border, #e2e8f0);
  font-size: 13px;
  cursor: pointer;
  border-radius: 4px;
  transition: background 0.15s;
}

.reader-paragraph-item:hover {
  background: var(--color-hover, #edf2f7);
}

.reader-paragraph-item--active {
  background: var(--color-active, #ebf8ff);
  border-color: var(--color-accent, #2b6cb0);
}

.reader-paragraph-label {
  font-weight: 600;
  color: var(--color-accent, #2b6cb0);
  min-width: 80px;
  white-space: nowrap;
}

.reader-paragraph-preview {
  color: var(--color-text-muted, #718096);
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* OCR chunks */
.reader-ocr-chunk {
  margin-bottom: 16px;
  padding: 12px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 8px;
  background: var(--color-page-bg, #f7fafc);
  transition: border-color 0.3s, box-shadow 0.3s;
}

.reader-ocr-chunk-header {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 8px;
  font-size: 12px;
  color: var(--color-text-muted, #a0aec0);
}

.reader-ocr-chunk-idx {
  font-weight: 600;
  color: var(--color-accent, #2b6cb0);
}

.reader-ocr-chunk-page {
  font-weight: 500;
}

.reader-ocr-chunk-confidence {
  font-weight: 500;
  color: var(--color-text-muted, #718096);
}

.reader-ocr-chunk-text {
  font-size: 14px;
  line-height: 1.8;
  color: var(--color-text-secondary, #4a5568);
  white-space: pre-wrap;
}

/* Translation */
.reader-translation-item {
  margin-bottom: 20px;
  padding: 16px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 8px;
  transition: border-color 0.3s, box-shadow 0.3s;
}

.reader-translation-header {
  margin-bottom: 12px;
}

.reader-translation-order {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-accent, #2b6cb0);
  padding: 2px 8px;
  background: var(--color-active, #ebf8ff);
  border-radius: 4px;
}

.reader-translation-original {
  font-size: 15px;
  line-height: 1.9;
  color: var(--color-text-primary, #1a365d);
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px dashed var(--color-border, #e2e8f0);
}

.reader-translation-text {
  font-size: 14px;
  line-height: 1.8;
  color: var(--color-text-secondary, #4a5568);
}

/* Citation */
.reader-citation-item {
  margin-bottom: 16px;
  padding: 14px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 8px;
  transition: border-color 0.3s, box-shadow 0.3s;
}

.reader-citation-quote {
  font-size: 14px;
  font-style: italic;
  color: var(--color-text-primary, #1a365d);
  margin-bottom: 6px;
  line-height: 1.6;
}

.reader-citation-note {
  font-size: 13px;
  color: var(--color-text-secondary, #4a5568);
  margin-bottom: 6px;
}

.reader-citation-meta {
  font-size: 11px;
  color: var(--color-text-muted, #a0aec0);
  text-transform: uppercase;
}

/* Evidence */
.reader-evidence-item {
  margin-bottom: 16px;
  padding: 14px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 8px;
  transition: border-color 0.3s, box-shadow 0.3s;
}

.reader-evidence-level {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-accent, #2b6cb0);
  margin-bottom: 6px;
}

.reader-evidence-desc {
  font-size: 14px;
  line-height: 1.6;
  color: var(--color-text-primary, #1a365d);
  margin-bottom: 6px;
}

.reader-evidence-passage {
  font-size: 11px;
  color: var(--color-text-muted, #a0aec0);
  font-family: monospace;
}

/* Highlight */
.reader-highlight {
  border-color: var(--color-accent, #2b6cb0) !important;
  box-shadow: 0 0 0 2px rgba(43, 108, 176, 0.2);
}

/* Back button */
.reader-back-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 8px;
  background: var(--color-navbar-bg, #fff);
  color: var(--color-text-secondary, #4a5568);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
}

.reader-back-btn:hover {
  background: var(--color-hover, #edf2f7);
  color: var(--color-accent, #2b6cb0);
}

/* Links */
.reader-external-link {
  color: var(--color-accent, #2b6cb0);
  text-decoration: underline;
}

/* Responsive */
@media (max-width: 768px) {
  .reader-body {
    padding: 16px 20px;
  }
}
</style>
