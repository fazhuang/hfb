import { createRouter, createWebHistory } from 'vue-router';
import type { RouteLocationNormalized } from 'vue-router';
import DefaultLayout from '@/layouts/DefaultLayout.vue';

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
          path: 'dashboard',
          name: 'dashboard',
          component: () => import('@/views/DashboardView.vue'),
        },
      ],
    },
  ],
});

// Auth navigation guard
router.beforeEach(async (to: RouteLocationNormalized, _from, next) => {
  // Lazily import to avoid circular dependency
  const { useAuthStore } = await import('@/stores/auth');
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

  // Guest-only pages (login, register) redirect if already authed
  if (to.meta.guest && auth.isAuthenticated) {
    next({ name: 'home' });
    return;
  }

  next();
});

export default router;
