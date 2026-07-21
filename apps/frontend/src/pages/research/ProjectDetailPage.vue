<template>
  <div class="research-page">
    <!-- Page Header -->
    <ResearchPageHeader
      :title="pageTitle"
      :description="project?.context_notes ?? undefined"
      :breadcrumbs="[
        { label: 'Research', to: '/research' },
        { label: pageTitle },
      ]"
    >
      <template #actions>
        <!-- Continue Research -->
        <router-link
          v-if="project"
          :to="`/research/${project.id}/workspace`"
          class="pdp-action-btn pdp-action-btn--primary"
        >
          继续研究
        </router-link>

        <!-- More actions menu -->
        <div v-if="project" class="pdp-more-wrap">
          <button
            ref="moreBtnRef"
            class="pdp-action-btn pdp-action-btn--secondary"
            aria-label="更多操作"
            :aria-expanded="showMoreMenu"
            @click="showMoreMenu = !showMoreMenu"
            @keydown.escape="showMoreMenu = false"
          >
            ···
          </button>

          <div
            v-if="showMoreMenu"
            class="pdp-more-menu"
            role="menu"
            aria-label="更多操作"
            @keydown.escape="showMoreMenu = false"
          >
            <button
              class="pdp-more-item"
              role="menuitem"
              @click="onEdit"
            >
              编辑课题
            </button>
            <button
              class="pdp-more-item pdp-more-item--danger"
              role="menuitem"
              @click="onDelete"
            >
              删除课题
            </button>
          </div>
        </div>
      </template>
    </ResearchPageHeader>

    <div class="pdp-body">
      <!-- Loading -->
      <LoadingState
        v-if="loading"
        message="正在加载课题信息..."
      />

      <!-- Page-level error -->
      <ErrorState
        v-else-if="pageError"
        :title="errorTitle"
        :message="errorMessage"
        @retry="loadProject"
      />

      <!-- Not found -->
      <EmptyState
        v-else-if="notFound"
        title="课题不存在"
        description="该课题可能已被删除，或您没有访问权限。"
        icon="🔍"
      >
        <template #action>
          <router-link to="/research" class="pdp-back-link">
            返回研究课题列表
          </router-link>
        </template>
      </EmptyState>

      <!-- Content -->
      <template v-else-if="project">
        <!-- Project Overview -->
        <ProjectOverview :project="project" />

        <!-- Research Activity -->
        <ResearchActivityList :project-id="project.id" />

        <!-- Reports -->
        <ProjectReports :project-id="project.id" />

        <!-- Notes -->
        <ProjectNotes :project-id="project.id" />
      </template>
    </div>

    <!-- Edit Dialog -->
    <EditProjectDialog
      :open="editDialogOpen"
      :project-id="project?.id ?? ''"
      :current-title="project?.title ?? ''"
      :current-notes="project?.context_notes ?? ''"
      :trigger-el="moreBtnRef"
      @update:open="editDialogOpen = $event"
      @saved="onEditSaved"
    />

    <!-- Delete Dialog -->
    <DeleteProjectDialog
      :open="deleteDialogOpen"
      :project-id="project?.id ?? ''"
      :project-title="project?.title ?? ''"
      :trigger-el="moreBtnRef"
      @update:open="deleteDialogOpen = $event"
      @deleted="onDeleted"
    />
  </div>
</template>

<script setup lang="ts">
/**
 * ProjectDetailPage — 研究课题详情页
 *
 * Data sources:
 *   GET /api/v1/workspace/sessions/{id}          — single session detail
 *   PATCH /api/v1/workspace/sessions/{id}         — update (edit dialog)
 *   DELETE /api/v1/workspace/sessions/{id}        — delete (delete dialog)
 *   GET /api/v4/research/session/{id}/history     — activity list
 *   GET /api/v4/research/session/{id}/runs        — reports
 *   GET /api/v1/workspace/sessions/{id}/notes     — notes
 *
 * Route param :projectId === ResearchSession.id
 * There is no independent Project entity.
 *
 * ref: docs/20-product/2012-project-detail-migration.md
 */
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import api from '@/api/client';
import { toProjectDetail } from '@/types/research';
import type { ResearchProjectDetail } from '@/types/research';

import ResearchPageHeader from '@/components/layout/ResearchPageHeader.vue';
import LoadingState from '@/components/common/LoadingState.vue';
import EmptyState from '@/components/common/EmptyState.vue';
import ErrorState from '@/components/common/ErrorState.vue';
import ProjectOverview from '@/components/research/ProjectOverview.vue';
import ResearchActivityList from '@/components/research/ResearchActivityList.vue';
import ProjectReports from '@/components/research/ProjectReports.vue';
import ProjectNotes from '@/components/research/ProjectNotes.vue';
import EditProjectDialog from '@/components/research/EditProjectDialog.vue';
import DeleteProjectDialog from '@/components/research/DeleteProjectDialog.vue';

const route = useRoute();
const router = useRouter();

// ---- Project detail (single source of truth) ----
const project = ref<ResearchProjectDetail | null>(null);
const loading = ref(false);
const pageError = ref(false);
const errorMessage = ref('');
const notFound = ref(false);

// ---- More actions menu ----
const showMoreMenu = ref(false);
const moreBtnRef = ref<HTMLButtonElement | null>(null);
const editDialogOpen = ref(false);
const deleteDialogOpen = ref(false);

// ---- Derived ----
const pageTitle = computed(() => project.value?.title || '课题详情');

const errorTitle = computed(() => {
  if (errorMessage.value.includes('403') || errorMessage.value.includes('Forbidden')) {
    return '权限不足';
  }
  return '加载失败';
});

// ---- Request dedup ----
let reqId = 0;

// ---- Load single session ----
async function loadProject() {
  const id = String(route.params.projectId || '');
  if (!id || id === 'undefined' || id === 'null') {
    notFound.value = true;
    return;
  }

  const myReqId = ++reqId;
  loading.value = true;
  pageError.value = false;
  errorMessage.value = '';
  notFound.value = false;
  project.value = null;

  try {
    const { data } = await api.get(`/api/v1/workspace/sessions/${id}`);
    if (myReqId !== reqId) return;
    const raw = (data.data ?? data) as Record<string, unknown>;
    project.value = toProjectDetail(raw);
  } catch (e: unknown) {
    if (myReqId !== reqId) return;
    const status = (e as any)?.response?.status;
    const msg =
      (e as any)?.response?.data?.message ||
      (e as any)?.message ||
      '加载失败，请检查网络连接后重试。';
    if (status === 404) {
      notFound.value = true;
    } else {
      pageError.value = true;
      errorMessage.value = msg;
    }
  } finally {
    if (myReqId === reqId) {
      loading.value = false;
    }
  }
}

// ---- Watch route param changes ----
watch(
  () => route.params.projectId,
  () => {
    loadProject();
  },
);

// ---- Edit ----
function onEdit() {
  showMoreMenu.value = false;
  editDialogOpen.value = true;
}

async function onEditSaved() {
  // Reload project to get updated title/context_notes
  await loadProject();
}

// ---- Delete ----
function onDelete() {
  showMoreMenu.value = false;
  deleteDialogOpen.value = true;
}

function onDeleted() {
  router.push('/research');
}

// ---- Close more menu on outside click ----
function onDocumentClick(e: MouseEvent) {
  const target = e.target as HTMLElement;
  if (!target.closest('.pdp-more-wrap')) {
    showMoreMenu.value = false;
  }
}

// ---- Lifecycle ----
onMounted(() => {
  document.addEventListener('click', onDocumentClick);
  loadProject();
});

onBeforeUnmount(() => {
  reqId = -1;
  document.removeEventListener('click', onDocumentClick);
});
</script>

<style scoped>
.research-page {
  min-height: 100%;
}

.pdp-body {
  padding: var(--space-6) var(--space-8);
}

/* ---- Action buttons ---- */
.pdp-action-btn {
  display: inline-flex;
  align-items: center;
  padding: var(--btn-padding-md);
  border-radius: var(--btn-radius);
  font-size: var(--btn-font-md);
  font-weight: var(--font-semibold);
  cursor: pointer;
  text-decoration: none;
  transition: all var(--transition-base);
  white-space: nowrap;
}

.pdp-action-btn--primary {
  border: none;
  background: var(--color-accent);
  color: #fff;
}

.pdp-action-btn--primary:hover {
  background: var(--color-accent-hover);
}

.pdp-action-btn--primary:focus-visible {
  background: var(--color-accent-hover);
}

.pdp-action-btn--secondary {
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  color: var(--color-text-secondary);
  letter-spacing: 2px;
  padding: 8px 14px;
  font-size: var(--text-lg);
  line-height: 1;
}

.pdp-action-btn--secondary:hover {
  background: var(--color-hover);
}

.pdp-action-btn--secondary:focus-visible {
  background: var(--color-hover);
}

/* ---- More menu ---- */
.pdp-more-wrap {
  position: relative;
}

.pdp-more-menu {
  position: absolute;
  top: calc(100% + 4px);
  right: 0;
  min-width: 140px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  z-index: 100;
  overflow: hidden;
}

.pdp-more-item {
  display: block;
  width: 100%;
  padding: 10px var(--space-4);
  border: none;
  background: none;
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  cursor: pointer;
  text-align: left;
  transition: background var(--transition-fast);
}

.pdp-more-item:hover {
  background: var(--color-hover);
}

.pdp-more-item:focus-visible {
  background: var(--color-hover);
}

.pdp-more-item--danger {
  color: var(--color-error-text);
}

.pdp-more-item--danger:hover {
  background: var(--color-error-bg);
}

.pdp-more-item--danger:focus-visible {
  background: var(--color-error-bg);
}

/* ---- Back link ---- */
.pdp-back-link {
  display: inline-flex;
  align-items: center;
  padding: var(--btn-padding-md);
  border: 1px solid var(--color-accent);
  border-radius: var(--btn-radius);
  font-size: var(--btn-font-md);
  font-weight: var(--font-semibold);
  color: var(--color-accent);
  text-decoration: none;
  transition: all var(--transition-base);
}

.pdp-back-link:hover {
  background: var(--color-accent);
  color: #fff;
}

.pdp-back-link:focus-visible {
  background: var(--color-accent);
  color: #fff;
}

/* ---- Responsive ---- */
@media (max-width: 768px) {
  .pdp-body {
    padding: var(--space-4) var(--space-5);
  }
}
</style>
