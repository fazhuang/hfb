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

    <!-- Document not found -->
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

        <!-- Section: Original Text (rendered from backend chunks) -->
        <section v-if="chunks.length > 0" class="reader-panel">
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
          >
            <div
              v-for="chunk in chunks"
              :key="chunk.id"
              :id="`chunk-${chunk.id}`"
              :ref="(el) => registerChunkEl(chunk.id, el)"
              class="reader-chunk-paragraph"
              :class="{ 'reader-highlight': highlightedChunkIds.has(chunk.id) }"
              :data-chunk-index="chunk.chunk_index"
              :data-paragraph-index="chunk.paragraph_index"
              :data-page-number="chunk.page_number"
            >
              <span v-if="chunk.page_number" class="reader-chunk-page-marker">
                [页{{ chunk.page_number }}]
              </span>
              {{ chunk.content }}
            </div>
          </div>
        </section>

        <!-- Section: Paragraph navigation (from backend chunks, not regex) -->
        <section v-if="chunks.length > 0" class="reader-panel">
          <h3>段落导航</h3>
          <div class="reader-paragraph-list">
            <div
              v-for="chunk in chunks"
              :key="`nav-${chunk.id}`"
              class="reader-paragraph-item"
              :class="{ 'reader-paragraph-item--active': highlightedChunkIds.has(chunk.id) }"
              @click="scrollToChunk(chunk.id)"
            >
              <span class="reader-paragraph-label">
                段 {{ chunk.paragraph_index != null ? chunk.paragraph_index + 1 : chunk.chunk_index + 1 }}
              </span>
              <span class="reader-paragraph-preview">{{ chunkPreview(chunk.content) }}</span>
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
            :key="`ocr-${chunk.id}`"
            :id="`ocr-chunk-${chunk.id}`"
            class="reader-ocr-chunk"
            :class="{ 'reader-highlight': highlightedChunkIds.has(chunk.id) }"
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
            :key="`trans-${passage.id}`"
            :id="`passage-${passage.id}`"
            class="reader-translation-item"
            :class="{ 'reader-highlight': highlightedPassageIds.has(passage.id) }"
          >
            <div class="reader-translation-header">
              <span class="reader-translation-order">#{{ passage.order }}</span>
            </div>
            <div class="reader-translation-original">{{ passage.content_text }}</div>
            <div class="reader-translation-text">{{ passage.translation }}</div>
          </div>
        </section>
        <section v-else-if="passages.length > 0" class="reader-panel">
          <h3>现代汉语翻译</h3>
          <p class="reader-section-hint">该文献的段落暂无现代汉语翻译。</p>
        </section>

        <!-- Section: Citations -->
        <section v-if="citations.length > 0" class="reader-panel">
          <h3>引文定位</h3>
          <div
            v-for="citation in citations"
            :key="`cit-${citation.id}`"
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
              <button
                v-if="citation.anchor_chunk_ids && citation.anchor_chunk_ids.length > 0"
                class="reader-anchor-btn"
                @click.stop="scrollToCitationAnchor(citation)"
              >
                📍 定位到原文
              </button>
              <span v-else class="reader-no-anchor">无法定位到原文</span>
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
            :key="`ev-${evidence.id}`"
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
            <div class="reader-evidence-actions">
              <button
                v-if="evidence.anchor_chunk_ids && evidence.anchor_chunk_ids.length > 0"
                class="reader-anchor-btn"
                @click.stop="scrollToEvidenceAnchor(evidence)"
              >
                📍 定位到原文
              </button>
              <span v-else class="reader-no-anchor">无法定位到原文</span>
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
 * Route: /reader/:id  (standalone route, NOT under Library module)
 *
 * Data: GET /api/v1/documents/{id}/reader
 *   - Document metadata
 *   - Chunks (stable backend IDs for anchoring)
 *   - OCR chunks
 *   - Linked passages with translation
 *   - Citations with anchor_chunk_ids
 *   - Evidence with anchor_chunk_ids
 *
 * ref: docs/20-product/2017-task009-reader-refactor.md
 */
import { computed, ref, onMounted, onUnmounted, watch, nextTick } from 'vue';
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

interface ReaderChunk {
  id: string;
  chunk_index: number;
  content: string;
  page_number?: number | null;
  paragraph_index?: number | null;
  passage_id?: string | null;
}

interface OcrChunk {
  id: string;
  chunk_index: number;
  content: string;
  page_number?: number | null;
  paragraph_index?: number | null;
  ocr_confidence?: number | null;
  passage_id?: string | null;
  match_method?: string | null;
  quote_bbox?: Record<string, unknown> | null;
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
  anchor_chunk_ids: string[];
  anchor_passage_ids: string[];
}

interface ReaderEvidence {
  id: string;
  description: string;
  evidence_level: number;
  source_passage_id?: string | null;
  source_ref_id?: string | null;
  anchor_chunk_ids: string[];
}

interface ReaderData {
  document: ReaderDocument;
  ocr_chunks: OcrChunk[];
  passages: ReaderPassage[];
  chunks: ReaderChunk[];
  citations: ReaderCitation[];
  evidences: ReaderEvidence[];
}

// ---- State ----

const loading = ref(false);
const error = ref<string | null>(null);
const doc = ref<ReaderDocument | null>(null);
const ocrChunks = ref<OcrChunk[]>([]);
const passages = ref<ReaderPassage[]>([]);
const chunks = ref<ReaderChunk[]>([]);
const citations = ref<ReaderCitation[]>([]);
const evidences = ref<ReaderEvidence[]>([]);

const textExpanded = ref(false);
const textContainerRef = ref<HTMLElement | null>(null);

// Map of chunk id -> DOM element for scroll anchoring
const chunkElMap = ref<Map<string, HTMLElement>>(new Map());
function registerChunkEl(id: string, el: unknown) {
  const map = chunkElMap.value;
  if (el instanceof HTMLElement) {
    map.set(id, el);
  } else {
    map.delete(id);
  }
}

const highlightedChunkIds = ref<Set<string>>(new Set());
const highlightedPassageIds = ref<Set<string>>(new Set());
const highlightedCitationId = ref<string | null>(null);
const highlightedEvidenceId = ref<string | null>(null);

// Request serial for race-condition protection
let reqSerial = 0;
let mounted = false;

// ---- Computed ----

const docId = computed(() => route.params.id as string);

const breadcrumbs = computed<Breadcrumb[]>(() => [
  { label: 'Library', to: { name: 'library-search' } },
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

// ---- Data fetching ----

async function fetchReaderData() {
  const serial = ++reqSerial;
  loading.value = true;
  error.value = null;
  try {
    const { data } = await api.get(`/api/v1/documents/${docId.value}/reader`);
    if (serial !== reqSerial || !mounted) return;
    const body: ReaderData = data.data ?? data;
    doc.value = body.document;
    ocrChunks.value = body.ocr_chunks ?? [];
    passages.value = body.passages ?? [];
    chunks.value = body.chunks ?? [];
    citations.value = body.citations ?? [];
    evidences.value = body.evidences ?? [];

    // Restore anchor from URL hash
    nextTick(() => restoreAnchorFromUrl());
  } catch (e: unknown) {
    if (serial !== reqSerial || !mounted) return;
    const status = (e as { response?: { status?: number } })?.response?.status;
    const detail =
      (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
      (e as Error).message ??
      '加载失败';
    if (status === 401 || status === 403) {
      error.value = '您没有权限访问该文献。';
    } else if (status === 404) {
      error.value = '文献未找到，可能已被撤回或不存在。';
    } else if (status === 422) {
      error.value = `请求参数错误: ${detail}`;
    } else {
      error.value = `服务器错误 (${status || '未知'}): ${detail}`;
    }
  } finally {
    if (serial === reqSerial && mounted) {
      loading.value = false;
    }
  }
}

// ---- Chunk helpers ----

function chunkPreview(content: string): string {
  return content.replace(/\s+/g, '').substring(0, 40);
}

// ---- Anchor resolution ----

function resolveAnchorChunkIds(citationOrEvidence: ReaderCitation | ReaderEvidence): string[] {
  return (citationOrEvidence as { anchor_chunk_ids?: string[] }).anchor_chunk_ids ?? [];
}

// ---- Scroll & highlight ----

function scrollToChunk(chunkId: string) {
  textExpanded.value = true;
  highlightChunkIds([chunkId]);
  nextTick(() => {
    const el = chunkElMap.value.get(chunkId);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  });
}

function highlightChunkIds(ids: string[]) {
  const set = new Set(ids);
  highlightedChunkIds.value = set;
  if (ids.length > 0) {
    setTimeout(() => { highlightedChunkIds.value = new Set(); }, 3000);
  }
}

function scrollToCitationAnchor(citation: ReaderCitation) {
  const anchorIds = resolveAnchorChunkIds(citation);
  if (anchorIds.length === 0) return;
  highlightedCitationId.value = citation.id;
  highlightChunkIds(anchorIds);
  // Scroll to first anchor chunk
  const firstId = anchorIds[0]!;
  nextTick(() => {
    const el = chunkElMap.value.get(firstId);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  });
  setTimeout(() => { highlightedCitationId.value = null; }, 3000);
}

function scrollToEvidenceAnchor(evidence: ReaderEvidence) {
  const anchorIds = resolveAnchorChunkIds(evidence);
  if (anchorIds.length === 0) return;
  highlightedEvidenceId.value = evidence.id;
  highlightChunkIds(anchorIds);
  const firstId = anchorIds[0]!;
  nextTick(() => {
    const el = chunkElMap.value.get(firstId);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  });
  setTimeout(() => { highlightedEvidenceId.value = null; }, 3000);
}

// ---- URL anchor restore ----

function restoreAnchorFromUrl() {
  const hash = route.hash?.replace('#', '');
  if (!hash) return;
  if (hash.startsWith('citation-')) {
    const citId = hash.replace('citation-', '');
    const cit = citations.value.find((c) => c.id === citId);
    if (cit) scrollToCitationAnchor(cit);
  } else if (hash.startsWith('evidence-')) {
    const evId = hash.replace('evidence-', '');
    const ev = evidences.value.find((e) => e.id === evId);
    if (ev) scrollToEvidenceAnchor(ev);
  } else if (hash.startsWith('chunk-')) {
    const chunkId = hash.replace('chunk-', '');
    scrollToChunk(chunkId);
  }
}

// ---- Navigation ----

function backToLibrary() {
  router.push({ name: 'library-search' });
}

// ---- Lifecycle ----

mounted = true;
onMounted(() => {
  fetchReaderData();
});

onUnmounted(() => {
  mounted = false;
});

// Watch route param changes for same-component navigation
watch(
  () => route.params.id,
  (newId, oldId) => {
    if (newId !== oldId) {
      // Clear all state before fetching new document
      doc.value = null;
      chunks.value = [];
      ocrChunks.value = [];
      passages.value = [];
      citations.value = [];
      evidences.value = [];
      highlightedChunkIds.value = new Set();
      highlightedPassageIds.value = new Set();
      highlightedCitationId.value = null;
      highlightedEvidenceId.value = null;
      textExpanded.value = false;
      error.value = null;
      chunkElMap.value = new Map();
      fetchReaderData();
    }
  },
);

// Watch URL hash changes for anchor restore
watch(
  () => route.hash,
  () => {
    if (!loading.value) restoreAnchorFromUrl();
  },
);
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
  max-height: 400px;
  overflow-y: auto;
  border-top: 1px solid var(--color-border, #e2e8f0);
  padding-top: 12px;
}

.reader-content-text--expanded {
  max-height: none;
  overflow-y: visible;
}

.reader-chunk-paragraph {
  padding: 8px 0;
  border-bottom: 1px dashed var(--color-border, #e2e8f0);
  font-size: 16px;
  line-height: 2;
  color: var(--color-text-primary, #1a365d);
  white-space: pre-wrap;
  transition: background 0.3s, border-color 0.3s;
  border-radius: 4px;
  padding: 8px;
}

.reader-chunk-paragraph:last-child {
  border-bottom: none;
}

.reader-chunk-page-marker {
  font-size: 11px;
  color: var(--color-text-muted, #a0aec0);
  margin-right: 8px;
  user-select: none;
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
  display: flex;
  align-items: center;
  gap: 12px;
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
  margin-bottom: 8px;
}

.reader-evidence-actions {
  margin-top: 4px;
}

/* Anchor button */
.reader-anchor-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 10px;
  border: 1px solid var(--color-accent, #2b6cb0);
  border-radius: 4px;
  background: var(--color-active, #ebf8ff);
  color: var(--color-accent, #2b6cb0);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
}

.reader-anchor-btn:hover {
  background: var(--color-accent, #2b6cb0);
  color: white;
}

.reader-no-anchor {
  font-size: 12px;
  color: var(--color-text-muted, #a0aec0);
  font-style: italic;
}

/* Highlight */
.reader-highlight {
  background: rgba(43, 108, 176, 0.08) !important;
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
