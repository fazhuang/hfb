<template>
  <section class="rrv-section" aria-labelledby="rrv-heading">
    <h2 id="rrv-heading" class="rrv-heading">研究报告正文</h2>

    <div v-if="report.markdown" class="rrv-report" role="document">
      <h3 class="rrv-report-title">{{ report.title }}</h3>

      <!-- Render sections from markdown -->
      <div
        v-for="(section, si) in sections"
        :key="si"
        class="rrv-section-block"
      >
        <h4 v-if="section.heading" class="rrv-section-heading">{{ section.heading }}</h4>
        <p
          v-for="(para, pi) in section.paragraphs"
          :key="pi"
          class="rrv-paragraph"
        >
          <template v-for="(token, ti) in para.tokens" :key="ti">
            <span v-if="token.bold" class="rrv-bold">{{ token.text }}</span>
            <button
              v-else-if="token.citation && displayNumbers.get(token.citation)"
              type="button"
              class="rrv-citation-marker"
              :class="{ 'rrv-citation-marker--active': isSelectedCitation(token.citation!) }"
              :aria-label="`引用 [${displayNumbers.get(token.citation!)}]`"
              @click="$emit('select-citation', token.citation!)"
            >
              [{{ displayNumbers.get(token.citation!) }}]
            </button>
            <span v-else>{{ token.text }}</span>
          </template>
        </p>
      </div>
    </div>

    <div v-else class="rrv-empty">
      <span class="rrv-empty-icon" aria-hidden="true">📄</span>
      <p>此运行尚未生成报告内容。</p>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { ResultReport } from '@/composables/useResearchResult';

const props = defineProps<{
  report: ResultReport;
  selectedCitationTraceId: string | null;
  /** Set of trace_ids from the current run's real citations (output_artifacts.citations).
   * Only markers matching a real citation become clickable buttons. */
  validCitationTraceIds: Set<string>;
}>();

defineEmits<{
  'select-citation': [traceId: string];
}>();

interface TextToken {
  text: string;
  bold?: boolean;
  citation?: string;
  displayNumber?: number;
}

interface ParsedParagraph {
  tokens: TextToken[];
}

interface ParsedSection {
  heading: string | null;
  paragraphs: ParsedParagraph[];
}

/**
 * Pattern to match citation markers.
 *
 * Three formats are supported (validated against validCitationTraceIds):
 *   1. [doc_id:chunk_id]       — generation_service / seed test data
 *   2. [UUIDv5]                 — workflow build_markdown_artifact (new)
 *   3. `UUIDv5`                — legacy reports (backtick-wrapped trace_id)
 */
const CITATION_RE =
  /\[([a-zA-Z0-9_-]+:[a-zA-Z0-9_-]+|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\]|`([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})`/gi;

/** Pattern to match bold markers like **text** */
const BOLD_RE = /\*\*(.+?)\*\*/g;

/**
 * Parse markdown report into sections for safe display.
 *
 * This approach:
 *   1. Never uses v-html or innerHTML
 *   2. Renders via Vue template with bound data only
 *   3. Citation markers [trace_id] become clickable buttons ONLY when they match
 *      a real trace_id from the current run's output_artifacts.citations
 *   4. Unknown, cross-run, or missing markers render as plain text
 *   5. Bold **text** is applied via CSS, not HTML interpretation
 *   6. No script execution, no event attributes, no iframe, no javascript: URLs
 */
const sections = computed((): ParsedSection[] => {
  if (!props.report.markdown) return [];

  const lines = props.report.markdown.split('\n');
  const result: ParsedSection[] = [];
  let currentSection: ParsedSection = { heading: null, paragraphs: [] };

  for (const line of lines) {
    const trimmed = line.trim();

    // Skip empty lines
    if (!trimmed) {
      if (currentSection.paragraphs.length > 0 || currentSection.heading) {
        result.push(currentSection);
        currentSection = { heading: null, paragraphs: [] };
      }
      continue;
    }

    // Section heading
    if (trimmed.startsWith('## ')) {
      if (currentSection.paragraphs.length > 0 || currentSection.heading) {
        result.push(currentSection);
      }
      currentSection = { heading: trimmed.slice(3).trim(), paragraphs: [] };
      continue;
    }

    // Main title — skip or treat as section heading
    if (trimmed.startsWith('# ')) {
      if (currentSection.paragraphs.length > 0 || currentSection.heading) {
        result.push(currentSection);
      }
      currentSection = { heading: trimmed.slice(2).trim(), paragraphs: [] };
      continue;
    }

    // Horizontal rule or metadata — skip
    if (trimmed === '---' || trimmed === '***' || trimmed.startsWith('> ')) {
      continue;
    }

    // Parse tokens in this line
    const tokens = parseTokens(trimmed);
    if (tokens.length > 0) {
      currentSection.paragraphs.push({ tokens });
    }
  }

  // Push final section
  if (currentSection.paragraphs.length > 0 || currentSection.heading) {
    result.push(currentSection);
  }

  return result;
});

interface TokenMatch {
  start: number;
  end: number;
  text: string;
  type: 'citation' | 'bold';
}

function parseTokens(line: string): TextToken[] {
  // Collect all matches
  const matches: TokenMatch[] = [];

  // Citation markers
  let citMatch: RegExpExecArray | null;
  CITATION_RE.lastIndex = 0;
  while ((citMatch = CITATION_RE.exec(line)) !== null) {
    // group(1) = bracket capture, group(2) = backtick capture
    const tid = citMatch[1] || citMatch[2] || '';
    matches.push({
      start: citMatch.index,
      end: citMatch.index + citMatch[0].length,
      text: tid,
      type: 'citation',
    });
  }

  // Bold markers
  let boldMatch: RegExpExecArray | null;
  BOLD_RE.lastIndex = 0;
  while ((boldMatch = BOLD_RE.exec(line)) !== null) {
    matches.push({
      start: boldMatch.index,
      end: boldMatch.index + boldMatch[0].length,
      text: boldMatch[1] || '',
      type: 'bold',
    });
  }

  // Sort by start position
  matches.sort((a, b) => a.start - b.start);

  // Build token list with plain text segments between matches
  const tokens: TextToken[] = [];
  let pos = 0;

  for (const m of matches) {
    // Plain text before this match
    if (m.start > pos) {
      const plain = line.slice(pos, m.start);
      if (plain) tokens.push({ text: plain });
    }

    // The match token
    if (m.type === 'citation') {
      // m.text is the captured trace_id (no brackets).
      // Store the trace_id as citation, full [trace_id] as text for
      // unknown-marker fallback rendering.
      tokens.push({ text: `[${m.text}]`, citation: m.text });
    } else {
      tokens.push({ text: m.text, bold: true });
    }

    pos = m.end;
  }

  // Remaining text
  if (pos < line.length) {
    tokens.push({ text: line.slice(pos) });
  }

  return tokens;
}

/**
 * Assign a sequential display number to each valid citation trace_id
 * that actually appears in the report markdown.
 * The display number is view-local; the stable identity is always trace_id.
 */
const displayNumbers = computed((): Map<string, number> => {
  const map = new Map<string, number>();
  if (!props.report.markdown) return map;

  let next = 1;
  CITATION_RE.lastIndex = 0;
  let m: RegExpExecArray | null;
  while ((m = CITATION_RE.exec(props.report.markdown)) !== null) {
    const tid = m[1] || m[2];
    if (tid && props.validCitationTraceIds.has(tid) && !map.has(tid)) {
      map.set(tid, next++);
    }
  }
  return map;
});

/**
 * Check if a citation trace_id is the currently selected one.
 */
function isSelectedCitation(traceId: string): boolean {
  return props.selectedCitationTraceId === traceId;
}
</script>

<style scoped>
.rrv-section {
  padding: 0;
}

.rrv-heading {
  font-size: 18px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 var(--space-4);
  padding-bottom: 10px;
  border-bottom: 2px solid var(--color-accent);
}

.rrv-report {
  padding: 0;
}

.rrv-report-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0 0 var(--space-5);
  line-height: 1.4;
}

.rrv-section-block {
  margin-bottom: 20px;
}

.rrv-section-heading {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text-primary, var(--color-hover));
  margin: 0 0 var(--space-3);
  border-left: 3px solid var(--color-accent);
  padding-left: 12px;
}

.rrv-paragraph {
  margin: 0 0 var(--space-2-5);
  font-size: 14px;
  color: var(--color-text-primary);
  line-height: 1.8;
}

.rrv-bold {
  font-weight: 700;
}

.rrv-citation-marker {
  display: inline;
  margin: 0 var(--space-0-25);
  padding: var(--space-0-25) 5px;
  border: 1px solid var(--color-accent);
  border-radius: var(--radius-sm);
  background: var(--color-accent-light);
  color: var(--color-accent);
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
  transition: all var(--transition-base);
  vertical-align: super;
  line-height: 1;
}

.rrv-citation-marker:hover {
  background: var(--color-accent);
  color: var(--color-surface);
}

.rrv-citation-marker:focus-visible {
  background: var(--color-accent);
  color: var(--color-surface);
}

.rrv-citation-marker--active {
  background: var(--color-accent);
  color: var(--color-surface);
  outline: 2px solid var(--color-text-primary);
  outline-offset: 2px;
}

/* Empty state */
.rrv-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-12) 20px;
  border: 2px dashed var(--color-border);
  border-radius: var(--radius-lg);
  color: var(--color-text-muted);
}

.rrv-empty-icon {
  font-size: 36px;
}

.rrv-empty p {
  margin: 0;
  font-size: 14px;
}
</style>
