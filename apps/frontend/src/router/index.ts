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
          redirect: '/research/workspace',
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
          meta: { section: 'research', requiresAuth: true },
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
          meta: { section: 'library', requiresAuth: true },
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

        // Knowledge module (placeholder)
        {
          path: 'knowledge',
          component: () => import('@/layouts/ResearchAppLayout.vue'),
          meta: { section: 'knowledge', requiresAuth: true },
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
          meta: { section: 'reports', requiresAuth: true },
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
          redirect: '/research/workspace?tab=research',
        },
        {
          path: 'research/workspace',
          name: 'research-workspace',
          component: () => import('@/views/ResearchWorkspaceView.vue'),
          meta: { requiresAuth: true },
        },
        {
          path: 'v4/research',
          redirect: '/research/workspace?tab=v4-research',
        },
        {
          path: 'v4',
          redirect: '/research/workspace?tab=v4-research',
        },
        // Keep V4ResearchView as an internal route (workspace renders it inline)
        {
          path: 'v4/research-internal',
          name: 'v4-research',
          component: () => import('@/views/V4ResearchView.vue'),
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

export default router;
