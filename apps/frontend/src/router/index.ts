import { createRouter, createWebHistory } from 'vue-router';
import type { RouteLocationNormalized } from 'vue-router';
import DefaultLayout from '@/layouts/DefaultLayout.vue';
import { useAuthStore } from '@/stores/auth';

const router = createRouter({
  history: createWebHistory(),
  routes: [
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
          name: 'workspace',
          component: () => import('@/views/WorkspaceView.vue'),
          meta: { requiresAuth: true },
        },
        {
          path: 'research',
          name: 'research-workflow',
          component: () => import('@/views/ResearchWorkflowView.vue'),
          meta: { requiresAuth: true },
        },
        {
          path: 'v4/research',
          name: 'v4-research',
          component: () => import('@/views/V4ResearchView.vue'),
          meta: { requiresAuth: true },
        },
        {
          path: 'v4',
          redirect: '/v4/research',
        },
        {
          path: 'dashboard',
          name: 'dashboard',
          component: () => import('@/views/DashboardView.vue'),
        },
        // Literature metadata
        {
          path: 'literature',
          name: 'literature',
          component: () => import('@/views/literature/LiteratureListView.vue'),
        },
        {
          path: 'literature/:id',
          name: 'literature-detail',
          component: () => import('@/views/literature/LiteratureDetailView.vue'),
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
