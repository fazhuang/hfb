import { describe, it, expect, beforeEach } from 'vitest';
import { mount } from '@vue/test-utils';
import { setActivePinia, createPinia } from 'pinia';
import { createRouter, createWebHistory } from 'vue-router';
import { createI18n } from 'vue-i18n';
import zhCN from '@/i18n/locales/zh-CN';
import { useAuthStore, type CurrentUser } from '@/stores/auth';
import ResearchPrimaryNav from '@/components/layout/ResearchPrimaryNav.vue';

const i18n = createI18n({ legacy: false, locale: 'zh-CN', messages: { 'zh-CN': zhCN } });

function makeUser(roleNames: Array<string>, isSuperuser: boolean): CurrentUser {
  return {
    id: 'u1',
    username: 'u1',
    email: 'u1@test.com',
    display_name: 'U1',
    affiliation: null,
    is_active: true,
    is_superuser: isSuperuser,
    roles: roleNames.map((name, i) => ({ id: `role-${i}`, name, description: null })),
    created_at: null,
    updated_at: null,
  };
}

function setUser(roleNames: Array<string>, isSuperuser: boolean) {
  const store = useAuthStore();
  store.user = makeUser(roleNames, isSuperuser);
  return store;
}

describe('source-admission capability matrix (auth store)', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('Platform Administrator role (non-superuser) gets nav + fill + review', () => {
    const store = setUser(['Platform Administrator'], false);
    expect(store.isPlatformAdministrator).toBe(true);
    expect(store.canReadSourceAdmissions).toBe(true); // nav entry
    expect(store.canFillSourceAdmissions).toBe(true); // fill button
    expect(store.canReviewSourceAdmissions).toBe(true); // review button
  });

  it('superuser gets full access regardless of roles', () => {
    const store = setUser([], true);
    expect(store.canReadSourceAdmissions).toBe(true);
    expect(store.canFillSourceAdmissions).toBe(true);
    expect(store.canReviewSourceAdmissions).toBe(true);
  });

  it('Researcher (non-superuser) can read but not fill or review', () => {
    const store = setUser(['Researcher'], false);
    expect(store.canReadSourceAdmissions).toBe(true);
    expect(store.canFillSourceAdmissions).toBe(false);
    expect(store.canReviewSourceAdmissions).toBe(false);
  });

  it('Steering Committee (non-superuser) can read + review but not fill', () => {
    const store = setUser(['Steering Committee'], false);
    expect(store.canReadSourceAdmissions).toBe(true);
    expect(store.canFillSourceAdmissions).toBe(false);
    expect(store.canReviewSourceAdmissions).toBe(true);
  });

  it('Student (non-superuser) has no source-admission access', () => {
    const store = setUser(['Student'], false);
    expect(store.canReadSourceAdmissions).toBe(false);
    expect(store.canFillSourceAdmissions).toBe(false);
    expect(store.canReviewSourceAdmissions).toBe(false);
  });
});

describe('source-admission nav entry (component)', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('renders the entry for a non-superuser Platform Administrator', async () => {
    setUser(['Platform Administrator'], false);

    const stub = { template: '<div />' };
    const router = createRouter({
      history: createWebHistory(),
      routes: [
        { path: '/', component: stub },
        { path: '/research', component: stub },
        { path: '/library', component: stub },
        { path: '/knowledge', component: stub },
        { path: '/reports', component: stub },
        { path: '/candidate-review', component: stub },
        { path: '/admin/literature-review', component: stub },
        { path: '/source-admission', component: stub },
      ],
    });
    await router.push('/research');
    await router.isReady();

    const wrapper = mount(ResearchPrimaryNav, {
      global: { plugins: [router, i18n] },
    });

    expect(wrapper.findAll('a[href="/source-admission"]').length).toBeGreaterThan(0);
    expect(wrapper.text()).toContain('来源准入');
  });
});
