import { createRouter, createWebHistory } from 'vue-router';
import type { RouteLocationNormalized } from 'vue-router';
import DefaultLayout from '@/layouts/DefaultLayout.vue';
import { useAuthStore } from '@/stores/auth';

const router = createRouter({
  history: createWebHistory(),
  routes: [
    // ============================================================
    // Legacy routes — all preserved, no modifications
    // ============================================================
    {
      path: '/',
      component: DefaultLayout,
      children: [
        {
          path: '',
          name: 'home',
          component: () => import('@/views/HomeView.vue'),
        },
        {
          path: 'search',
          name: 'search',
          component: () => import('@/views/SearchView.vue'),
        },
        {
          path: 'documents',
          name: 'documents',
          component: () => import('@/views/DocumentsView.vue'),
        },
        {
          path: 'about',
          name: 'about',
          component: () => import('@/views/AboutView.vue'),
        },
        {
          path: 'login',
          name: 'login',
          component: () => import('@/views/LoginView.vue'),
          meta: { guest: true },
        },
        {
          path: 'register',
          name: 'register',
          component: () => import('@/views/RegisterView.vue'),
          meta: { guest: true },
        },
        {
          path: 'books',
          name: 'books',
          component: () => import('@/views/BookListView.vue'),
        },
        {
          path: 'books/:id',
          name: 'book-detail',
          component: () => import('@/views/BookDetailView.vue'),
        },
        {
          path: 'versions/:id',
          name: 'version-detail',
          component: () => import('@/views/VersionDetailView.vue'),
        },
        {
          path: 'persons',
          name: 'persons',
          component: () => import('@/views/PersonListView.vue'),
        },
        {
          path: 'persons/intro',
          name: 'person-intro',
          component: () => import('@/views/PersonIntroView.vue'),
          meta: { title: '人物研究网络导览' },
        },
        {
          path: 'persons/:id',
          name: 'person-detail',
          component: () => import('@/views/PersonDetailView.vue'),
        },
        {
          path: 'graph',
          name: 'graph',
          component: () => import('@/views/GraphExplorerView.vue'),
        },
        {
          path: 'workspace',
          name: 'legacy-workspace-short',
          component: () => import('@/components/common/LegacyRedirect.vue'),
          meta: { requiresAuth: true },
        },
        {
          path: 'research/new',
          name: 'research-new',
          component: () => import('@/views/ResearchNewView.vue'),
          meta: { requiresAuth: true },
        },
        {
          path: 'research/home',
          name: 'research-home',
          component: () => import('@/views/ResearchHomeView.vue'),
          meta: { requiresAuth: true },
        },

        // ============================================================
        // NEW Research App Shell routes (UI Sprint 2)
        // Placed BEFORE legacy /research redirect so they take precedence.
        // All legacy routes below remain for backward compatibility.
        // ============================================================

        // Research module
        {
          path: 'research',
          component: () => import('@/layouts/ResearchAppLayout.vue'),
          meta: { section: 'research', requiresAuth: true, appShell: 'research' },
          children: [
            {
              path: '',
              name: 'research-project-list',
              component: () => import('@/pages/research/ProjectListPage.vue'),
            },
            {
              path: ':projectId',
              name: 'research-project-detail',
              component: () => import('@/pages/research/ProjectDetailPage.vue'),
            },
            {
              path: ':projectId/workspace',
              name: 'research-project-workspace',
              component: () => import('@/pages/research/ResearchWorkspacePage.vue'),
            },
            {
              path: ':projectId/workflow',
              name: 'research-project-workflow',
              component: () => import('@/pages/research/ResearchWorkflowPage.vue'),
            },
            {
              path: ':projectId/version-comparison',
              name: 'research-project-version-comparison',
              component: () => import('@/pages/research/VersionComparisonPage.vue'),
            },
            {
              path: ':projectId/result/:runId',
              name: 'research-project-result',
              component: () => import('@/pages/research/ResearchResultPage.vue'),
            },
          ],
        },

        // Library module
        {
          path: 'library',
          component: () => import('@/layouts/ResearchAppLayout.vue'),
          meta: { section: 'library', requiresAuth: true, appShell: 'research' },
          children: [
            {
              path: '',
              name: 'library-search',
              component: () => import('@/pages/library/LibrarySearchPage.vue'),
            },
            {
              path: ':id',
              name: 'library-detail',
              component: () => import('@/pages/library/LibraryDetailPage.vue'),
            },
          ],
        },

        // Reader (standalone, not under Library module — Task 009)
        {
          path: 'reader/:id',
          name: 'reader',
          component: () => import('@/pages/reader/ReaderPage.vue'),
          meta: { requiresAuth: true },
        },

        // Knowledge module
        {
          path: 'knowledge',
          component: () => import('@/layouts/ResearchAppLayout.vue'),
          meta: { section: 'knowledge', requiresAuth: true, appShell: 'research' },
          children: [
            {
              path: '',
              name: 'knowledge-explorer',
              component: () => import('@/pages/knowledge/KnowledgeExplorerPage.vue'),
            },
          ],
        },

        // Reports module (placeholder)
        {
          path: 'reports',
          component: () => import('@/layouts/ResearchAppLayout.vue'),
          meta: { section: 'reports', requiresAuth: true, appShell: 'research' },
          children: [
            {
              path: '',
              name: 'report-list',
              component: () => import('@/pages/reports/ReportListPage.vue'),
            },
          ],
        },

        // Legacy redirect — now only catches paths NOT matched by the new routes above.
        // `/research` still hits the new ProjectListPage above.
        // Individual `/research/workspace` w/o :projectId falls through to here.
        {
          path: 'research',
          name: 'legacy-research',
          component: () => import('@/components/common/LegacyRedirect.vue'),
          meta: { requiresAuth: true },
        },
        {
          path: 'research/workspace',
          name: 'legacy-workspace',
          component: () => import('@/components/common/LegacyRedirect.vue'),
          meta: { requiresAuth: true },
        },
        // /workspace → resolve most-recent session → /research/:projectId/workspace
        {
          path: 'workspace',
          name: 'legacy-workspace-short',
          component: () => import('@/components/common/LegacyRedirect.vue'),
          meta: { requiresAuth: true },
        },
        // /v4/research → resolve most-recent session → /research/:projectId/workflow
        {
          path: 'v4/research',
          name: 'legacy-v4-research',
          component: () => import('@/components/common/LegacyRedirect.vue'),
          meta: { requiresAuth: true },
        },
        // /v4 → resolve most-recent session → /research/:projectId/workflow
        {
          path: 'v4',
          name: 'legacy-v4',
          component: () => import('@/components/common/LegacyRedirect.vue'),
          meta: { requiresAuth: true },
        },
        // /v4/research-internal → resolve most-recent session → /research/:projectId/workflow
        // Legacy /v4/research-internal — redirects to canonical workflow
        {
          path: 'v4/research-internal',
          name: 'legacy-v4-research-internal',
          component: () => import('@/components/common/LegacyRedirect.vue'),
          meta: { requiresAuth: true },
        },
        {
          path: 'dashboard',
          name: 'dashboard',
          component: () => import('@/views/DashboardView.vue'),
        },
        // Literature metadata (same permission boundary as Library)
        {
          path: 'literature',
          name: 'literature',
          component: () => import('@/views/literature/LiteratureListView.vue'),
          meta: { requiresAuth: true },
        },
        {
          path: 'literature/:id',
          name: 'literature-detail',
          component: () => import('@/views/literature/LiteratureDetailView.vue'),
          meta: { requiresAuth: true },
        },
        // Classical version catalogue
        {
          path: 'classical-versions',
          name: 'classical-versions',
          component: () => import('@/views/classical-versions/ClassicalVersionListView.vue'),
          meta: { requiresAuth: true },
        },
        // Candidate extraction review queue (Phase A0) — session-owner self-review.
        // RBAC is enforced server-side (extraction.read / extraction.approve);
        // any authenticated user may reach the page, but only the session owner
        // can approve/reject a given candidate.
        {
          path: 'candidate-review',
          name: 'candidate-review',
          component: () => import('@/views/admin/CandidateReviewQueue.vue'),
          meta: { requiresAuth: true, title: '候选审核队列' },
        },
        // Source admission checklist (HFB-DAT-0306) — Research Lead + Steering
        {
          path: 'source-admission',
          name: 'source-admission',
          component: () => import('@/views/admin/SourceAdmissionPage.vue'),
          meta: { requiresAuth: true, title: '来源准入清单' },
        },
        // Admin: literature review queue
        {
          path: 'admin/literature-review',
          name: 'admin-literature-review',
          component: () => import('@/views/admin/LiteratureReviewQueue.vue'),
          meta: { requiresAuth: true, requiresAdmin: true },
        },
        // Admin: ingestion task records
        {
          path: 'admin/ingestion-tasks',
          name: 'admin-ingestion-tasks',
          component: () => import('@/views/admin/IngestionTasksView.vue'),
          meta: { requiresAuth: true, requiresAdmin: true },
        },
        // Admin: source policy (super admin only)
        {
          path: 'admin/source-policy',
          name: 'admin-source-policy',
          component: () => import('@/views/admin/SourcePolicyView.vue'),
          meta: { requiresAuth: true, requiresSuperAdmin: true },
        },
        // Admin: user & role management
        {
          path: 'admin/users',
          name: 'admin-users',
          component: () => import('@/views/admin/UserManagementView.vue'),
          meta: { requiresAuth: true, requiresAdmin: true, title: '用户与权限管理' },
        },
        // Admin: system health diagnostics
        {
          path: 'admin/system-health',
          name: 'admin-system-health',
          component: () => import('@/views/admin/SystemHealthView.vue'),
          meta: { requiresAuth: true, requiresAdmin: true, title: '系统健康诊断' },
        },
        // Phase 2 Prototype — clickable harness for the 4-page main loop
        {
          path: 'prototype',
          name: 'phase2-prototype',
          component: () => import('@/pages/prototype/Phase2PrototypePage.vue'),
          meta: { title: 'Phase 2 Prototype' },
        },
      ],
    },
  ],
});


// Auth navigation guard
router.beforeEach(async (to: RouteLocationNormalized, _from, next) => {
  const auth = useAuthStore();

  // Fetch user on first navigation if we have a token but no user
  if (auth.accessToken && !auth.user && !auth.loading) {
    await auth.fetchMe();
  }

  // Pages that require authentication
  const requiresAuth = to.matched.some((r) => r.meta.requiresAuth);

  if (requiresAuth && !auth.isAuthenticated) {
    next({ name: 'login', query: { redirect: to.fullPath } });
    return;
  }

  // Pages that require admin
  const requiresAdmin = to.matched.some((r) => r.meta.requiresAdmin);

  if (requiresAdmin && !auth.canReviewDocuments) {
    next({ name: 'home' });
    return;
  }

  // Pages that require super admin
  const requiresSuperAdmin = to.matched.some((r) => r.meta.requiresSuperAdmin);

  if (requiresSuperAdmin && !auth.canManageSourcePolicies) {
    next({ name: 'home' });
    return;
  }

  // Guest-only pages (login, register) redirect if already authed
  if (to.meta.guest && auth.isAuthenticated) {
    next({ name: 'home' });
    return;
  }

  next();
});

// ---- Document title & focus management ----
// After each navigation: set document.title from route meta, then move
// focus to the main content area so screen-reader and keyboard users
// land on the page content.
router.afterEach((to) => {
  // Document title — derived from route meta.title, falls back to brand name
  const pageTitle = (to.meta.title as string) || '';
  document.title = pageTitle ? `${pageTitle} · HFB` : '皇甫谧数字人文平台';

  // Focus management — requestAnimationFrame waits for DOM render
  requestAnimationFrame(() => {
    const main = document.querySelector<HTMLElement>('[data-main-content]');
    if (main) {
      main.focus({ preventScroll: true });
    }
  });
});

export default router;
