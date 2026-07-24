<template>
  <div class="workspace-layout">
    <!-- Back to current research -->
    <div v-if="researchStore.hasActiveResearch" class="workspace-back-bar">
      <router-link :to="{ name: 'research-home' }" class="back-link">
        {{ t('researchEntry.backToResearch') }}
      </router-link>
      <span class="back-context">{{ researchStore.currentTopic?.name }}</span>
    </div>

    <div class="workspace-body">
      <!-- Left Panel: Knowledge Navigator -->
      <aside class="panel panel--left">
      <div class="panel-header">
        <h3>{{ t('workspace.knowledgeNav') }}</h3>
      </div>
      <div class="panel-body">
        <!-- Session list -->
        <div class="section">
          <div class="section-header">
            <span>{{ t('workspace.sessions') }}</span>
            <button class="icon-btn" @click="createSession" :disabled="!auth.isAuthenticated">+</button>
          </div>
          <ul v-if="sessions.length > 0" class="session-list">
            <li
              v-for="s in sessions"
              :key="s.id"
              class="session-item"
              :class="{ 'session-item--active': activeSession?.id === s.id }"
              @click="selectSession(s)"
            >
              {{ s.title }}
            </li>
          </ul>
          <p v-else class="muted">{{ t('workspace.noSessions') }}</p>
          <p v-if="sessions.length === 0" class="muted muted--hint">{{ t('onboarding.noSessionsHint') }}</p>
        </div>

        <!-- Entity browser -->
        <div class="section">
          <div class="section-header">{{ t('workspace.entityBrowser') }}</div>
          <div class="entity-actions">
            <button class="action-btn action-btn--sm" @click="browseEntity('person')">👤 {{ t('nav.persons') }}</button>
            <button class="action-btn action-btn--sm" @click="browseEntity('book')">📚 {{ t('nav.books') }}</button>
          </div>
        </div>
      </div>
    </aside>

    <!-- Center Panel: Research Canvas -->
    <main class="panel panel--center">
      <div class="panel-header">
        <h3>{{ activeSession?.title || t('workspace.researchCanvas') }}</h3>
        <div class="panel-header-actions">
          <button class="action-btn action-btn--sm" @click="autoSave" :disabled="!activeSession">
            💾 {{ t('common.save') }}
          </button>
        </div>
      </div>
      <div class="panel-body panel-body--scroll">
        <!-- Context Notes (Markdown editor) -->
        <div class="canvas-section">
          <label class="section-label">{{ t('workspace.contextNotes') }}</label>
          <textarea
            v-model="contextNotes"
            class="notes-editor"
            :placeholder="t('workspace.notesPlaceholder')"
            rows="10"
          ></textarea>
        </div>

        <!-- Active Entities -->
        <div v-if="activeEntities.length > 0" class="canvas-section">
          <label class="section-label">{{ t('workspace.activeEntities') }}</label>
          <div class="entity-chips">
            <span v-for="eid in activeEntities" :key="eid" class="entity-chip">
              {{ eid }}
              <button class="chip-remove" @click="removeEntity(eid)">×</button>
            </span>
          </div>
        </div>

        <!-- Research Notes -->
        <div class="canvas-section">
          <div class="section-header">
            <label class="section-label">{{ t('workspace.notes') }}</label>
            <button class="icon-btn" @click="addNote">+</button>
          </div>
          <div v-if="notes.length > 0" class="notes-list">
            <article v-for="note in notes" :key="note.id" class="note-card">
              <div class="note-meta">
                <span v-if="note.entity_type" class="note-badge">{{ note.entity_type }}</span>
                <span v-if="note.tags" class="note-tags">{{ note.tags }}</span>
              </div>
              <p class="note-content">{{ note.content }}</p>
              <button class="note-delete" @click="deleteNote(note.id)">🗑️</button>
            </article>
          </div>
          <p v-else class="muted">{{ t('workspace.noNotes') }}</p>
        </div>
      </div>
    </main>

    <!-- Right Panel: AI Assistant + Evidence -->
    <aside class="panel panel--right">
      <!-- AI Assistant -->
      <div class="panel-section panel-section--chat">
        <div class="panel-header">
          <h3>{{ t('workspace.aiAssistant') }}</h3>
        </div>
        <div class="chat-body" ref="chatBodyRef">
          <div v-if="chatMessages.length === 0" class="chat-empty">
            {{ t('workspace.chatPlaceholder') }}
          </div>
          <div
            v-for="(msg, idx) in chatMessages"
            :key="idx"
            class="chat-message"
            :class="`chat-message--${msg.role}`"
          >
            <div class="chat-role">{{ msg.role === 'user' ? '👤' : '🤖' }}</div>
            <div class="chat-content" v-text="msg.content"></div>
          </div>
          <div v-if="chatLoading" class="chat-message chat-message--assistant">
            <div class="chat-role">🤖</div>
            <div class="chat-content"><span class="typing-indicator">...</span></div>
          </div>
        </div>
        <div class="chat-input-area">
          <input
            v-model="chatInput"
            type="text"
            class="chat-input"
            :placeholder="t('workspace.chatPlaceholder')"
            @keyup.enter="sendMessage"
          />
          <button class="chat-send-btn" @click="sendMessage" :disabled="!chatInput.trim() || chatLoading">
            ➤
          </button>
        </div>
      </div>

      <!-- Evidence Panel -->
      <div class="panel-section panel-section--evidence">
        <div class="panel-header">
          <h3>{{ t('workspace.evidence') }}</h3>
        </div>
        <div class="panel-body">
          <p v-if="evidence.length === 0" class="muted">{{ t('workspace.evidenceHint') }}</p>
          <div v-for="(ev, idx) in evidence" :key="idx" class="evidence-item">
            <span class="evidence-type">{{ ev.entity_type }}</span>
            <span class="evidence-text">{{ ev.content?.substring(0, 100) }}</span>
          </div>
        </div>
      </div>
    </aside>
    </div> <!-- /workspace-body -->
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';
import api from '@/api/client';
import { useAuthStore } from '@/stores/auth';
import { useResearchStore } from '@/stores/research';

const { t } = useI18n();
const router = useRouter();
const auth = useAuthStore();
const researchStore = useResearchStore();

// --- State ---
interface Session {
  id: string;
  title: string;
  active_entities: string[] | null;
  context_notes: string | null;
}

interface Note {
  id: string;
  content: string;
  entity_type: string | null;
  entity_id: string | null;
  tags: string | null;
}

const sessions = ref<Session[]>([]);
const activeSession = ref<Session | null>(null);
const contextNotes = ref('');
const activeEntities = ref<string[]>([]);
const notes = ref<Note[]>([]);
const chatMessages = ref<{ role: string; content: string }[]>([]);
const chatInput = ref('');
const chatLoading = ref(false);
const evidence = ref<{ entity_type: string; content?: string }[]>([]);
const chatBodyRef = ref<HTMLElement | null>(null);

// --- Load sessions ---
async function loadSessions() {
  if (!auth.isAuthenticated) return;
  try {
    const { data } = await api.get('/api/v1/workspace/sessions');
    sessions.value = (data.data ?? []) as Session[];
  } catch { /* ignore */ }
}

// --- Session management ---
async function createSession() {
  try {
    const { data } = await api.post('/api/v1/workspace/sessions', { title: '未命名研究' });
    const s = data.data as Session;
    sessions.value.unshift(s);
    selectSession(s);
  } catch { /* ignore */ }
}

async function selectSession(s: Session) {
  activeSession.value = s;
  contextNotes.value = s.context_notes || '';
  activeEntities.value = s.active_entities || [];
  chatMessages.value = [];

  // Load notes
  try {
    const { data } = await api.get(`/api/v1/workspace/sessions/${s.id}/notes`);
    notes.value = (data.data ?? []) as Note[];
  } catch { notes.value = []; }

  // Load chat history
  try {
    const { data } = await api.get(`/api/v1/workspace/sessions/${s.id}`);
    const full = data.data;
    if (full?.chat_history) {
      chatMessages.value = full.chat_history;
    }
  } catch { /* ignore */ }
}

async function autoSave() {
  if (!activeSession.value) return;
  try {
    await api.patch(`/api/v1/workspace/sessions/${activeSession.value.id}`, {
      context_notes: contextNotes.value,
      active_entities: activeEntities.value,
    });
  } catch { /* ignore */ }
}

// --- AI Chat ---
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
        session_id: activeSession.value?.id,
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
        const { data } = await api.get('/api/v1/search', { params: { q: msg, limit: 3 } });
        evidence.value = (data.data?.items ?? []).slice(0, 3);
      } catch { evidence.value = []; }
    }
  } catch {
    chatMessages.value.push({ role: 'assistant', content: '⚠️ 连接失败，请重试' });
  } finally {
    chatLoading.value = false;
    nextTick(() => {
      if (chatBodyRef.value) chatBodyRef.value.scrollTop = chatBodyRef.value.scrollHeight;
    });
  }
}

// --- Notes ---
async function addNote() {
  if (!activeSession.value) return;
  const content = prompt(t('workspace.noteContent'));
  if (!content) return;
  try {
    const { data } = await api.post(`/api/v1/workspace/sessions/${activeSession.value.id}/notes`, { content });
    notes.value.unshift(data.data as Note);
  } catch { /* ignore */ }
}

async function deleteNote(noteId: string) {
  try {
    await api.delete(`/api/v1/workspace/notes/${noteId}`);
    notes.value = notes.value.filter(n => n.id !== noteId);
  } catch { /* ignore */ }
}

// --- Entities ---
function removeEntity(eid: string) {
  activeEntities.value = activeEntities.value.filter(e => e !== eid);
  autoSave();
}

function browseEntity(type: string) {
  router.push(type === 'person' ? '/persons' : '/books');
}

// --- Init ---
loadSessions();
</script>

<style scoped>
/* --- Back to research bar --- */
.workspace-back-bar {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) 20px;
  background: var(--color-page-bg);
  border-bottom: 1px solid var(--color-border);
  grid-column: 1 / -1;
}

.back-link {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-accent);
  text-decoration: none;
}

.back-link:hover {
  text-decoration: underline;
}

.back-context {
  font-size: 12px;
  color: var(--color-text-muted);
}

.workspace-layout {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 56px);
  overflow: hidden;
}

.workspace-body {
  display: grid;
  grid-template-columns: 240px 1fr 320px;
  flex: 1;
  overflow: hidden;
}

.panel {
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--color-border);
  background: var(--color-navbar-bg, var(--color-surface));
}

.panel--right {
  border-right: none;
  border-left: 1px solid var(--color-border);
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3) 16px;
  border-bottom: 1px solid var(--color-border);
}

.panel-header h3 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.panel-body {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-3) 16px;
}

.panel-body--scroll {
  overflow-y: auto;
}

/* --- Sections --- */
.section {
  margin-bottom: 20px;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-muted);
  text-transform: uppercase;
}

.section-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-muted);
  text-transform: uppercase;
  margin-bottom: 8px;
  display: block;
}

/* --- Session list --- */
.session-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.session-item {
  padding: var(--space-2) 10px;
  border-radius: var(--radius-md);
  font-size: 13px;
  cursor: pointer;
  color: var(--color-text-secondary, var(--color-text-muted));
  transition: all var(--transition-fast);
}

.session-item:hover {
  background: var(--color-hover);
}

.session-item--active {
  background: var(--color-accent-light);
  color: var(--color-accent);
  font-weight: 600;
}

/* --- Buttons --- */
.icon-btn {
  width: 24px;
  height: 24px;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  font-size: 16px;
  cursor: pointer;
  color: var(--color-text-secondary, var(--color-text-muted));
  display: flex;
  align-items: center;
  justify-content: center;
}

.icon-btn:hover { background: var(--color-hover); }
.icon-btn:disabled { opacity: 0.4; cursor: not-allowed; }

.action-btn {
  padding: var(--space-2) 16px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: transparent;
  font-size: 13px;
  cursor: pointer;
  color: var(--color-accent);
  transition: all var(--transition-base);
}

.action-btn:hover { background: var(--color-hover); }
.action-btn:disabled { opacity: 0.4; cursor: not-allowed; }

.action-btn--sm {
  padding: var(--space-1) 10px;
  font-size: 12px;
}

/* --- Canvas --- */
.canvas-section {
  margin-bottom: 24px;
}

.notes-editor {
  width: 100%;
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: 14px;
  font-family: inherit;
  resize: vertical;
  background: var(--color-page-bg);
  color: var(--color-text-primary);
  line-height: 1.6;
}

.entity-chips {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1-5);
}

.entity-chip {
  display: flex;
  align-items: center;
  gap: var(--space-1-5);
  padding: var(--space-1) 10px;
  border: 1px solid var(--color-accent);
  border-radius: var(--radius-xl);
  font-size: 12px;
  color: var(--color-accent);
  background: var(--color-accent-alpha-05);
}

.chip-remove {
  border: none;
  background: transparent;
  color: var(--color-text-muted);
  cursor: pointer;
  font-size: 14px;
  padding: 0;
  line-height: 1;
}

/* --- Notes --- */
.notes-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.note-card {
  position: relative;
  padding: var(--space-2-5) 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}

.note-meta {
  display: flex;
  gap: var(--space-1-5);
  margin-bottom: 4px;
}

.note-badge {
  font-size: 10px;
  padding: var(--space-0-5) 6px;
  border-radius: var(--radius-sm);
  background: var(--color-accent-light);
  color: var(--color-accent);
}

.note-tags {
  font-size: 10px;
  color: var(--color-text-muted);
}

.note-content {
  margin: 0;
  font-size: 13px;
  color: var(--color-text-primary);
  line-height: 1.4;
}

.note-delete {
  position: absolute;
  top: 6px;
  right: 6px;
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 12px;
  opacity: 0;
  transition: opacity var(--transition-base);
}

.note-card:hover .note-delete { opacity: 1; }

/* --- Chat --- */
.panel-section {
  display: flex;
  flex-direction: column;
  border-bottom: 1px solid var(--color-border);
}

.panel-section--chat {
  flex: 1;
  min-height: 0;
}

.panel-section--evidence {
  max-height: 200px;
}

.chat-body {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-2) 12px;
  min-height: 200px;
}

.chat-empty {
  text-align: center;
  color: var(--color-text-muted);
  font-size: 13px;
  padding: var(--space-10) 0;
}

.chat-message {
  margin-bottom: 12px;
  font-size: 13px;
  line-height: 1.5;
}

.chat-message--user .chat-content {
  background: var(--color-accent-light);
  border-radius: var(--radius-lg) 8px 0 8px;
  padding: var(--space-2) 12px;
}

.chat-message--assistant .chat-content {
  background: var(--color-page-bg);
  border-radius: var(--radius-lg) 8px 8px 0;
  padding: var(--space-2) 12px;
}

.chat-role {
  font-size: 12px;
  margin-bottom: 2px;
}

.chat-input-area {
  display: flex;
  padding: var(--space-2) 12px;
  border-top: 1px solid var(--color-border);
  gap: var(--space-2);
}

.chat-input {
  flex: 1;
  padding: var(--space-2) 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  font-size: 13px;
  outline: none;
  background: var(--color-page-bg);
}

.chat-input:focus {
  border-color: var(--color-accent);
}

.chat-send-btn {
  width: 36px;
  height: 36px;
  border: none;
  border-radius: 50%;
  background: var(--color-accent);
  color: white;
  font-size: 16px;
  cursor: pointer;
  flex-shrink: 0;
  transition: opacity var(--transition-base);
}

.chat-send-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* --- Evidence --- */
.evidence-item {
  padding: var(--space-1-5) 0;
  font-size: 12px;
  border-bottom: 1px solid var(--color-border);
}

.evidence-type {
  font-weight: 600;
  color: var(--color-accent);
  margin-right: 6px;
}

.evidence-text {
  color: var(--color-text-secondary, var(--color-text-muted));
}

/* --- Utility --- */
.muted {
  color: var(--color-text-muted);
  font-size: 13px;
  text-align: center;
  padding: var(--space-5) 0;
}
.muted--hint {
  padding-top: 0;
  font-size: 12px;
  opacity: 0.75;
}

.entity-actions {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.typing-indicator {
  animation: blink var(--transition-slow) infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

@media (max-width: 1024px) {
  .workspace-body {
    grid-template-columns: 1fr;
    grid-template-rows: auto 1fr auto;
  }
  .panel--left, .panel--right {
    max-height: 200px;
    border-right: none;
    border-bottom: 1px solid var(--color-border);
  }
}
</style>
