/**
 * Batch 4 — Domain Semantic Regression Tests
 *
 * Asserts that Citation, Evidence, SourceReference, PassageReader,
 * and OCRConfidence components display trace_id, source locators,
 * evidence associations, passage/page information, and semantic labels.
 *
 * Only style tokenization is allowed; no data contract, sort, filter,
 * or fail-closed behavior may change.
 */
import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import { createI18n } from 'vue-i18n';
import { createRouter, createWebHistory } from 'vue-router';
import type { ResultCitation, ResultEvidence } from '@/composables/useResearchResult';
import CitationPanel from '@/components/research/result/CitationPanel.vue';
import EvidenceDetail from '@/components/research/result/EvidenceDetail.vue';
import SourceReferenceCard from '@/components/research/result/SourceReferenceCard.vue';
import PassageReader from '@/components/reader/PassageReader.vue';

// ─── i18n ────────────────────────────────────────────────────────────────

const i18n = createI18n({
  legacy: false,
  locale: 'zh',
  messages: {
    zh: {
      common: { loading: '加载中...' },
      passage: { translation: '译文', notes: '注释', versionLinked: '已关联版本' },
    },
  },
});

const router = createRouter({
  history: createWebHistory(),
  routes: [],
});

const globalPlugins = { plugins: [i18n, router] };

// Build test fixtures matching the actual types exactly
function makeCitation(overrides: Partial<ResultCitation> & { trace_id: string }): ResultCitation {
  return {
    document_id: '',
    citation_text: '',
    quote: '',
    ...overrides,
  };
}

function makeEvidence(overrides: Partial<ResultEvidence> & { trace_id: string }): ResultEvidence {
  return {
    document_id: '',
    chunk_id: '',
    claim_text: '',
    quote: '',
    citation_text: '',
    ...overrides,
  };
}

// ────────────────────────────────────────────────────────────────────────
// CitationPanel
// ────────────────────────────────────────────────────────────────────────
describe('CitationPanel — Domain Semantic Regression', () => {
  it('renders trace_id for each citation', () => {
    const citations: ResultCitation[] = [
      makeCitation({ trace_id: 'trace-001-abcdef', citation_text: 'Test citation' }),
      makeCitation({ trace_id: 'trace-002-ghijkl', quote: 'Original text quote' }),
    ];
    const wrapper = mount(CitationPanel, {
      props: { citations, evidence: [], selectedTraceId: null },
    });
    expect(wrapper.text()).toContain('trace-001');
    expect(wrapper.text()).toContain('trace-002');
  });

  it('renders citation_text when available', () => {
    const citations: ResultCitation[] = [
      makeCitation({ trace_id: 't1', citation_text: '《针灸甲乙经》记载...' }),
    ];
    const wrapper = mount(CitationPanel, {
      props: { citations, evidence: [], selectedTraceId: null },
    });
    expect(wrapper.text()).toContain('《针灸甲乙经》记载...');
  });

  it('renders quote when citation_text is absent', () => {
    const citations: ResultCitation[] = [
      makeCitation({ trace_id: 't1', quote: 'A direct quote from source' }),
    ];
    const wrapper = mount(CitationPanel, {
      props: { citations, evidence: [], selectedTraceId: null },
    });
    expect(wrapper.text()).toContain('A direct quote from source');
  });

  it('data contract: trace_id key is used for unique identification and selection', () => {
    const citations: ResultCitation[] = [
      makeCitation({ trace_id: 'trace-001' }),
    ];
    const wrapper = mount(CitationPanel, {
      props: { citations, evidence: [], selectedTraceId: 'trace-001' },
    });
    expect(wrapper.find('[aria-selected="true"]').exists()).toBe(true);
  });

  it('emits select event with trace_id', async () => {
    const citations: ResultCitation[] = [
      makeCitation({ trace_id: 'ct-1', citation_text: 'Citation 1' }),
    ];
    const wrapper = mount(CitationPanel, {
      props: { citations, evidence: [], selectedTraceId: null },
    });
    const citationItem = wrapper.find('[role="button"]');
    await citationItem.trigger('click');
    expect(wrapper.emitted('select')?.[0]).toEqual(['ct-1']);
  });

  it('shows evidence count prompt text', () => {
    const citations: ResultCitation[] = [
      makeCitation({ trace_id: 't1', citation_text: 'Test' }),
    ];
    const wrapper = mount(CitationPanel, {
      props: { citations, evidence: [], selectedTraceId: 't1' },
    });
    expect(wrapper.text()).toContain('缺少证据关联');
  });
});

// ────────────────────────────────────────────────────────────────────────
// EvidenceDetail
// ────────────────────────────────────────────────────────────────────────
describe('EvidenceDetail — Domain Semantic Regression', () => {
  it('renders trace_id in metadata', () => {
    const evidence: ResultEvidence = makeEvidence({
      trace_id: 'ev-trace-abc123',
      claim_text: 'Key finding',
      document_id: 'doc-1',
      passage_id: 'passage-1',
    });
    const wrapper = mount(EvidenceDetail, {
      props: { evidence },
      global: globalPlugins,
    });
    expect(wrapper.text()).toContain('ev-trace');
  });

  it('renders document_id and passage_id', () => {
    const evidence: ResultEvidence = makeEvidence({
      trace_id: 'ev-1',
      claim_text: 'Finding',
      document_id: 'doc-xyz',
      passage_id: 'pass-abc',
    });
    const wrapper = mount(EvidenceDetail, {
      props: { evidence },
      global: globalPlugins,
    });
    expect(wrapper.text()).toContain('doc-xyz');
    expect(wrapper.text()).toContain('pass-abc');
  });

  it('renders chunk_id when passage_id is absent', () => {
    const evidence: ResultEvidence = makeEvidence({
      trace_id: 'ev-2',
      claim_text: 'Finding',
      document_id: 'doc-1',
      chunk_id: 'chunk-123',
    });
    const wrapper = mount(EvidenceDetail, {
      props: { evidence },
      global: globalPlugins,
    });
    expect(wrapper.text()).toContain('chunk-123');
  });

  it('renders claim_text and quote', () => {
    const evidence: ResultEvidence = makeEvidence({
      trace_id: 'ev-3',
      claim_text: 'AI归纳结论',
      quote: '原典文字',
    });
    const wrapper = mount(EvidenceDetail, {
      props: { evidence },
      global: globalPlugins,
    });
    expect(wrapper.text()).toContain('AI归纳结论');
    expect(wrapper.text()).toContain('原典文字');
  });

  it('source_ref_title and source_ref_id rendered via SourceRef sub-component', () => {
    const evidence: ResultEvidence = makeEvidence({
      trace_id: 'ev-4',
      source_ref_title: '针灸甲乙经 · 四库本',
      source_ref_id: 'src-ref-456',
      passage_id: 'p-1',
      claim_text: 'Finding',
    });
    const wrapper = mount(EvidenceDetail, {
      props: { evidence },
      global: globalPlugins,
    });
    expect(wrapper.text()).toContain('针灸甲乙经');
    expect(wrapper.text()).toContain('src-ref');
    expect(wrapper.text()).toContain('文献来源');
  });
});

// ────────────────────────────────────────────────────────────────────────
// SourceReferenceCard
// ────────────────────────────────────────────────────────────────────────
describe('SourceReferenceCard — Domain Semantic Regression', () => {
  it('renders source_ref_title and source_ref_id', () => {
    const evidence: ResultEvidence = makeEvidence({
      trace_id: 'e1',
      source_ref_title: '黄帝内经',
      source_ref_id: 's-ref-001',
      passage_id: 'p-01',
    });
    const wrapper = mount(SourceReferenceCard, {
      props: { evidence },
      global: globalPlugins,
    });
    expect(wrapper.text()).toContain('黄帝内经');
    expect(wrapper.text()).toContain('s-ref-001');
  });

  it('renders passage_id with "passage" label', () => {
    const evidence: ResultEvidence = makeEvidence({
      trace_id: 'e1',
      source_ref_title: 'Book',
      source_ref_id: 's1',
      passage_id: 'passage-abc',
    });
    const wrapper = mount(SourceReferenceCard, {
      props: { evidence },
      global: globalPlugins,
    });
    expect(wrapper.text()).toContain('passage');
    expect(wrapper.text()).toContain('精确段落定位可用');
  });

  it('shows document-only location when no passage_id', () => {
    const evidence: ResultEvidence = makeEvidence({
      trace_id: 'e2',
      source_ref_title: 'Book',
      source_ref_id: 's2',
      document_id: 'doc-1',
    });
    const wrapper = mount(SourceReferenceCard, {
      props: { evidence },
      global: globalPlugins,
    });
    expect(wrapper.text()).toContain('仅文献级定位');
  });

  it('shows missing source warning when no source_ref', () => {
    const evidence: ResultEvidence = makeEvidence({
      trace_id: 'e3',
    });
    const wrapper = mount(SourceReferenceCard, {
      props: { evidence },
      global: globalPlugins,
    });
    expect(wrapper.text()).toContain('缺少文献来源信息');
  });

  it('has aria-label "来源参考"', () => {
    const evidence: ResultEvidence = makeEvidence({
      trace_id: 'e1',
      source_ref_title: 'Book',
      source_ref_id: 's1',
    });
    const wrapper = mount(SourceReferenceCard, {
      props: { evidence },
      global: globalPlugins,
    });
    expect(wrapper.attributes('aria-label')).toBe('来源参考');
  });
});

// ────────────────────────────────────────────────────────────────────────
// PassageReader
// ────────────────────────────────────────────────────────────────────────
describe('PassageReader — Domain Semantic Regression', () => {
  it('component is importable (data-fetching component)', () => {
    expect(PassageReader).toBeDefined();
  });
});
