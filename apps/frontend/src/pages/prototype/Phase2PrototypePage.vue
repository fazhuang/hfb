<template>
  <div class="proto-page">
    <ResearchPageHeader
      :title="'Phase 2 Prototype — 主链路验证'"
      :breadcrumbs="[{ label: 'Prototype', to: '/prototype' }]"
    />

    <div class="proto-body">
      <div class="proto-main">
      <!-- ============================================================ -->
      <!-- Page 1: Anonymous Draft Input -->
      <!-- ============================================================ -->
      <section class="proto-section" id="proto-page1">
        <h2 class="proto-section-title">Page 1 — 首页草稿输入 (Anonymous)</h2>
        <div class="proto-panel">
          <label class="proto-label" for="proto-question">研究问题 (max {{ MAX_QUESTION_LENGTH }} 字)：</label>
          <textarea
            id="proto-question"
            v-model="draftText"
            class="proto-textarea"
            :maxlength="MAX_QUESTION_LENGTH"
            :disabled="isAuthed"
            :placeholder="isAuthed ? '已登录 — 请使用项目工作流' : '请输入您想探索的问题...'"
            rows="3"
          />
          <div class="proto-char-count">{{ draftText.length }} / {{ MAX_QUESTION_LENGTH }}</div>
          <div class="proto-actions">
            <button
              class="proto-btn proto-btn--primary"
              :disabled="!draftText.trim() || isAuthed"
              @click="handleWriteTemp"
            >
              保存临时草稿
            </button>
            <span v-if="tempSaveResult" class="proto-feedback">{{ tempSaveResult }}</span>
          </div>

          <!-- Disabled message when authed -->
          <div v-if="isAuthed" class="proto-notice">
            <span aria-hidden="true">🔒</span>
            <p>已登录用户请通过项目工作流输入问题。当前草稿为匿名模式。</p>
          </div>

          <!-- Honest prompt when storage fails -->
          <div v-if="storageUnavailable" class="proto-notice proto-notice--warn" role="alert">
            <span aria-hidden="true">⚠️</span>
            <p>未保存，登录后重新输入。当前浏览器不支持临时存储。</p>
          </div>

          <!-- Temp key status -->
          <div v-if="tempExists" class="proto-notice proto-notice--info">
            <span aria-hidden="true">📝</span>
            <p>草稿已保存到临时存储 (hfb_temp_pending_question)。登录后自动迁移。</p>
          </div>
        </div>
      </section>

      <!-- ============================================================ -->
      <!-- Page 2: Migration -->
      <!-- ============================================================ -->
      <section class="proto-section" id="proto-page2">
        <h2 class="proto-section-title">Page 2 — 项目确定与草稿迁移</h2>
        <div class="proto-panel">
          <div class="proto-migration-form">
            <label class="proto-label" for="proto-project-id">Project ID (从 Research Module 复制)：</label>
            <div class="proto-input-row">
              <input
                id="proto-project-id"
                v-model="projectIdInput"
                class="proto-input"
                type="text"
                placeholder="UUID v4 project id"
              />
              <button
                class="proto-btn proto-btn--secondary"
                :disabled="!projectIdInput.trim()"
                @click="handleReadCanonical"
              >
                读取项目草稿
              </button>
            </div>
          </div>

          <!-- Migration steps -->
          <div v-if="migrationState !== 'idle'" class="proto-migration-log">
            <h3 class="proto-log-title">迁移步骤 (3-Step Deterministic)</h3>
            <ol class="proto-step-list">
              <li
                v-for="(step, i) in migrationSteps"
                :key="i"
                :class="['proto-step', `proto-step--${step.status}`]"
              >
                <span class="proto-step-name">{{ step.name }}</span>
                <span class="proto-step-status">{{ migrationStatusIcon(step.status) }} {{ step.status }}</span>
                <span v-if="step.detail" class="proto-step-detail">{{ step.detail }}</span>
              </li>
            </ol>
            <div v-if="migrationError" class="proto-notice proto-notice--error" role="alert">
              {{ migrationError }}
            </div>
            <div v-if="migrationState === 'done'" class="proto-notice proto-notice--info">
              ✅ 迁移完成。Canonical Key: hfb.research.{{ projectIdInput }}.pending-question =
              "{{ canonicalQuestion }}"
            </div>
          </div>

          <!-- Migration triggers -->
          <div class="proto-actions">
            <button
              class="proto-btn proto-btn--primary"
              :disabled="!canMigrate || !projectIdInput.trim()"
              @click="handleMigrate"
            >
              执行迁移 (3-Step)
            </button>
            <button
              class="proto-btn proto-btn--secondary"
              :disabled="!projectIdInput.trim()"
              @click="handleClearCanonical"
            >
              清除项目草稿
            </button>
          </div>

          <!-- Canonical key status -->
          <div v-if="hasCanonicalQuestion" class="proto-notice proto-notice--info">
            <span aria-hidden="true">📋</span>
            <p>Canonical question: "{{ canonicalQuestion }}"</p>
          </div>
        </div>
      </section>

      <!-- ============================================================ -->
      <!-- Page 3: Workflow Submission -->
      <!-- ============================================================ -->
      <section class="proto-section" id="proto-page3">
        <h2 class="proto-section-title">Page 3 — 范围确认与 Workflow 提交</h2>
        <div class="proto-panel">
          <div v-if="!hasCanonicalQuestion && !workflowQuestion" class="proto-notice">
            <span aria-hidden="true">📭</span>
            <p>未检测到草稿。请先完成 Page 2 迁移，或在下方直接输入问题。</p>
          </div>

          <div class="proto-migration-form">
            <label class="proto-label" for="proto-wf-question">研究问题 (确认后提交)：</label>
            <textarea
              id="proto-wf-question"
              v-model="workflowQuestion"
              class="proto-textarea"
              :maxlength="MAX_QUESTION_LENGTH"
              placeholder="输入或从 Canonical Key 填充..."
              rows="2"
            />
            <label class="proto-label" for="proto-wf-project">Project ID：</label>
            <input
              id="proto-wf-project"
              v-model="projectIdInput"
              class="proto-input"
              type="text"
              placeholder="UUID v4 project id"
            />
          </div>

          <div class="proto-actions">
            <button
              class="proto-btn proto-btn--secondary"
              :disabled="!projectIdInput.trim()"
              @click="handleFillFromCanonical"
            >
              从 Canonical Key 填充
            </button>
            <button
              class="proto-btn proto-btn--primary"
              :disabled="!workflowQuestion.trim() || !projectIdInput.trim() || submitting"
              @click="handleSubmitWorkflow"
            >
              {{ submitting ? '提交中...' : '开始分析 → POST /api/v4/research/workflow' }}
            </button>
          </div>

          <!-- Submission result -->
          <div v-if="submitError" class="proto-notice proto-notice--error" role="alert">
            {{ submitError }}
          </div>
          <div v-if="wfRunId" class="proto-notice proto-notice--info">
            <span aria-hidden="true">✅</span>
            <p>
              Workflow 提交成功！Run ID: {{ wfRunId }}
              <router-link
                v-if="projectIdInput"
                :to="`/research/${projectIdInput}/result/${wfRunId}`"
                class="proto-link"
              >
                → 跳转到 Result Page
              </router-link>
            </p>
          </div>
          <div v-if="submitCount > 0" class="proto-notice">
            <span aria-hidden="true">📊</span>
            <p>物理请求计数：{{ submitCount }} (应恰好为 1)</p>
          </div>
        </div>
      </section>

      <!-- ============================================================ -->
      <!-- Page 4: Result → Reader Jump -->
      <!-- ============================================================ -->
      <section class="proto-section" id="proto-page4">
        <h2 class="proto-section-title">Page 4 — Result → Reader 跳转验证 (readerAddressable)</h2>
        <div class="proto-panel">
          <div v-if="!hasEvidence" class="proto-notice">
            <span aria-hidden="true">📭</span>
            <p>无证据数据。请先完成 Page 3 Workflow 提交并在 Result 页面加载数据。</p>
          </div>

          <div v-else class="proto-evidence-list">
            <h3 class="proto-log-title">证据列表 — readerAddressable 检测</h3>
            <table class="proto-table">
              <thead>
                <tr>
                  <th>Trace ID</th>
                  <th>Document ID</th>
                  <th>Chunk ID</th>
                  <th>Reader Addressable</th>
                  <th>Jump Link</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="ev in mockEvidence"
                  :key="ev.trace_id"
                >
                  <td><code>{{ ev.trace_id.slice(0, 8) }}...</code></td>
                  <td><code>{{ ev.document_id || '—' }}</code></td>
                  <td><code>{{ ev.chunk_id || '—' }}</code></td>
                  <td>
                    <HfbBadge
                      :variant="isReaderAddressable(ev.document_id, ev.chunk_id) ? 'success' : 'neutral'"
                      :dot="true"
                    >
                      {{ isReaderAddressable(ev.document_id, ev.chunk_id) ? '是' : '否' }}
                    </HfbBadge>
                  </td>
                  <td>
                    <a
                      v-if="isReaderAddressable(ev.document_id, ev.chunk_id)"
                      :href="buildReaderUrl(ev.document_id, ev.chunk_id)!"
                      class="proto-link"
                      target="_blank"
                    >
                      /reader/{{ ev.document_id }}#chunk-{{ ev.chunk_id }}
                    </a>
                    <span v-else class="proto-text-muted">—</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Manual verification -->
          <div class="proto-manual-verify">
            <h3 class="proto-log-title">手动验证</h3>
            <div class="proto-input-row">
              <input v-model="manualDocId" class="proto-input" type="text" placeholder="document_id" />
              <input v-model="manualChunkId" class="proto-input" type="text" placeholder="chunk_id" />
              <a
                v-if="manualDocId && manualChunkId"
                :href="`/reader/${manualDocId}#chunk-${manualChunkId}`"
                class="proto-btn proto-btn--secondary"
                target="_blank"
              >
                测试跳转
              </a>
              <span v-else class="proto-text-muted">输入 document_id + chunk_id 以测试跳转</span>
            </div>
          </div>
        </div>
      </section>

      <!-- ============================================================ -->
      <!-- Responsive Breakpoint Verification with Live HfbDrawer -->
      <!-- ============================================================ -->
      <section class="proto-section" id="proto-responsive">
        <h2 class="proto-section-title">响应式断点验证 — 实时 HfbDrawer</h2>
        <div class="proto-panel">
          <div class="proto-breakpoint-bar">
            <div
              :class="['proto-bp-zone', currentBreakpoint === 'mobile' ? 'proto-bp-zone--active' : '']"
            >
              &lt; 1024px<br />覆盖式 Drawer
            </div>
            <div
              :class="['proto-bp-zone', currentBreakpoint === 'tablet' ? 'proto-bp-zone--active' : '']"
            >
              1024-1439px<br />悬浮 Overlay Drawer
            </div>
            <div
              :class="['proto-bp-zone', currentBreakpoint === 'desktop' ? 'proto-bp-zone--active' : '']"
            >
              ≥ 1440px<br />常驻 Flex 侧栏
            </div>
          </div>
          <p class="proto-bp-current">
            当前断点：<strong>{{ currentBreakpointLabel }}</strong> (viewport: {{ viewportWidth }}px)
          </p>

          <!-- Live HfbDrawer demo trigger -->
          <div class="proto-actions">
            <button class="proto-btn proto-btn--primary" @click="drawerOpen = true">
              打开 HfbDrawer 验证布局
            </button>
            <button class="proto-btn proto-btn--secondary" @click="toggleZoom">
              {{ zoomActive ? '恢复 100% 缩放' : '激活 200% 缩放' }}
            </button>
          </div>

            <p class="proto-hint">
              缩放浏览器窗口以测试断点切换。&lt; 1024px 覆盖 Drawer、1024–1439px 悬浮 Drawer、≥ 1440px 常驻 Flex &lt;aside&gt; 侧栏。200% 缩放下验证无溢出破版。
            </p>

          <!-- Zoom status -->
          <div v-if="zoomActive" class="proto-notice proto-notice--warn" role="alert">
            <span aria-hidden="true">🔍</span>
            <p>200% 缩放已激活 — 检查布局无水平溢出、文字不裁剪、交互元素不重叠。</p>
          </div>
        </div>
      </section>

      <!-- ============================================================ -->
      <!-- Live HfbDrawer for responsive prototyping (mobile/tablet)   -->
      <!-- Replaced by persistent <aside> at ≥ 1440px                 -->
      <!-- ============================================================ -->
      <HfbDrawer
        v-if="currentBreakpoint !== 'desktop'"
        :open="drawerOpen"
        title="Phase 2 — 响应式断点验证抽屉"
        :placement="currentBreakpoint === 'mobile' ? 'bottom' : 'right'"
        :size="drawerSize"
        @update:open="drawerOpen = $event"
      >
        <div class="proto-drawer-content">
          <h3>断点信息</h3>
          <div class="proto-drawer-info-grid">
            <div class="proto-drawer-info-item">
              <span class="proto-drawer-info-label">断点</span>
              <span class="proto-drawer-info-value">{{ currentBreakpointLabel }}</span>
            </div>
            <div class="proto-drawer-info-item">
              <span class="proto-drawer-info-label">视口宽度</span>
              <span class="proto-drawer-info-value">{{ viewportWidth }}px</span>
            </div>
            <div class="proto-drawer-info-item">
              <span class="proto-drawer-info-label">Drawer 模式</span>
              <span class="proto-drawer-info-value">{{ drawerModeLabel }}</span>
            </div>
            <div class="proto-drawer-info-item">
              <span class="proto-drawer-info-label">缩放级别</span>
              <span class="proto-drawer-info-value">{{ zoomActive ? '200%' : '100%' }}</span>
            </div>
          </div>

          <h3 style="margin-top: var(--space-6)">黄金行宽测试文本（40 字）</h3>
          <p class="proto-golden-line">
            皇甫谧幼年过继给叔父十五岁时随叔父迁居新安因战乱频仍皇甫谧失去了正规求学的机会但他并未气馁
          </p>
          <p class="proto-golden-note">
            ← 此段恰好 40 汉字，在 1024–1439px 断点下应在一行内完整显示不折行。
          </p>

          <h3 style="margin-top: var(--space-6)">溢出测试</h3>
          <div class="proto-overflow-box">
            <code>hfb.research.{{ projectIdInput || '<projectId>' }}.pending-question</code>
          </div>
          <p class="proto-golden-note">
            ← 长 Key 字符串应自动折行，不产生水平溢出。
          </p>
        </div>

        <template #footer>
          <button class="proto-btn proto-btn--secondary" @click="drawerOpen = false">
            关闭 Drawer
          </button>
        </template>
      </HfbDrawer>
      </div><!-- .proto-main -->

      <!-- Persistent sidebar: flex <aside> pinned to viewport at ≥1440px -->
      <aside v-if="currentBreakpoint === 'desktop'" class="proto-aside">
        <div class="proto-aside-header">
          <h3 class="proto-aside-title">Phase 2 — 响应式侧栏</h3>
        </div>
        <div class="proto-drawer-content">
          <h3>断点信息</h3>
          <div class="proto-drawer-info-grid">
            <div class="proto-drawer-info-item">
              <span class="proto-drawer-info-label">断点</span>
              <span class="proto-drawer-info-value">{{ currentBreakpointLabel }}</span>
            </div>
            <div class="proto-drawer-info-item">
              <span class="proto-drawer-info-label">视口宽度</span>
              <span class="proto-drawer-info-value">{{ viewportWidth }}px</span>
            </div>
            <div class="proto-drawer-info-item">
              <span class="proto-drawer-info-label">布局模式</span>
              <span class="proto-drawer-info-value">常住 Flex 侧栏</span>
            </div>
            <div class="proto-drawer-info-item">
              <span class="proto-drawer-info-label">缩放级别</span>
              <span class="proto-drawer-info-value">{{ zoomActive ? '200%' : '100%' }}</span>
            </div>
          </div>

          <h3 style="margin-top: var(--space-6)">黄金行宽测试文本（40 字）</h3>
          <p class="proto-golden-line">
            皇甫谧幼年过继给叔父十五岁时随叔父迁居新安因战乱频仍皇甫谧失去了正规求学的机会但他并未气馁
          </p>
          <p class="proto-golden-note">
            ← 此段恰好 40 汉字，在 1024–1439px 断点下应在一行内完整显示不折行。
          </p>

          <h3 style="margin-top: var(--space-6)">溢出测试</h3>
          <div class="proto-overflow-box">
            <code>hfb.research.{{ projectIdInput || '<projectId>' }}.pending-question</code>
          </div>
          <p class="proto-golden-note">
            ← 长 Key 字符串应自动折行，不产生水平溢出。
          </p>
        </div>
      </aside>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
import { useRoute } from 'vue-router';
import ResearchPageHeader from '@/components/layout/ResearchPageHeader.vue';
import HfbBadge from '@/components/common/HfbBadge.vue';
import { usePrototypeDraft } from '@/composables/usePrototypeDraft';
import { useAuthStore } from '@/stores/auth';
import HfbDrawer from '@/components/common/HfbDrawer.vue';
import api from '@/api/client';

const route = useRoute();
const auth = useAuthStore();

const {
  tempQuestion,
  tempExists,
  writeTempQuestion,
  readTempQuestion,
  canonicalQuestion,
  readCanonicalQuestion,
  clearCanonicalQuestion,
  migrationState,
  migrationSteps,
  migrationError,
  migrateTempToCanonical,
  canMigrate,
  hasCanonicalQuestion,
  isReaderAddressable,
  buildReaderUrl,
  init,
  MAX_QUESTION_LENGTH,
} = usePrototypeDraft();

// ---- Page 1 state ----
const draftText = ref('');
const tempSaveResult = ref('');
const storageUnavailable = ref(false);
const isAuthed = computed(() => auth.isAuthenticated);

function handleWriteTemp() {
  const ok = writeTempQuestion(draftText.value);
  if (!ok) {
    storageUnavailable.value = true;
    tempSaveResult.value = '';
  } else {
    storageUnavailable.value = false;
    tempSaveResult.value = '草稿已保存 (hfb_temp_pending_question)';
    setTimeout(() => { tempSaveResult.value = ''; }, 3000);
  }
}

// ---- Page 2 state ----
const projectIdInput = ref('');

function handleReadCanonical() {
  readCanonicalQuestion(projectIdInput.value);
}

function handleMigrate() {
  migrateTempToCanonical(projectIdInput.value);
  if (migrationState.value === 'done') {
    readCanonicalQuestion(projectIdInput.value);
  }
}

function handleClearCanonical() {
  clearCanonicalQuestion(projectIdInput.value);
}

function migrationStatusIcon(status: string): string {
  switch (status) {
    case 'running': return '⏳';
    case 'done': return '✅';
    case 'failed': return '❌';
    default: return '⬜';
  }
}

// ---- Page 3 state ----
const workflowQuestion = ref('');
const submitting = ref(false);
const submitError = ref('');
const submitCount = ref(0);
const wfRunId = ref('');

function handleFillFromCanonical() {
  const q = readCanonicalQuestion(projectIdInput.value);
  if (q) {
    workflowQuestion.value = q;
  }
}

async function handleSubmitWorkflow() {
  if (submitting.value) return;
  submitting.value = true;
  submitError.value = '';
  wfRunId.value = '';

  try {
    const { data } = await api.post(
      '/api/v4/research/workflow',
      {
        session_id: projectIdInput.value.trim(),
        topic: workflowQuestion.value.trim(),
        workflow_type: 'full_research_flow',
      },
      { timeout: 120000 },
    );
    submitCount.value++;
    if (data.success) {
      wfRunId.value = (data.data?.run_id as string) || '';
    } else {
      submitError.value = data.message || '工作流执行失败';
    }
  } catch (e: unknown) {
    submitCount.value++;
    const err = e as Record<string, unknown>;
    const resp = err.response as Record<string, unknown> | undefined;
    submitError.value = (resp?.data as Record<string, unknown>)?.detail as string
      || (err.message as string)
      || '请求失败';
  } finally {
    submitting.value = false;
  }
}

// ---- Page 4 state ----
const hasEvidence = ref(false);
const manualDocId = ref('');
const manualChunkId = ref('');

// Mock evidence data for readerAddressable visualization
const mockEvidence = ref<Array<{
  trace_id: string;
  document_id: string;
  chunk_id: string;
}>>([
  { trace_id: 'a1b2c3d4-e5f6-4abc-8def-012345678901', document_id: 'doc-123', chunk_id: 'chunk-1' },
  { trace_id: 'b2c3d4e5-f6a7-4bcd-9ef0-123456789012', document_id: 'doc-456', chunk_id: '' },
  { trace_id: 'c3d4e5f6-a7b8-4cde-0f01-234567890123', document_id: '', chunk_id: 'chunk-3' },
  { trace_id: 'd4e5f6a7-b8c9-4def-1023-345678901234', document_id: '', chunk_id: '' },
  { trace_id: 'e5f6a7b8-c9d0-4efa-2345-456789012345', document_id: 'doc-789', chunk_id: 'chunk-5' },
]);

hasEvidence.value = true;

// ---- Responsive ----
const viewportWidth = ref(typeof window !== 'undefined' ? window.innerWidth : 1200);
const zoomActive = ref(false);
const drawerOpen = ref(false);

const currentBreakpoint = computed(() => {
  if (viewportWidth.value < 1024) return 'mobile';
  if (viewportWidth.value < 1440) return 'tablet';
  return 'desktop';
});
const currentBreakpointLabel = computed(() => {
  switch (currentBreakpoint.value) {
    case 'mobile': return '覆盖式 Drawer';
    case 'tablet': return '悬浮 Overlay Drawer (40 字黄金行宽)';
    case 'desktop': return '常驻 Flex 侧栏 (≥ 1440px)';
    default: return '';
  }
});
const drawerSize = computed(() => {
  switch (currentBreakpoint.value) {
    case 'mobile': return 'sm';
    case 'tablet': return 'md';
    case 'desktop': return 'lg';
  }
});
const drawerModeLabel = computed(() => {
  switch (currentBreakpoint.value) {
    case 'mobile': return '覆盖式 (bottom, sm)';
    case 'tablet': return '悬浮 Overlay (right, md)';
    case 'desktop': return '常驻侧栏 (≥ 1440px, no overlay)';
    default: return '';
  }
});

function onResize() {
  viewportWidth.value = window.innerWidth;
}

function toggleZoom() {
  if (zoomActive.value) {
    (document.body.style as CSSStyleDeclaration).zoom = '';
    zoomActive.value = false;
  } else {
    (document.body.style as CSSStyleDeclaration).zoom = '200%';
    zoomActive.value = true;
    // Force breakpoint re-check after zoom
    viewportWidth.value = window.innerWidth;
  }
}

// ---- Lifecycle ----
onMounted(() => {
  init();
  readTempQuestion();
  if (tempQuestion.value) {
    draftText.value = tempQuestion.value;
  }
  window.addEventListener('resize', onResize);
  // Sync projectId from route if available
  const pid = route.query.projectId as string;
  if (pid) {
    projectIdInput.value = pid;
    readCanonicalQuestion(pid);
    workflowQuestion.value = canonicalQuestion.value || '';
  }
});

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize);
  // Restore zoom if active
  if (zoomActive.value) {
    (document.body.style as CSSStyleDeclaration).zoom = '';
  }
});
</script>

<style scoped>
.proto-page {
  min-height: 100%;
}

.proto-body {
  padding: var(--space-6) var(--space-8);
  max-width: 960px;
}

.proto-main {
  /* content flows naturally */
}

/* ---- Persistent aside at ≥ 1440px ---- */
.proto-aside {
  display: none;
}

@media (min-width: 1440px) {
  .proto-body {
    display: flex;
    gap: var(--space-6);
    max-width: none;
    padding: var(--space-6) var(--space-8);
    align-items: flex-start;
  }

  .proto-main {
    flex: 1;
    min-width: 0;
    max-width: 960px;
  }

  .proto-aside {
    display: block;
    flex: 0 0 360px;
    position: sticky;
    top: var(--space-6);
    max-height: calc(100vh - var(--space-6) * 2);
    overflow-y: auto;
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    padding: var(--space-5);
  }
}

.proto-aside-header {
  margin-bottom: var(--space-4);
  padding-bottom: var(--space-3);
  border-bottom: 1px solid var(--color-border);
}

.proto-aside-title {
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
  margin: 0;
}

.proto-section {
  margin-bottom: var(--space-10);
}

.proto-section-title {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
  margin: 0 0 var(--space-4);
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--color-border);
}

.proto-panel {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-5);
}

.proto-label {
  display: block;
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--color-text-primary);
  margin-bottom: var(--space-2);
}

.proto-textarea,
.proto-input {
  width: 100%;
  box-sizing: border-box;
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-page-bg);
  color: var(--color-text-primary);
  font-family: var(--font-sans);
  font-size: var(--text-base);
  line-height: var(--leading-normal);
  resize: vertical;
}

.proto-textarea:focus,
.proto-input:focus {
  outline: none;
  border-color: var(--color-accent);
  box-shadow: var(--focus-ring);
}

.proto-textarea:disabled,
.proto-input:disabled {
  background: var(--color-disabled-bg);
  color: var(--color-disabled-text);
  cursor: not-allowed;
}

.proto-input {
  padding: var(--space-1-5) var(--space-3);
}

.proto-char-count {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  text-align: right;
  margin-top: var(--space-1);
}

.proto-actions {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-top: var(--space-3);
  flex-wrap: wrap;
}

.proto-btn {
  padding: var(--space-2) var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  cursor: pointer;
  transition: all var(--transition-base);
  white-space: nowrap;
}

.proto-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.proto-btn--primary {
  background: var(--color-accent);
  color: var(--color-on-accent);
  border-color: var(--color-accent);
}

.proto-btn--primary:hover:not(:disabled) {
  background: var(--color-accent-hover);
}

.proto-btn--secondary {
  background: var(--color-surface);
  color: var(--color-accent);
  border-color: var(--color-accent);
}

.proto-btn--secondary:hover:not(:disabled) {
  background: var(--color-accent-alpha-08);
}

.proto-feedback {
  font-size: var(--text-sm);
  color: var(--color-success-text);
}

.proto-notice {
  display: flex;
  gap: var(--space-2);
  align-items: flex-start;
  padding: var(--space-3);
  border-radius: var(--radius-md);
  background: var(--color-hover);
  margin-top: var(--space-3);
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
}

.proto-notice p {
  margin: 0;
}

.proto-notice--warn {
  background: var(--color-warning-bg);
  color: var(--color-warning-text);
  border: 1px solid var(--color-warning);
}

.proto-notice--info {
  background: var(--color-info-bg);
  color: var(--color-info-text);
  border: 1px solid var(--color-info);
}

.proto-notice--error {
  background: var(--color-error-bg);
  color: var(--color-error-light-text);
  border: 1px solid var(--color-error-icon-bg);
}

.proto-input-row {
  display: flex;
  gap: var(--space-3);
  align-items: center;
}

.proto-input-row .proto-input {
  flex: 1;
}

.proto-migration-form {
  margin-bottom: var(--space-4);
}

.proto-migration-log {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-4);
  margin-bottom: var(--space-4);
  background: var(--color-page-bg);
}

.proto-log-title {
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
  margin: 0 0 var(--space-3);
}

.proto-step-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.proto-step {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  background: var(--color-surface);
}

.proto-step--running {
  background: var(--color-info-bg);
}

.proto-step--done {
  background: var(--color-success-bg);
}

.proto-step--failed {
  background: var(--color-error-bg);
}

.proto-step-name {
  font-weight: var(--font-medium);
  min-width: 140px;
}

.proto-step-status {
  color: var(--color-text-muted);
  min-width: 80px;
}

.proto-step-detail {
  color: var(--color-text-secondary);
  font-size: var(--text-xs);
}

.proto-link {
  color: var(--color-accent);
  text-decoration: none;
  font-weight: var(--font-medium);
}

.proto-link:hover {
  text-decoration: underline;
}

.proto-text-muted {
  color: var(--color-text-muted);
  font-size: var(--text-sm);
}

.proto-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--text-sm);
}

.proto-table th,
.proto-table td {
  padding: var(--space-2) var(--space-3);
  border-bottom: 1px solid var(--color-border);
  text-align: left;
}

.proto-table th {
  font-weight: var(--font-semibold);
  color: var(--color-text-secondary);
  background: var(--color-page-bg);
}

.proto-table td code {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  background: var(--color-page-bg);
  padding: var(--space-0-25) var(--space-1);
  border-radius: var(--radius-xs);
}

.proto-evidence-list {
  margin-top: var(--space-3);
}

.proto-manual-verify {
  margin-top: var(--space-5);
  padding-top: var(--space-4);
  border-top: 1px solid var(--color-border);
}

.proto-bp-zone {
  padding: var(--space-3);
  border-radius: var(--radius-md);
  background: var(--color-page-bg);
  border: 2px solid var(--color-border);
  font-size: var(--text-sm);
  text-align: center;
  line-height: var(--leading-normal);
}

.proto-bp-zone--active {
  border-color: var(--color-accent);
  background: var(--color-accent-light);
  font-weight: var(--font-bold);
}

.proto-bp-current {
  margin-top: var(--space-3);
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
}

.proto-hint {
  margin-top: var(--space-2);
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.proto-hint code {
  font-family: var(--font-mono);
  background: var(--color-hover);
  padding: var(--space-0-25) var(--space-1);
  border-radius: var(--radius-xs);
}

/* Breakpoint bar layout */
.proto-breakpoint-bar {
  display: flex;
  gap: var(--space-4);
}

.proto-breakpoint-bar > * {
  flex: 1;
}

@media (max-width: 768px) {
  .proto-body {
    padding: var(--space-4) var(--space-5);
  }

  .proto-breakpoint-bar {
    flex-direction: column;
  }

  .proto-actions {
    flex-direction: column;
    align-items: stretch;
  }
}

/* ---- Drawer demo styles ---- */
.proto-drawer-content h3 {
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
  margin: 0 0 var(--space-3);
}

.proto-drawer-info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-2);
}

.proto-drawer-info-item {
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-page-bg);
}

.proto-drawer-info-label {
  display: block;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  margin-bottom: var(--space-0-5);
}

.proto-drawer-info-value {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--color-text-primary);
}

.proto-golden-line {
  font-family: var(--font-sans);
  font-size: var(--text-base);
  line-height: var(--leading-normal);
  color: var(--color-text-primary);
  padding: var(--space-3);
  background: var(--color-page-bg);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-accent-alpha-12);
  margin: 0;
  white-space: nowrap;
}

.proto-golden-note {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  margin: var(--space-2) 0 0;
}

.proto-overflow-box {
  padding: var(--space-3);
  background: var(--color-page-bg);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  overflow-x: auto;
  word-break: break-all;
}

.proto-overflow-box code {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
}
</style>
