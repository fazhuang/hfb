<template>
  <div class="research-workspace">
    <!-- Back to current research -->
    <div v-if="store.hasActiveResearch" class="rw-back-bar">
      <router-link :to="{ name: 'research-home' }" class="back-link">
        {{ t('researchEntry.backToResearch') }}
      </router-link>
      <span class="back-context">{{ store.currentTopic?.name }}</span>
    </div>

    <header class="rw-header">
      <div>
        <h1>{{ t('researchWorkspace.title') }}</h1>
        <p class="rw-subtitle">{{ t('researchWorkspace.subtitle') }}</p>
      </div>
      <div class="rw-header-actions">
        <span v-if="store.hasActiveResearch" class="rw-topic-badge">
          🔬 {{ store.currentTopic?.name }}
        </span>
      </div>
    </header>

    <!-- Tab bar -->
    <nav class="rw-tabs" role="tablist">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        role="tab"
        :aria-selected="activeTab === tab.key"
        :class="['rw-tab', { active: activeTab === tab.key }]"
        @click="activeTab = tab.key"
      >
        <span class="rw-tab-icon">{{ tab.icon }}</span>
        <span class="rw-tab-label">{{ tab.label }}</span>
        <span v-if="tab.badge" class="rw-tab-badge">{{ tab.badge }}</span>
      </button>
    </nav>
    <!-- ============================================================ -->
    <!-- Tab: 资料 (Materials / Literature) -->
    <!-- ============================================================ -->
    <section v-if="activeTab === 'materials'" class="rw-panel">
      <div class="rw-panel-header">
        <h2>{{ t('researchWorkspace.materials') }}</h2>
        <div class="rw-panel-actions">
          <input
            v-model="materialsQuery"
            type="text"
            class="rw-search-input"
            :placeholder="t('researchWorkspace.searchMaterials')"
            @keyup.enter="fetchMaterials(1)"
          />
          <router-link :to="{ name: 'literature' }" class="rw-action-link">
            {{ t('researchWorkspace.viewAll') }} →
          </router-link>
        </div>
      </div>

      <div v-if="materialsLoading" class="rw-loading">{{ t('common.loading') }}</div>
      <div v-else-if="materialsError" class="rw-error">{{ materialsError }}</div>
      <div v-else-if="materials.length === 0" class="rw-empty">{{ t('common.noData') }}</div>
      <ul v-else class="rw-list">
        <li v-for="item in materials" :key="item.id" class="rw-list-item">
          <router-link :to="`/literature/${item.id}`" class="rw-item-link">
            <span class="rw-item-title">{{ item.title }}</span>
            <span class="rw-item-meta">
              <span v-if="item.dynasty" class="rw-tag">{{ item.dynasty }}</span>
              <span v-if="item.category" class="rw-tag">{{ item.category }}</span>
              <span class="rw-tag rw-tag--dim">{{ item.source_name || '—' }}</span>
            </span>
          </router-link>
        </li>
      </ul>

      <div v-if="materialsTotal > materialsLimit" class="rw-pagination">
        <button :disabled="materialsPage <= 1" @click="fetchMaterials(materialsPage - 1)">
          {{ t('common.back') }}
        </button>
        <span>{{ materialsPage }} / {{ Math.ceil(materialsTotal / materialsLimit) }}</span>
        <button
          :disabled="materialsPage >= Math.ceil(materialsTotal / materialsLimit)"
          @click="fetchMaterials(materialsPage + 1)"
        >
          {{ t('common.next') }}
        </button>
      </div>
    </section>

    <!-- ============================================================ -->
    <!-- Tab: 版本 (Versions) -->
    <!-- ============================================================ -->
    <section v-if="activeTab === 'versions'" class="rw-panel">
      <div class="rw-panel-header">
        <h2>{{ t('researchWorkspace.versions') }}</h2>
        <div class="rw-panel-actions">
          <input
            v-model="versionsQuery"
            type="text"
            class="rw-search-input"
            :placeholder="t('researchWorkspace.searchVersions')"
            @keyup.enter="fetchVersions(1)"
          />
          <router-link :to="{ name: 'classical-versions' }" class="rw-action-link">
            {{ t('researchWorkspace.viewAll') }} →
          </router-link>
        </div>
      </div>

      <div v-if="versionsLoading" class="rw-loading">{{ t('common.loading') }}</div>
      <div v-else-if="versionsError" class="rw-error">{{ versionsError }}</div>
      <div v-else-if="versions.length === 0" class="rw-empty">{{ t('common.noData') }}</div>
      <ul v-else class="rw-list">
        <li v-for="item in versions" :key="item.id" class="rw-list-item">
          <router-link :to="`/versions/${item.id}`" class="rw-item-link">
            <span class="rw-item-title">{{ item.work_title }}</span>
            <span class="rw-item-sub">{{ item.version_name }}</span>
            <span class="rw-item-meta">
              <span v-if="item.dynasty" class="rw-tag">{{ item.dynasty }}</span>
              <span v-if="item.edition_type" class="rw-tag">{{ item.edition_type }}</span>
              <span v-if="item.repository" class="rw-tag rw-tag--dim">{{ item.repository }}</span>
            </span>
          </router-link>
        </li>
      </ul>

      <div v-if="versionsTotal > versionsLimit" class="rw-pagination">
        <button :disabled="versionsPage <= 1" @click="fetchVersions(versionsPage - 1)">
          {{ t('common.back') }}
        </button>
        <span>{{ versionsPage }} / {{ Math.ceil(versionsTotal / versionsLimit) }}</span>
        <button
          :disabled="versionsPage >= Math.ceil(versionsTotal / versionsLimit)"
          @click="fetchVersions(versionsPage + 1)"
        >
          {{ t('common.next') }}
        </button>
      </div>
    </section>

    <!-- ============================================================ -->
    <!-- Tab: 笔记 (Notes) -->
    <!-- ============================================================ -->
    <section v-if="activeTab === 'notes'" class="rw-panel">
      <div class="rw-panel-header">
        <h2>{{ t('researchWorkspace.notes') }}</h2>
        <div class="rw-panel-actions">
          <select v-model="notesSessionFilter" class="rw-select" @change="fetchNotesForSession">
            <option value="">{{ t('researchWorkspace.allSessions') }}</option>
            <option v-for="s in sessions" :key="s.id" :value="s.id">{{ s.title }}</option>
          </select>
          <button class="rw-btn rw-btn--sm" @click="createQuickNote" :disabled="!quickNoteText.trim()">
            + {{ t('researchWorkspace.quickNote') }}
          </button>
        </div>
      </div>

      <!-- Quick note input -->
      <div class="rw-quick-note">
        <textarea
          v-model="quickNoteText"
          class="rw-textarea"
          :placeholder="t('researchWorkspace.notePlaceholder')"
          rows="3"
        ></textarea>
        <select v-model="quickNoteSession" class="rw-select rw-select--inline">
          <option value="">{{ t('researchWorkspace.pickSession') }}</option>
          <option v-for="s in sessions" :key="s.id" :value="s.id">{{ s.title }}</option>
        </select>
      </div>

      <div v-if="notesLoading" class="rw-loading">{{ t('common.loading') }}</div>
      <div v-else-if="notes.length === 0" class="rw-empty">{{ t('workspace.noNotes') }}</div>
      <div v-else class="rw-notes-grid">
        <article v-for="note in notes" :key="note.id" class="rw-note-card">
          <div class="rw-note-meta">
            <span v-if="note.entity_type" class="rw-tag rw-tag--accent">{{ note.entity_type }}</span>
            <span class="rw-note-session">{{ note.session_title || '—' }}</span>
            <span class="rw-note-date">{{ formatDate(note.created_at) }}</span>
          </div>
          <p class="rw-note-content">{{ note.content }}</p>
          <button class="rw-note-delete" @click="deleteNoteById(note.id)" :title="t('common.delete')">×</button>
        </article>
      </div>
    </section>

    <!-- ============================================================ -->
    <!-- Tab: 报告 (Reports) -->
    <!-- ============================================================ -->
    <section v-if="activeTab === 'reports'" class="rw-panel">
      <div class="rw-panel-header">
        <h2>{{ t('researchWorkspace.reports') }}</h2>
        <button class="rw-action-link rw-action-link--btn" @click="activeTab = 'v4-research'">
          {{ t('researchWorkspace.newReport') }} →
        </button>
      </div>

      <div v-if="reportsLoading" class="rw-loading">{{ t('common.loading') }}</div>
      <div v-else-if="reportsError" class="rw-error">{{ reportsError }}</div>
      <div v-else-if="reports.length === 0" class="rw-empty">
        <p>{{ t('researchWorkspace.noReports') }}</p>
        <button class="rw-btn rw-btn--primary" @click="activeTab = 'v4-research'">
          {{ t('researchWorkspace.runFirstResearch') }}
        </button>
      </div>
      <div v-else class="rw-reports-list">
        <div v-for="run in reports" :key="run.run_id" class="rw-report-card">
          <div class="rw-report-header">
            <h3>{{ run.topic || t('researchWorkspace.untitledReport') }}</h3>
            <span class="rw-report-date">{{ formatDate(run.completed_at) }}</span>
          </div>
          <div v-if="run.step_execution_trace" class="rw-report-steps">
            <span
              v-for="step in run.step_execution_trace"
              :key="step.name"
              class="rw-step-badge"
              :class="`rw-step--${step.status || 'pending'}`"
              :title="stepName(step.name)"
            >
              {{ stepIcon(step.status) }} {{ stepName(step.name) }}
            </span>
          </div>
          <div v-if="run.output_artifacts?.report_sections" class="rw-report-preview">
            <div
              v-for="(section, si) in run.output_artifacts.report_sections.slice(0, 3)"
              :key="si"
              class="rw-report-section"
            >
              <strong>{{ section.title || section.heading }}</strong>
              <p>{{ (section.content || section.body || '').substring(0, 200) }}{{ (section.content || section.body || '').length > 200 ? '...' : '' }}</p>
            </div>
          </div>
          <div class="rw-report-actions">
            <a
              v-if="run.run_id"
              class="rw-btn rw-btn--sm"
              @click="viewReport(run)"
            >
              {{ t('researchWorkspace.viewReport') }}
            </a>
          </div>
        </div>
      </div>
    </section>

    <!-- ============================================================ -->
    <!-- Tab: 版本研究 (Version Comparison) — embedded inline        -->
    <!-- ============================================================ -->
    <section v-if="activeTab === 'research'" class="rw-panel rw-panel--flush">
      <ResearchWorkflowView />
    </section>

    <!-- ============================================================ -->
    <!-- Tab: V4 研究 (V4 Research) — inline workflow + run loading -->
    <!-- ============================================================ -->
    <section v-if="activeTab === 'v4-research'" class="rw-panel">
      <div class="rw-panel-header">
        <h2>{{ t('nav.v4Research') }} — {{ t('v4.researchTitle') }}</h2>
      </div>

      <!-- If a specific report is selected -->
      <div v-if="selectedReport" class="rw-report-detail">
        <button class="rw-btn rw-btn--sm rw-back-btn" @click="selectedReport = null">
          ← {{ t('common.back') }}
        </button>

        <div class="rw-report-header">
          <h3>{{ selectedReport.topic || t('researchWorkspace.untitledReport') }}</h3>
          <span class="rw-report-date">{{ formatDate(selectedReport.completed_at) }}</span>
        </div>

        <!-- Steps -->
        <div v-if="selectedReport.step_execution_trace" class="rw-report-steps">
          <span
            v-for="step in selectedReport.step_execution_trace"
            :key="step.name"
            class="rw-step-badge"
            :class="`rw-step--${step.status || 'pending'}`"
          >
            {{ stepIcon(step.status) }} {{ stepName(step.name) }}
          </span>
        </div>

        <!-- Full report content -->
        <div v-if="selectedReport.output_artifacts?.report_sections" class="rw-report-full">
          <div
            v-for="(section, si) in selectedReport.output_artifacts.report_sections"
            :key="si"
            class="rw-report-section-full"
          >
            <h4>{{ section.title || section.heading || `§${si + 1}` }}</h4>
            <div class="rw-report-body" v-text="section.content || section.body"></div>
            <!-- Evidence badges for this section -->
            <div v-if="section.evidence_ids?.length" class="rw-section-evidence">
              <span class="rw-evidence-label">📎 {{ t('researchWorkspace.linkedEvidence') }}:</span>
              <span
                v-for="(evId, ei) in section.evidence_ids.slice(0, 5)"
                :key="ei"
                class="rw-evidence-pill"
                @click="openEvidenceInGraph(evId)"
              >
                {{ evId.slice(0, 8) }}...
              </span>
            </div>
          </div>
        </div>

        <!-- Full markdown fallback -->
        <pre v-else-if="selectedReport.output_artifacts?.markdown" class="rw-report-markdown">{{
          selectedReport.output_artifacts.markdown
        }}</pre>

        <!-- Citations -->
        <div v-if="reportCitations.length" class="rw-citations">
          <h4>{{ t('v4.citations') }} ({{ reportCitations.length }})</h4>
          <div v-for="(cit, ci) in reportCitations" :key="ci" class="rw-citation-item">
            <span class="cit-index">#{{ ci + 1 }}</span>
            <span class="cit-text">{{ cit.claim_text || cit.quote || cit.citation_text || '—' }}</span>
            <button
              v-if="cit.trace_id"
              class="rw-evidence-pill rw-evidence-pill--link"
              @click="openEvidenceInGraph(cit.trace_id)"
            >
              🔗 {{ t('researchWorkspace.viewInGraph') }}
            </button>
            <!-- P2-⑤: Create note from citation -->
            <button
              class="rw-evidence-pill rw-evidence-pill--note"
              @click="noteFromCitation(cit)"
              :title="t('v4.noteFromCitation')"
            >
              📝 {{ t('v4.noteFromCitation') }}
            </button>
          </div>
        </div>
      </div>

      <!-- Report list (when no specific report is selected) -->
      <div v-else>
        <!-- Quick workflow runner -->
        <div class="rw-v4-quick">
          <input
            v-model="v4Topic"
            type="text"
            class="rw-search-input"
            :placeholder="t('v4.topicPlaceholder')"
            :disabled="v4Loading"
            style="flex:1"
            @keyup.enter="runV4WorkflowInline"
          />
          <button
            class="rw-btn rw-btn--primary"
            :disabled="v4Loading || !v4Topic.trim()"
            @click="runV4WorkflowInline"
          >
            {{ v4Loading ? t('common.loading') + '...' : t('v4.runWorkflow') }}
          </button>
        </div>
        <p v-if="v4Error" class="rw-error">{{ v4Error }}</p>

        <div v-if="reportsLoading" class="rw-loading">{{ t('common.loading') }}</div>
        <div v-else-if="reports.length === 0" class="rw-empty">
          <p>{{ t('researchWorkspace.noReports') }}</p>
        </div>
        <div v-else class="rw-reports-list">
          <div v-for="run in reports" :key="run.run_id" class="rw-report-card">
            <div class="rw-report-header">
              <h3>{{ run.topic || t('researchWorkspace.untitledReport') }}</h3>
              <span class="rw-report-date">{{ formatDate(run.completed_at) }}</span>
            </div>
            <div v-if="run.step_execution_trace" class="rw-report-steps">
              <span
                v-for="step in run.step_execution_trace"
                :key="step.name"
                class="rw-step-badge"
                :class="`rw-step--${step.status || 'pending'}`"
              >
                {{ stepIcon(step.status) }} {{ stepName(step.name) }}
              </span>
            </div>
            <div class="rw-report-actions">
              <button class="rw-btn rw-btn--sm" @click="openReportDetail(run)">
                {{ t('researchWorkspace.viewReport') }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ============================================================ -->
    <!-- Tab: 研究助手 (Research Assistant) -->
    <!-- ============================================================ -->
    <section v-if="activeTab === 'assistant'" class="rw-panel rw-panel--assistant">
      <div class="rw-assistant-layout">
        <!-- Chat area -->
        <div class="rw-chat-area">
          <div class="rw-panel-header">
            <h2>{{ t('researchWorkspace.assistant') }}</h2>
            <span v-if="chatSessionTitle" class="rw-session-label">{{ chatSessionTitle }}</span>
          </div>

          <div class="rw-chat-body" ref="chatBodyRef">
            <div v-if="chatMessages.length === 0" class="rw-chat-empty">
              <p>{{ t('researchWorkspace.assistantHint') }}</p>
              <div class="rw-chat-prompts">
                <button
                  v-for="prompt in suggestedPrompts"
                  :key="prompt"
                  class="rw-prompt-chip"
                  @click="sendPrompt(prompt)"
                >
                  {{ prompt }}
                </button>
              </div>
            </div>
            <div
              v-for="(msg, idx) in chatMessages"
              :key="idx"
              class="rw-chat-msg"
              :class="`rw-chat-msg--${msg.role}`"
            >
              <span class="rw-chat-role">{{ msg.role === 'user' ? '👤' : '🤖' }}</span>
              <div class="rw-chat-content" v-text="msg.content"></div>
            </div>
            <div v-if="chatLoading" class="rw-chat-msg rw-chat-msg--assistant">
              <span class="rw-chat-role">🤖</span>
              <div class="rw-chat-content"><span class="rw-typing">...</span></div>
            </div>
          </div>

          <div class="rw-chat-input-row">
            <input
              v-model="chatInput"
              type="text"
              class="rw-chat-input"
              :placeholder="t('researchWorkspace.chatPlaceholder')"
              :disabled="chatLoading"
              @keyup.enter="sendMessage"
            />
            <button
              class="rw-chat-send"
              :disabled="!chatInput.trim() || chatLoading"
              @click="sendMessage"
            >
              ➤
            </button>
          </div>
        </div>

        <!-- Sidebar: session + evidence -->
        <aside class="rw-assistant-sidebar">
          <!-- Session picker -->
          <div class="rw-sidebar-section">
            <label class="rw-sidebar-label">{{ t('workspace.sessions') }}</label>
            <select v-model="chatSessionId" class="rw-select rw-select--full" @change="onChatSessionChange">
              <option value="">{{ t('researchWorkspace.noSession') }}</option>
              <option v-for="s in sessions" :key="s.id" :value="s.id">{{ s.title }}</option>
            </select>
            <button class="rw-btn rw-btn--sm rw-btn--full" @click="createChatSession" style="margin-top:6px">
              + {{ t('researchWorkspace.newSession') }}
            </button>
          </div>

          <!-- Evidence -->
          <div class="rw-sidebar-section">
            <label class="rw-sidebar-label">{{ t('workspace.evidence') }}</label>
            <div v-if="evidence.length === 0" class="rw-sidebar-empty">{{ t('workspace.evidenceHint') }}</div>
            <div v-for="(ev, idx) in evidence" :key="idx" class="rw-evidence-item">
              <span class="rw-evidence-type">{{ ev.entity_type }}</span>
              <span class="rw-evidence-text">{{ (ev.content || '').substring(0, 120) }}</span>
              <div class="rw-evidence-actions">
                <button
                  v-if="chatSessionId"
                  class="rw-evidence-action-btn"
                  :class="{ saved: ev.saved }"
                  @click="saveCitation(ev, idx)"
                  :disabled="ev.saving"
                  :title="ev.saved ? t('v4.citationSaved') : t('v4.saveCitation')"
                >
                  {{ ev.saving ? '...' : ev.saved ? '💾✓' : '💾' }}
                </button>
                <button
                  v-if="ev.entity_type && ev.id"
                  class="rw-evidence-graph-link"
                  @click="openEntityInGraph(ev.entity_type, ev.id)"
                  :title="t('researchWorkspace.viewInGraph')"
                >
                  🔗
              </button>
            </div>
          </div>

            <!-- Graph quick-preview if available -->
            <div v-if="evidenceGraphData" class="rw-evidence-graph-preview">
              <label class="rw-sidebar-label">📊 {{ t('researchWorkspace.evidenceGraph') }}</label>
              <div class="rw-mini-graph">
                <div v-for="n in evidenceGraphData.nodes?.slice(0, 5)" :key="n.id" class="rw-mini-node">
                  <span class="rw-mini-node-type">{{ n.type }}</span>
                  {{ (n.label || n.id || '').substring(0, 20) }}
                </div>
                <p v-if="(evidenceGraphData.edges?.length || 0) > 0" class="rw-mini-edge-count">
                  {{ evidenceGraphData.edges?.length }} evidence links
                </p>
              </div>
            </div>
          </div>
        </aside>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick, computed, onMounted } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { useI18n } from 'vue-i18n';
import api from '@/api/client';
import { useAuthStore } from '@/stores/auth';
import { useResearchStore } from '@/stores/research';
import ResearchWorkflowView from '@/views/ResearchWorkflowView.vue';

const { t } = useI18n();
const router = useRouter();
const route = useRoute();
const auth = useAuthStore();
const store = useResearchStore();

// ---- Tab state ----
// Support ?tab=materials|versions|notes|reports|assistant|research|v4-research
const activeTab = ref('materials');

interface TabDef {
  key: string;
  icon: string;
  label: string;
  badge?: string;
}

const tabs = computed<TabDef[]>(() => [
  { key: 'materials', icon: '📄', label: t('researchWorkspace.materials') },
  { key: 'versions', icon: '🏛️', label: t('researchWorkspace.versions') },
  { key: 'notes', icon: '📝', label: t('researchWorkspace.notes'), badge: String(notesCount.value) },
  { key: 'reports', icon: '📊', label: t('researchWorkspace.reports') },
  { key: 'research', icon: '校', label: t('nav.research') },
  { key: 'v4-research', icon: '🧬', label: t('nav.v4Research') },
  { key: 'assistant', icon: '🤖', label: t('researchWorkspace.assistant') },
]);

// ---- Types ----
interface MaterialItem {
  id: string; title: string; dynasty: string | null;
  category: string | null; source_name: string | null;
}
interface VersionItem {
  id: string; work_title: string; version_name: string;
  dynasty: string | null; edition_type: string | null; repository: string | null;
}
interface SessionItem { id: string; title: string; }
interface NoteItem {
  id: string; content: string; entity_type: string | null;
  session_title?: string; created_at?: string;
}
interface ReportRun {
  run_id: string; topic: string; completed_at: string;
  step_execution_trace?: Array<{ name: string; status: string }>;
  output_artifacts?: Record<string, any>;
}
interface EvidenceItem { entity_type: string; content?: string; id?: string; saved?: boolean; saving?: boolean; }

// ---- V4 inline state ----
const v4Topic = ref('');
const v4Loading = ref(false);
const v4Error = ref('');
const selectedReport = ref<ReportRun | null>(null);
const reportCitations = ref<Array<{ trace_id: string; claim_text: string; quote: string; citation_text: string; document_id: string }>>([]);

// ---- Evidence graph state ----
interface GraphPreview { nodes: Array<{ id: string; type: string; label?: string }>; edges: Array<{ source: string; target: string; evidence_ids?: string[] }>; }
const evidenceGraphData = ref<GraphPreview | null>(null);

// ---- Materials state ----
const materials = ref<MaterialItem[]>([]);
const materialsTotal = ref(0);
const materialsPage = ref(1);
const materialsLimit = 20;
const materialsQuery = ref('');
const materialsLoading = ref(false);
const materialsError = ref<string | null>(null);

// ---- Versions state ----
const versions = ref<VersionItem[]>([]);
const versionsTotal = ref(0);
const versionsPage = ref(1);
const versionsLimit = 20;
const versionsQuery = ref('');
const versionsLoading = ref(false);
const versionsError = ref<string | null>(null);

// ---- Sessions (shared) ----
const sessions = ref<SessionItem[]>([]);

// ---- Notes state ----
const notes = ref<NoteItem[]>([]);
const notesLoading = ref(false);
const notesSessionFilter = ref('');
const quickNoteText = ref('');
const quickNoteSession = ref('');
const notesCount = computed(() => notes.value.length);

// ---- Reports state ----
const reports = ref<ReportRun[]>([]);
const reportsLoading = ref(false);
const reportsError = ref<string | null>(null);

// ---- Assistant state ----
const chatMessages = ref<{ role: string; content: string }[]>([]);
const chatInput = ref('');
const chatLoading = ref(false);
const chatSessionId = ref('');
const chatSessionTitle = ref('');
const evidence = ref<EvidenceItem[]>([]);
const chatBodyRef = ref<HTMLElement | null>(null);

const suggestedPrompts = [
  '针灸甲乙经有哪些重要版本？',
  '《黄帝内经》与《针灸甲乙经》的关系是什么？',
  '请比较不同版本的异文特征',
];

// ================================================================
// Materials
// ================================================================
async function fetchMaterials(p: number) {
  materialsPage.value = p;
  materialsLoading.value = true;
  materialsError.value = null;
  try {
    const params: Record<string, unknown> = { page: p, limit: materialsLimit };
    if (materialsQuery.value.trim()) params.q = materialsQuery.value.trim();
    const { data } = await api.get('/api/v1/documents', { params });
    materials.value = (data.data ?? []) as MaterialItem[];
    materialsTotal.value = (data.total ?? data.meta?.total ?? 0) as number;
  } catch (e: any) {
    materialsError.value = e?.message || t('common.error');
  } finally {
    materialsLoading.value = false;
  }
}

// ================================================================
// Versions
// ================================================================
async function fetchVersions(p: number) {
  versionsPage.value = p;
  versionsLoading.value = true;
  versionsError.value = null;
  try {
    const params: Record<string, unknown> = { page: p, limit: versionsLimit };
    if (versionsQuery.value.trim()) params.q = versionsQuery.value.trim();
    const { data } = await api.get('/api/classical-versions', { params });
    versions.value = (data.data ?? []) as VersionItem[];
    versionsTotal.value = (data.total ?? data.meta?.total ?? 0) as number;
  } catch (e: any) {
    versionsError.value = e?.message || t('common.error');
  } finally {
    versionsLoading.value = false;
  }
}

// ================================================================
// Sessions
// ================================================================
async function loadSessions() {
  if (!auth.isAuthenticated) return;
  try {
    const { data } = await api.get('/api/v1/workspace/sessions');
    sessions.value = (data.data ?? []) as SessionItem[];
  } catch { /* ignore */ }
}

// ================================================================
// Notes
// ================================================================
async function fetchNotesForSession() {
  notesLoading.value = true;
  try {
    if (notesSessionFilter.value) {
      const { data } = await api.get(`/api/v1/workspace/sessions/${notesSessionFilter.value}/notes`);
      const raw = (data.data ?? []) as NoteItem[];
      notes.value = raw.map(n => ({ ...n, session_title: sessions.value.find(s => s.id === notesSessionFilter.value)?.title }));
    } else if (sessions.value.length > 0) {
      // Fetch notes from all sessions
      const allNotes: NoteItem[] = [];
      for (const s of sessions.value.slice(0, 5)) {
        try {
          const { data } = await api.get(`/api/v1/workspace/sessions/${s.id}/notes`);
          const raw = (data.data ?? []) as NoteItem[];
          allNotes.push(...raw.map(n => ({ ...n, session_title: s.title })));
        } catch { /* skip */ }
      }
      notes.value = allNotes.sort((a, b) =>
        (b.created_at || '').localeCompare(a.created_at || '')
      );
    } else {
      notes.value = [];
    }
  } catch {
    notes.value = [];
  } finally {
    notesLoading.value = false;
  }
}

async function createQuickNote() {
  const sessionId = quickNoteSession.value || sessions.value[0]?.id;
  if (!sessionId || !quickNoteText.value.trim()) return;
  try {
    await api.post(`/api/v1/workspace/sessions/${sessionId}/notes`, {
      content: quickNoteText.value.trim(),
    });
    quickNoteText.value = '';
    await fetchNotesForSession();
  } catch { /* ignore */ }
}

async function deleteNoteById(noteId: string) {
  try {
    await api.delete(`/api/v1/workspace/notes/${noteId}`);
    notes.value = notes.value.filter(n => n.id !== noteId);
  } catch { /* ignore */ }
}

// ================================================================
// Reports
// ================================================================
async function fetchReports() {
  reportsLoading.value = true;
  reportsError.value = null;
  try {
    // Gather runs from all workspace sessions
    const allRuns: ReportRun[] = [];
    for (const s of sessions.value.slice(0, 5)) {
      try {
        const { data } = await api.get(`/api/v4/research/session/${s.id}/runs`);
        const runs = (data.data?.runs ?? []) as ReportRun[];
        allRuns.push(...runs);
      } catch { /* skip session */ }
    }
    reports.value = allRuns.sort((a, b) =>
      (b.completed_at || '').localeCompare(a.completed_at || '')
    );
  } catch (e: any) {
    reportsError.value = e?.message || t('common.error');
  } finally {
    reportsLoading.value = false;
  }
}

function viewReport(run: ReportRun) {
  // Open inline in workspace instead of navigating
  selectedReport.value = run;
  activeTab.value = 'v4-research';
}

// ================================================================
// Reports — detail helpers
// ================================================================
function openReportDetail(run: ReportRun) {
  selectedReport.value = run;
  // Extract citations from run artifacts
  const citations: Array<{ trace_id: string; claim_text: string; quote: string; citation_text: string; document_id: string }> = [];
  const artifacts = run.output_artifacts;
  if (artifacts?.citations) {
    for (const c of (artifacts.citations as Array<Record<string, unknown>>)) {
      citations.push({
        trace_id: (c.trace_id as string) || '',
        claim_text: (c.claim_text as string) || '',
        quote: (c.quote as string) || '',
        citation_text: (c.citation_text as string) || '',
        document_id: (c.document_id as string) || '',
      });
    }
  }
  // Also try from step_execution_trace trace_ids
  if (citations.length === 0 && run.step_execution_trace) {
    for (const step of run.step_execution_trace) {
      if ((step as any).trace_ids && Array.isArray((step as any).trace_ids)) {
        for (const tid of (step as any).trace_ids) {
          citations.push({ trace_id: tid, claim_text: '', quote: '', citation_text: '', document_id: '' });
        }
      }
    }
  }
  reportCitations.value = citations;
}

async function runV4WorkflowInline() {
  if (!v4Topic.value.trim()) return;
  v4Loading.value = true;
  v4Error.value = '';
  try {
    const sResp = await api.post('/api/v4/research/session', {
      title: `V4 研究 - ${v4Topic.value}`,
    });
    const sid = sResp.data.data.session_id as string;

    const wfResp = await api.post('/api/v4/research/workflow', {
      session_id: sid,
      topic: v4Topic.value.trim(),
      workflow_type: 'full_research_flow',
    }, { timeout: 120000 });

    if (wfResp.data.success) {
      await loadSessions();
      await fetchReports();
      const latest = reports.value[0];
      if (latest) openReportDetail(latest);
    } else {
      v4Error.value = wfResp.data.message || t('v4.workflowFailed');
    }
  } catch (e: any) {
    v4Error.value = e?.message || t('v4.workflowFailed');
  } finally {
    v4Loading.value = false;
  }
}

// P2-⑤: Create a note from a citation
async function noteFromCitation(cit: { trace_id: string; claim_text: string; quote: string; citation_text: string; document_id: string }) {
  if (!quickNoteSession.value && sessions.value.length === 0) return;
  const sessionId = quickNoteSession.value || sessions.value[0]?.id;
  if (!sessionId) return;
  try {
    await api.post(`/api/v1/workspace/sessions/${sessionId}/notes`, {
      content: `引用: ${cit.citation_text || cit.claim_text || cit.quote || '—'}\n\n---\n\n`,
      entity_type: 'citation',
      entity_id: cit.trace_id,
      tags: '引用笔记',
    });
    quickNoteText.value = '';
    await fetchNotesForSession();
    activeTab.value = 'notes';
  } catch { /* ignore */ }
}

// ================================================================
// Evidence → Graph linking
// ================================================================
function openEntityInGraph(entityType: string, entityId: string) {
  router.push({ name: 'graph', query: { type: entityType, id: entityId } });
}

function openEvidenceInGraph(traceId: string) {
  router.push({ name: 'graph', query: { trace: traceId } });
}

// ================================================================
// Assistant
// ================================================================
async function onChatSessionChange() {
  if (!chatSessionId.value) {
    chatMessages.value = [];
    chatSessionTitle.value = '';
    return;
  }
  const s = sessions.value.find(x => x.id === chatSessionId.value);
  chatSessionTitle.value = s?.title || '';
  try {
    const { data } = await api.get(`/api/v1/workspace/sessions/${chatSessionId.value}`);
    const full = data.data;
    if (full?.chat_history) {
      chatMessages.value = full.chat_history;
    }
  } catch { chatMessages.value = []; }
}

async function createChatSession() {
  try {
    const { data } = await api.post('/api/v1/workspace/sessions', { title: t('researchWorkspace.newSessionDefault') });
    const s = data.data as SessionItem;
    sessions.value.unshift(s);
    chatSessionId.value = s.id;
    chatSessionTitle.value = s.title;
    chatMessages.value = [];
  } catch { /* ignore */ }
}

async function sendMessage() {
  const msg = chatInput.value.trim();
  if (!msg || chatLoading.value) return;

  chatMessages.value.push({ role: 'user', content: msg });
  chatInput.value = '';
  chatLoading.value = true;

  try {
    const response = await fetch('/api/v1/ai/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${auth.accessToken}` },
      body: JSON.stringify({
        message: msg,
        session_id: chatSessionId.value || undefined,
        use_rag: true,
      }),
    });

    const reader = response.body?.getReader();
    if (!reader) { chatLoading.value = false; return; }

    const assistantMsg = { role: 'assistant', content: '' };
    chatMessages.value.push(assistantMsg);

    const decoder = new TextDecoder();
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const text = decoder.decode(value, { stream: true });
      for (const line of text.split('\n')) {
        if (line.startsWith('data: ')) {
          try {
            const json = JSON.parse(line.slice(6));
            if (json.content) assistantMsg.content += json.content;
            if (json.done) break;
          } catch { /* partial JSON */ }
        }
      }
    }

    // Fetch evidence
    if (assistantMsg.content) {
      try {
        const { data } = await api.get('/api/v1/search', { params: { q: msg, limit: 5 } });
        const items = (data.data?.items ?? []) as Array<EvidenceItem & { id?: string }>;
        evidence.value = items.slice(0, 5);

        // Try to generate evidence graph preview
        if (items.length > 0) {
          const entityItems = items.filter(i => i.entity_type && i.id);
          if (entityItems.length >= 1) {
            try {
              const firstEntity = entityItems[0]!;
              const gResp = await api.get(`/api/v1/graph/neighbors/${firstEntity.entity_type}/${firstEntity.id}`);
              const gData = gResp.data?.data;
              if (gData) {
                evidenceGraphData.value = {
                  nodes: [gData.center, ...(gData.neighbors || [])].filter(Boolean),
                  edges: gData.edges || [],
                };
              }
            } catch { evidenceGraphData.value = null; }
          }
        }
      } catch { evidence.value = []; }
    }
  } catch {
    chatMessages.value.push({ role: 'assistant', content: '⚠️ ' + t('researchWorkspace.chatError') });
  } finally {
    chatLoading.value = false;
    nextTick(() => {
      if (chatBodyRef.value) chatBodyRef.value.scrollTop = chatBodyRef.value.scrollHeight;
    });
  }
}

function sendPrompt(prompt: string) {
  chatInput.value = prompt;
  sendMessage();
}

// ================================================================
// Citation save (P0-④: AI Q&A → Citation)
// ================================================================
async function saveCitation(ev: EvidenceItem, _idx: number) {
  if (!chatSessionId.value || ev.saving) return;
  ev.saving = true;
  try {
    const trace = JSON.stringify({
      entity_type: ev.entity_type,
      entity_id: ev.id || '',
      content: ev.content || '',
    });
    await api.post(`/api/v1/workspace/sessions/${chatSessionId.value}/citations`, {
      trace_json: trace,
      citation_text: `[${ev.entity_type}:${ev.id}] ${(ev.content || '').substring(0, 80)}`,
      source_document: ev.entity_type || 'unknown',
    });
    ev.saved = true;
  } catch {
    // silently ignore
  } finally {
    ev.saving = false;
  }
}

// ================================================================
// Helpers
// ================================================================
function formatDate(iso?: string): string {
  if (!iso) return '—';
  try { return new Date(iso).toLocaleDateString('zh-CN'); } catch { return iso; }
}

function stepName(name: string): string {
  const map: Record<string, string> = {
    topic_analysis: t('v4.stepTopic'),
    literature_retrieval: t('v4.stepRetrieval'),
    evidence_synthesis: t('v4.stepSynthesis'),
    report_generation: t('v4.stepReport'),
    citation_export: t('v4.stepCitation'),
  };
  return map[name] || name;
}

function stepIcon(status?: string): string {
  const map: Record<string, string> = {
    completed: '✓', failed: '✗', running: '⋯', pending: '○',
  };
  return map[status || 'pending'] || '○';
}

// ================================================================
// Init
// ================================================================
// Init
onMounted(() => {
  // Honor ?tab= query param
  const tabParam = route.query.tab as string | undefined;
  if (tabParam && ['materials', 'versions', 'notes', 'reports', 'research', 'v4-research', 'assistant'].includes(tabParam)) {
    activeTab.value = tabParam;
  }
  // Honor ?run= query param (deep-link to a specific report)
  const runParam = route.query.run as string | undefined;
  if (runParam) {
    activeTab.value = 'v4-research';
    // The run will be opened after reports load
    (window as any).__pendingRunId = runParam;
  }
  // P0-③: Honor ?ask= query param (auto-ask in assistant tab)
  const askParam = route.query.ask as string | undefined;
  if (askParam) {
    activeTab.value = 'assistant';
    (window as any).__pendingAsk = askParam;
  }
});

loadSessions().then(async () => {
  fetchMaterials(1);
  fetchVersions(1);
  fetchNotesForSession();
  fetchReports().then(() => {
    // If a run was requested via ?run=, open it inline
    const pendingRunId = (window as any).__pendingRunId as string | undefined;
    if (pendingRunId) {
      delete (window as any).__pendingRunId;
      const found = reports.value.find(r => r.run_id === pendingRunId);
      if (found) openReportDetail(found);
    }
  });

  // P0-③: Handle deferred ask — create session and send the question
  const pendingAsk = (window as any).__pendingAsk as string | undefined;
  if (pendingAsk) {
    delete (window as any).__pendingAsk;
    // Ensure a chat session exists
    if (!chatSessionId.value) {
      try {
        const { data } = await api.post('/api/v1/workspace/sessions', {
          title: '文献问答',
        });
        const s = data.data as SessionItem;
        sessions.value.unshift(s);
        chatSessionId.value = s.id;
        chatSessionTitle.value = s.title;
      } catch {
        return;
      }
    }
    // Send the question — small delay to let DOM settle
    chatInput.value = pendingAsk;
    setTimeout(() => sendMessage(), 200);
  }
});

// Refresh notes count when sessions load
watch(sessions, () => {
  fetchNotesForSession();
  fetchReports();
});
</script>

<style scoped>
/* ---- Layout ---- */
.research-workspace {
  max-width: 1100px;
  margin: 0 auto;
  padding: 0 20px 60px;
}

.rw-back-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid var(--color-border, #e2e8f0);
  margin-bottom: 20px;
}

.back-link {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-accent, #4299e1);
  text-decoration: none;
}
.back-link:hover { text-decoration: underline; }

.back-context {
  font-size: 12px;
  color: var(--color-text-muted, #a0aec0);
}

/* ---- Header ---- */
.rw-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
}

.rw-header h1 {
  font-size: 24px;
  font-weight: 700;
  color: var(--color-text-primary, #1a365d);
  margin: 0 0 4px;
}

.rw-subtitle {
  color: var(--color-text-muted, #718096);
  font-size: 14px;
  margin: 0;
}

.rw-topic-badge {
  font-size: 13px;
  padding: 6px 14px;
  border: 1px solid var(--color-accent, #4299e1);
  border-radius: 20px;
  color: var(--color-accent, #2b6cb0);
  background: var(--color-active, #ebf8ff);
}

/* ---- Tabs ---- */
.rw-tabs {
  display: flex;
  gap: 2px;
  border-bottom: 2px solid var(--color-border, #e2e8f0);
  margin-bottom: 24px;
}

.rw-tab {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 20px;
  border: none;
  background: transparent;
  font-size: 14px;
  color: var(--color-text-secondary, #718096);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  transition: all 0.15s;
  position: relative;
}

.rw-tab:hover {
  color: var(--color-text-primary, #1a365d);
  background: var(--color-hover, #edf2f7);
}

.rw-tab.active {
  color: var(--color-accent, #2b6cb0);
  border-bottom-color: var(--color-accent, #2b6cb0);
  font-weight: 600;
}

.rw-tab-icon { font-size: 16px; }

.rw-tab-badge {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 10px;
  background: var(--color-accent, #4299e1);
  color: #fff;
  font-weight: 600;
  min-width: 18px;
  text-align: center;
}

/* ---- Panel ---- */
.rw-panel {
  animation: rwFadeIn 0.15s ease;
}

@keyframes rwFadeIn {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}

.rw-panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 10px;
}

.rw-panel-header h2 {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text-primary, #1a365d);
  margin: 0;
}

.rw-panel-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

/* ---- Search ---- */
.rw-search-input {
  padding: 6px 12px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 6px;
  font-size: 13px;
  width: 200px;
  background: var(--color-page-bg, #fafafa);
  color: var(--color-text-primary, #1a365d);
}
.rw-search-input:focus {
  outline: none;
  border-color: var(--color-accent, #4299e1);
}

.rw-action-link {
  font-size: 13px;
  color: var(--color-accent, #4299e1);
  text-decoration: none;
  font-weight: 600;
  white-space: nowrap;
  background: none;
  border: none;
  cursor: pointer;
}
.rw-action-link:hover { text-decoration: underline; }
.rw-action-link--btn { font-family: inherit; }

/* ---- List ---- */
.rw-list {
  list-style: none;
  margin: 0;
  padding: 0;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 8px;
  overflow: hidden;
}

.rw-list-item {
  border-bottom: 1px solid var(--color-border, #e2e8f0);
}
.rw-list-item:last-child { border-bottom: none; }

.rw-item-link {
  display: flex;
  align-items: baseline;
  gap: 12px;
  padding: 12px 16px;
  text-decoration: none;
  transition: background 0.1s;
  flex-wrap: wrap;
}
.rw-item-link:hover { background: var(--color-hover, #edf2f7); }

.rw-item-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary, #1a365d);
  min-width: 0;
}

.rw-item-sub {
  font-size: 13px;
  color: var(--color-text-secondary, #4a5568);
}

.rw-item-meta {
  display: flex;
  gap: 6px;
  margin-left: auto;
  flex-wrap: wrap;
}

.rw-tag {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  background: var(--color-page-bg, #fafafa);
  color: var(--color-text-secondary, #718096);
  border: 1px solid var(--color-border, #e2e8f0);
  white-space: nowrap;
}

.rw-tag--dim { opacity: 0.7; }
.rw-tag--accent {
  color: var(--color-accent, #2b6cb0);
  border-color: var(--color-accent, #2b6cb0);
  background: var(--color-active, #ebf8ff);
}

/* ---- Buttons ---- */
.rw-btn {
  padding: 8px 16px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 6px;
  background: var(--color-navbar-bg, #fff);
  font-size: 13px;
  cursor: pointer;
  color: var(--color-accent, #2b6cb0);
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
  white-space: nowrap;
}
.rw-btn:hover:not(:disabled) { background: var(--color-hover, #edf2f7); }
.rw-btn:disabled { opacity: 0.4; cursor: not-allowed; }

.rw-btn--sm { padding: 5px 12px; font-size: 12px; }
.rw-btn--primary {
  background: var(--color-accent, #4299e1);
  color: #fff;
  border-color: var(--color-accent, #4299e1);
}
.rw-btn--primary:hover { background: var(--color-accent-hover, #3182ce); }
.rw-btn--full { width: 100%; }

/* ---- Select ---- */
.rw-select {
  padding: 6px 10px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 6px;
  font-size: 13px;
  background: var(--color-page-bg, #fafafa);
  color: var(--color-text-primary, #1a365d);
}
.rw-select--full { width: 100%; }
.rw-select--inline { margin-top: 8px; }

/* ---- Loading / Error / Empty ---- */
.rw-loading, .rw-error, .rw-empty {
  text-align: center;
  padding: 40px 20px;
  font-size: 14px;
  color: var(--color-text-muted, #a0aec0);
}
.rw-error { color: var(--color-error-text, #c53030); }

/* ---- Pagination ---- */
.rw-pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 12px;
  margin-top: 16px;
  font-size: 13px;
}
.rw-pagination button {
  padding: 6px 14px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 6px;
  background: var(--color-navbar-bg, #fff);
  cursor: pointer;
  font-size: 13px;
}
.rw-pagination button:disabled { opacity: 0.4; cursor: not-allowed; }
.rw-pagination button:hover:not(:disabled) { background: var(--color-hover, #edf2f7); }

/* ---- Notes ---- */
.rw-quick-note {
  margin-bottom: 16px;
  padding: 12px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 8px;
  background: var(--color-page-bg, #fafafa);
}

.rw-textarea {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 6px;
  font-size: 14px;
  font-family: inherit;
  resize: vertical;
  background: var(--color-navbar-bg, #fff);
  color: var(--color-text-primary, #1a365d);
  line-height: 1.5;
  box-sizing: border-box;
}
.rw-textarea:focus {
  outline: none;
  border-color: var(--color-accent, #4299e1);
}

.rw-notes-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 10px;
}

.rw-note-card {
  position: relative;
  padding: 12px 14px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 8px;
  background: var(--color-navbar-bg, #fff);
  transition: box-shadow 0.15s;
}
.rw-note-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.05); }

.rw-note-meta {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 6px;
  flex-wrap: wrap;
}
.rw-note-session {
  font-size: 11px;
  color: var(--color-text-muted, #a0aec0);
}
.rw-note-date {
  font-size: 11px;
  color: var(--color-text-muted, #a0aec0);
  margin-left: auto;
}
.rw-note-content {
  margin: 0;
  font-size: 14px;
  color: var(--color-text-primary, #1a365d);
  line-height: 1.5;
}
.rw-note-delete {
  position: absolute;
  top: 8px;
  right: 8px;
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 16px;
  color: var(--color-text-muted, #a0aec0);
  opacity: 0;
  transition: opacity 0.15s;
  padding: 2px 6px;
  border-radius: 4px;
}
.rw-note-card:hover .rw-note-delete { opacity: 1; }
.rw-note-delete:hover { background: rgba(197, 48, 48, 0.1); color: var(--color-error-text, #c53030); }

/* ---- Reports ---- */
.rw-reports-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.rw-report-card {
  padding: 16px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 10px;
  background: var(--color-navbar-bg, #fff);
}

.rw-report-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 10px;
}
.rw-report-header h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary, #1a365d);
}
.rw-report-date {
  font-size: 12px;
  color: var(--color-text-muted, #a0aec0);
}

.rw-report-steps {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 10px;
}

.rw-step-badge {
  font-size: 11px;
  padding: 3px 8px;
  border-radius: 4px;
  border: 1px solid var(--color-border, #e2e8f0);
  color: var(--color-text-secondary, #718096);
}
.rw-step--completed {
  border-color: #38a169;
  color: #38a169;
  background: #f0fff4;
}
.rw-step--failed {
  border-color: #c53030;
  color: #c53030;
  background: #fff5f5;
}
.rw-step--running {
  border-color: var(--color-accent, #4299e1);
  color: var(--color-accent, #4299e1);
  background: var(--color-active, #ebf8ff);
}

.rw-report-preview {
  margin-bottom: 10px;
}

.rw-report-section {
  margin-bottom: 8px;
}
.rw-report-section strong {
  font-size: 13px;
  color: var(--color-text-secondary, #4a5568);
}
.rw-report-section p {
  margin: 3px 0 0;
  font-size: 13px;
  color: var(--color-text-muted, #718096);
  line-height: 1.5;
}

.rw-report-actions {
  display: flex;
  gap: 8px;
}

/* ---- Assistant ---- */
.rw-panel--assistant {
  height: calc(100vh - 280px);
  min-height: 500px;
}

.rw-assistant-layout {
  display: grid;
  grid-template-columns: 1fr 260px;
  height: 100%;
  gap: 0;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 10px;
  overflow: hidden;
}

.rw-chat-area {
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--color-border, #e2e8f0);
}

.rw-chat-body {
  flex: 1;
  overflow-y: auto;
  padding: 12px 16px;
  min-height: 200px;
}

.rw-chat-empty {
  text-align: center;
  padding: 40px 10px;
}
.rw-chat-empty p {
  color: var(--color-text-muted, #a0aec0);
  font-size: 14px;
  margin: 0 0 16px;
}

.rw-chat-prompts {
  display: flex;
  flex-direction: column;
  gap: 6px;
  align-items: center;
}

.rw-prompt-chip {
  padding: 8px 16px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 20px;
  background: var(--color-navbar-bg, #fff);
  font-size: 13px;
  cursor: pointer;
  color: var(--color-text-secondary, #4a5568);
  transition: all 0.15s;
  max-width: 360px;
  text-align: left;
}
.rw-prompt-chip:hover {
  border-color: var(--color-accent, #4299e1);
  color: var(--color-accent, #2b6cb0);
}

.rw-chat-msg {
  margin-bottom: 12px;
  font-size: 13px;
  line-height: 1.5;
}
.rw-chat-msg--user .rw-chat-content {
  background: var(--color-active, #ebf8ff);
  border-radius: 8px 8px 0 8px;
  padding: 8px 12px;
}
.rw-chat-msg--assistant .rw-chat-content {
  background: var(--color-page-bg, #fafafa);
  border-radius: 8px 8px 8px 0;
  padding: 8px 12px;
}
.rw-chat-role { font-size: 12px; margin-bottom: 2px; display: block; }

.rw-typing { animation: rwBlink 1s infinite; }
@keyframes rwBlink { 0%,100%{opacity:1} 50%{opacity:0.3} }

.rw-chat-input-row {
  display: flex;
  padding: 10px 12px;
  border-top: 1px solid var(--color-border, #e2e8f0);
  gap: 8px;
}

.rw-chat-input {
  flex: 1;
  padding: 8px 14px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 20px;
  font-size: 13px;
  outline: none;
  background: var(--color-page-bg, #fafafa);
  color: var(--color-text-primary, #1a365d);
}
.rw-chat-input:focus { border-color: var(--color-accent, #4299e1); }

.rw-chat-send {
  width: 36px;
  height: 36px;
  border: none;
  border-radius: 50%;
  background: var(--color-accent, #2b6cb0);
  color: #fff;
  font-size: 16px;
  cursor: pointer;
  flex-shrink: 0;
  transition: opacity 0.15s;
}
.rw-chat-send:disabled { opacity: 0.4; cursor: not-allowed; }

/* ---- Assistant Sidebar ---- */
.rw-assistant-sidebar {
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow-y: auto;
}

.rw-sidebar-section { /* no extra styles needed */ }

.rw-sidebar-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--color-text-muted, #a0aec0);
  text-transform: uppercase;
  display: block;
  margin-bottom: 6px;
}

.rw-session-label {
  font-size: 12px;
  color: var(--color-text-muted, #a0aec0);
}

.rw-sidebar-empty {
  font-size: 12px;
  color: var(--color-text-muted, #a0aec0);
  padding: 10px 0;
}

.rw-evidence-item {
  padding: 6px 0;
  font-size: 12px;
  border-bottom: 1px solid var(--color-border, #e2e8f0);
}
.rw-evidence-type {
  font-weight: 600;
  color: var(--color-accent, #2b6cb0);
  margin-right: 6px;
}
.rw-evidence-text {
  color: var(--color-text-secondary, #718096);
}
.rw-evidence-actions {
  display: inline-flex;
  gap: 4px;
  margin-left: 6px;
  vertical-align: middle;
}
.rw-evidence-action-btn {
  border: none;
  background: transparent;
  font-size: 14px;
  cursor: pointer;
  padding: 2px 4px;
  border-radius: 4px;
  opacity: 0.5;
  transition: opacity 0.15s, background 0.15s;
}
.rw-evidence-action-btn:hover {
  opacity: 1;
  background: var(--color-hover, #edf2f7);
}
.rw-evidence-action-btn.saved {
  opacity: 1;
  color: #38a169;
}

/* ---- Responsive ---- */
@media (max-width: 768px) {
  .rw-tabs {
    overflow-x: auto;
    flex-wrap: nowrap;
  }
  .rw-tab {
    padding: 8px 14px;
    font-size: 13px;
    white-space: nowrap;
  }
  .rw-assistant-layout {
    grid-template-columns: 1fr;
    grid-template-rows: 1fr auto;
  }
  .rw-assistant-sidebar {
    border-top: 1px solid var(--color-border, #e2e8f0);
    max-height: 200px;
  }
  .rw-panel--assistant {
    height: auto;
    min-height: 400px;
  }
  .rw-notes-grid {
    grid-template-columns: 1fr;
  }
  .rw-panel-header {
    flex-direction: column;
    align-items: flex-start;
  }
  .rw-search-input {
    width: 150px;
  }
}
</style>
