import { createApp, h } from 'vue';
import EmptyState from '../../../src/components/common/EmptyState.vue';
import ErrorState from '../../../src/components/common/ErrorState.vue';
import LoadingState from '../../../src/components/common/LoadingState.vue';
import HfbSkeleton from '../../../src/components/common/HfbSkeleton.vue';
import HfbAlert from '../../../src/components/common/HfbAlert.vue';
import { createI18n } from 'vue-i18n';
import '../../../src/assets/main.css';

/**
 * B3-4 State Components standalone accessibility fixture.
 * Renders Empty/Error/Loading/Skeleton/Alert for Playwright E2E.
 * No backend, no router.
 */

const i18n = createI18n({
  legacy: false,
  locale: 'zh',
  messages: {
    zh: { common: { error: '错误', retry: '重试', loading: '加载中...' } },
    en: { common: { error: 'Error', retry: 'Retry', loading: 'Loading...' } },
  },
});

const App = {
  render() {
    return h('div', { style: { padding: '24px', fontFamily: 'sans-serif' } }, [
      h('h2', 'B3-4 State Components Accessibility Fixture'),

      // EmptyState
      h('div', { 'data-testid': 'empty-state-container' }, [
        h(EmptyState, { title: 'No items', description: 'Add your first item.' }),
      ]),

      // ErrorState
      h('div', { 'data-testid': 'error-state-container' }, [
        h(ErrorState, { title: 'Error', message: 'Something went wrong', retryLabel: 'Retry' }),
      ]),

      // LoadingState
      h('div', { 'data-testid': 'loading-state-container' }, [
        h(LoadingState, { message: 'Fetching data...' }),
      ]),

      // Skeleton variants
      h('div', { 'data-testid': 'skeleton-text' }, [
        h(HfbSkeleton, { variant: 'text', width: '200px' }),
      ]),
      h('div', { 'data-testid': 'skeleton-circle' }, [
        h(HfbSkeleton, { variant: 'circle', width: '40px', height: '40px' }),
      ]),
      h('div', { 'data-testid': 'skeleton-rect' }, [
        h(HfbSkeleton, { variant: 'rect', width: '300px', height: '100px' }),
      ]),

      // Alert variants
      h('div', { 'data-testid': 'alert-info' }, [
        h(HfbAlert, { variant: 'info', title: 'Information' }, () => 'This is an info alert.'),
      ]),
      h('div', { 'data-testid': 'alert-error' }, [
        h(HfbAlert, { variant: 'error', title: 'Error' }, () => 'This is an error alert.'),
      ]),
      h('div', { 'data-testid': 'alert-success' }, [
        h(HfbAlert, { variant: 'success', title: 'Success' }, () => 'Operation completed.'),
      ]),
    ]);
  },
};

const app = createApp(App);
app.use(i18n);
app.mount('#app');
