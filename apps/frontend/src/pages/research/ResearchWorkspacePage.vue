<template>
  <div class="research-page">
    <ResearchPageHeader
      :title="pageTitle"
      :description="project?.context_notes ?? undefined"
      :breadcrumbs="[
        { label: '研究课题', to: '/research' },
        { label: pageTitle, to: `/research/${projectId}` },
        { label: '研究工作区' },
      ]"
    >
      <template #actions>
        <router-link
          v-if="project"
          :to="`/research/${project.id}/workflow`"
          class="rwp-action-btn rwp-action-btn--primary"
        >
          开始新研究
        </router-link>
        <router-link
          v-if="project"
          :to="`/research/${project.id}`"
          class="rwp-action-btn rwp-action-btn--secondary"
        >
          查看课题详情
        </router-link>
      </template>
    </ResearchPageHeader>

    <div class="rwp-body">
      <!-- Page-level states -->
      <LoadingState
        v-if="pageLoading"
        message="正在加载工作区..."
      />

      <ErrorState
        v-else-if="pageError"
        :title="errorTitle"
        :message="pageErrorMessage"
        @retry="loadSession"
      />

      <EmptyState
        v-else-if="notFound"
        title="课题不存在"
        description="该课题可能已被删除，或您没有访问权限。"
        icon="🔍"
      >
        <template #action>
          <router-link to="/research" class="rwp-back-link">
            返回研究课题列表
          </router-link>
        </template>
      </EmptyState>

      <!-- Main content -->
      <template v-else-if="project">
        <main class="rwp-main">
          <!-- 1. Continue Research -->
          <ContinueResearchCard :project-id="project.id" />

          <!-- 3. Recent Activity -->
          <RecentResearchActivity :project-id="project.id" />

          <!-- 4. Recent Reports -->
          <RecentReports :project-id="project.id" />

          <!-- 5. Recent Notes -->
          <RecentNotes :project-id="project.id" />

          <!-- 6. Research Resources -->
          <ResearchResources :project-id="project.id" />
        </main>

        <!-- 7. AI Research Assistant sidebar -->
        <ResearchAssistantEntry :project-id="project.id" />
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * ResearchWorkspacePage — 研究工作台页面
 *
 * Page sections:
 *   1. ResearchPageHeader — title, context_notes, breadcrumbs, actions
 *   2. ContinueResearchCard — resumable run or "Start New Research"
 *   3. RecentResearchActivity — GET /api/v4/research/session/{id}/history
 *   4. RecentReports — GET /api/v4/research/session/{id}/runs
 *   5. RecentNotes — GET /api/v1/workspace/sessions/{id}/notes
 *   6. ResearchResources — GET /api/v1/workspace/sessions/{id}/citations
 *   7. ResearchAssistantEntry — question input → navigates to workflow
 *
 * The page owns the single ResearchSession detail (GET .../sessions/{id})
 * and passes projectId to all child components. Each child manages its
 * own loading/error/empty states independently — a block failure never
 * takes down the whole page.
 *
 * Route param :projectId === ResearchSession.id
 * There is no independent Project entity.
 *
 * ref: docs/20-product/2013-research-workspace-migration.md
 */
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue';
import { useRoute } from 'vue-router';
import api from '@/api/client';
import { toProjectDetail } from '@/types/research';
import type { ResearchProjectDetail } from '@/types/research';

import ResearchPageHeader from '@/components/layout/ResearchPageHeader.vue';
import LoadingState from '@/components/common/LoadingState.vue';
import EmptyState from '@/components/common/EmptyState.vue';
import ErrorState from '@/components/common/ErrorState.vue';
import ContinueResearchCard from '@/components/research/ContinueResearchCard.vue';
import RecentResearchActivity from '@/components/research/RecentResearchActivity.vue';
import RecentReports from '@/components/research/RecentReports.vue';
import RecentNotes from '@/components/research/RecentNotes.vue';
import ResearchResources from '@/components/research/ResearchResources.vue';
import ResearchAssistantEntry from '@/components/research/ResearchAssistantEntry.vue';

const route = useRoute();

// ---- Session detail (single source of truth) ----
const project = ref<ResearchProjectDetail | null>(null);
const pageLoading = ref(false);
const pageError = ref(false);
const pageErrorMessage = ref('');
const notFound = ref(false);

// ---- Derived ----
const projectId = computed(() => String(route.params.projectId || ''));
const pageTitle = computed(() => project.value?.title || '研究工作区');

const errorTitle = computed(() => {
  const msg = pageErrorMessage.value;
  if (msg.includes('403') || msg.includes('Forbidden')) {
    return '权限不足';
  }
  return '加载失败';
});

// ---- Request dedup ----
let reqId = 0;

// ---- Load single session ----
async function loadSession() {
  const id = String(route.params.projectId || '');
  if (!id || id === 'undefined' || id === 'null') {
    notFound.value = true;
    return;
  }

  const myReqId = ++reqId;
  pageLoading.value = true;
  pageError.value = false;
  pageErrorMessage.value = '';
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
      pageErrorMessage.value = msg;
    }
  } finally {
    if (myReqId === reqId) {
      pageLoading.value = false;
    }
  }
}

// ---- Watch route param changes ----
watch(
  () => route.params.projectId,
  () => {
    loadSession();
  },
);

// ---- Lifecycle ----
onMounted(() => {
  loadSession();
});

onBeforeUnmount(() => {
  reqId = -1;
});
</script>

<style scoped>
.research-page {
  min-height: 100%;
}

.rwp-body {
  padding: 24px 32px;
  display: flex;
  gap: 24px;
}

.rwp-main {
  flex: 1;
  min-width: 0;
}

/* ---- Sidebar (ResearchAssistantEntry wrapper) ---- */
.rwp-main + :deep(.rae-sidebar),
.rwp-body > :deep(.rae-sidebar) {
  width: 300px;
  flex-shrink: 0;
  border-left: 1px solid var(--color-border, #e2e8f0);
  padding-left: 24px;
}

/* ---- Action buttons ---- */
.rwp-action-btn {
  display: inline-flex;
  align-items: center;
  padding: 8px 20px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  text-decoration: none;
  transition: all 0.15s;
  white-space: nowrap;
}

.rwp-action-btn--primary {
  border: none;
  background: var(--color-accent, #4299e1);
  color: #fff;
}

.rwp-action-btn--primary:hover {
  background: var(--color-accent-hover, #3182ce);
}

.rwp-action-btn--secondary {
  border: 1px solid var(--color-border, #e2e8f0);
  background: var(--color-navbar-bg, #fff);
  color: var(--color-text-secondary, #4a5568);
}

.rwp-action-btn--secondary:hover {
  background: var(--color-hover, #edf2f7);
}

/* ---- Back link ---- */
.rwp-back-link {
  display: inline-flex;
  align-items: center;
  padding: 8px 20px;
  border: 1px solid var(--color-accent, #2b6cb0);
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  color: var(--color-accent, #2b6cb0);
  text-decoration: none;
  transition: all 0.15s;
}

.rwp-back-link:hover {
  background: var(--color-accent, #2b6cb0);
  color: #fff;
}

/* ---- Responsive ---- */
@media (max-width: 768px) {
  .rwp-body {
    flex-direction: column;
    padding: 16px 20px;
  }

  .rwp-main + :deep(.rae-sidebar),
  .rwp-body > :deep(.rae-sidebar) {
    width: 100%;
    border-left: none;
    border-top: 1px solid var(--color-border, #e2e8f0);
    padding-left: 0;
    padding-top: 16px;
  }
}
</style>
