import { createApp, h } from 'vue';
import { createI18n } from 'vue-i18n';
import HfbIcon from '../../../src/components/common/HfbIcon.vue';
import HfbButton from '../../../src/components/common/HfbButton.vue';
import HfbAlert from '../../../src/components/common/HfbAlert.vue';
import EmptyState from '../../../src/components/common/EmptyState.vue';
import ErrorState from '../../../src/components/common/ErrorState.vue';
import StatusCard from '../../../src/components/common/StatusCard.vue';
import '../../../src/assets/main.css';

const i18n = createI18n({
  legacy: false,
  locale: 'zh',
  messages: {
    zh: { common: { error: '错误', retry: '重试' } },
    en: { common: { error: 'Error', retry: 'Retry' } },
  },
});

/**
 * B3-5 HfbIcon standalone accessibility fixture.
 * Renders HfbIcon variations and the 5 converted components.
 * No backend, no router.
 */

const App = {
  render() {
    return h('div', { style: { padding: '24px', fontFamily: 'sans-serif', maxWidth: '600px' } }, [
      h('h2', 'B3-5 HfbIcon Accessibility Fixture'),

      // ── Raw HfbIcon variants ──
      h('div', { 'data-testid': 'icon-decorative' }, [
        h('p', 'Decorative icon (default):'),
        h(HfbIcon, { icon: 'lucide:check', size: 20 }),
      ]),

      h('div', { 'data-testid': 'icon-labeled' }, [
        h('p', 'Labeled icon:'),
        h(HfbIcon, { icon: 'lucide:info', size: 24, ariaLabel: 'Information' }),
      ]),

      h('div', { 'data-testid': 'icon-large' }, [
        h('p', 'Large icon:'),
        h(HfbIcon, { icon: 'lucide:house', size: 36 }),
      ]),

      h('div', { 'data-testid': 'icon-colored' }, [
        h('p', 'Colored icon:'),
        h(HfbIcon, { icon: 'lucide:triangle-alert', size: 20, color: '#c53030' }),
      ]),

      // ── Icon-only button (aria-label required per B3-1 §5.1) ──
      h('div', { 'data-testid': 'icon-button' }, [
        h(
          HfbButton,
          { ariaLabel: 'Close dialog' },
          { icon: () => h(HfbIcon, { icon: 'lucide:x', size: 16 }) },
        ),
      ]),

      // ── HfbAlert with SVG icons ──
      h('div', { 'data-testid': 'alert-error-svg' }, [
        h(HfbAlert, { variant: 'error', title: 'Error' }, () => 'Something went wrong.'),
      ]),
      h('div', { 'data-testid': 'alert-success-svg' }, [
        h(HfbAlert, { variant: 'success', title: 'Done' }, () => 'Completed.'),
      ]),

      // ── EmptyState with SVG icon ──
      h('div', { 'data-testid': 'empty-svg' }, [
        h(EmptyState, { title: 'No results', description: 'Nothing here.' }),
      ]),

      // ── ErrorState with SVG icon ──
      h('div', { 'data-testid': 'error-svg' }, [
        h(ErrorState, { message: 'Failed to load.', retryLabel: 'Try again' }),
      ]),

      // ── StatusCard with SVG icons ──
      h('div', { 'data-testid': 'status-connected' }, [
        h(StatusCard, { label: 'Backend Online', connected: true }),
      ]),
      h('div', { 'data-testid': 'status-disconnected' }, [
        h(StatusCard, { label: 'Redis Offline', connected: false }),
      ]),
    ]);
  },
};

const app = createApp(App);
app.use(i18n);
app.mount('#app');
