import { createApp, h } from 'vue';
import HfbButton from '../../../src/components/common/HfbButton.vue';
import '../../../src/assets/main.css';

/**
 * B3-1 HfbButton standalone accessibility fixture.
 *
 * Renders every HfbButton state variation so Playwright E2E can verify
 * keyboard activation, ARIA, focus-visible, and reduced-motion — without
 * backend or router.  Click counting is done via native DOM listeners.
 */

const App = {
  mounted() {
    // Use native DOM listeners to count clicks (independent of Vue events).
    // This also proves that native <button> Enter/Space → click works.
    const counts = { normal: 0, disabled: 0, loading: 0, 'icon-only': 0 };

    const install = (id: string, key: keyof typeof counts) => {
      const container = document.querySelector(`[data-testid="${id}"]`);
      const btn = container?.querySelector('button');
      if (btn) {
        btn.addEventListener('click', () => {
          counts[key]++;
          update();
        });
      }
    };

    const update = () => {
      const el = document.getElementById('click-output');
      if (el) el.textContent = JSON.stringify(counts);
    };

    install('btn-normal', 'normal');
    install('btn-disabled', 'disabled');
    install('btn-loading', 'loading');
    install('btn-icon-only', 'icon-only');

    // Initial render
    update();
  },

  render() {
    return h('div', { style: { padding: '24px', fontFamily: 'sans-serif' } }, [
      h('h2', 'B3-1 HfbButton Accessibility Fixture'),

      // Anchor button — first in tab order so focus-visible tests
      // can Tab from a known focusable element to btn-normal.
      // display:none removes from accessibility tree but keeps it
      // programmatically focusable; use a 1px placeholder instead
      // so all viewports (incl. Mobile) can Tab from it.
      h(
        'button',
        {
          'data-testid': 'tab-anchor',
          type: 'button',
          style: {
            width: '1px',
            height: '1px',
            padding: '0',
            margin: '0',
            border: 'none',
            background: 'transparent',
            color: 'transparent',
            overflow: 'hidden',
            position: 'absolute',
          },
          tabindex: '0',
        },
        'anchor',
      ),

      // 1. Normal button — Enter/Space must fire click
      h('div', { 'data-testid': 'btn-normal' }, [h(HfbButton, {}, () => 'Normal Button')]),

      // 2. Disabled button — Enter/Space must NOT fire click
      h('div', { 'data-testid': 'btn-disabled' }, [
        h(HfbButton, { disabled: true }, () => 'Disabled Button'),
      ]),

      // 3. Loading button — Enter/Space must NOT fire click;
      //    must expose aria-busy, disabled, spinner
      h('div', { 'data-testid': 'btn-loading' }, [
        h(HfbButton, { loading: true }, () => 'Loading Button'),
      ]),

      // 4. Icon-only — exact aria-label, no text content
      h('div', { 'data-testid': 'btn-icon-only' }, [
        h(
          HfbButton,
          { ariaLabel: 'Close dialog' },
          {
            icon: () => h('span', { class: 'icon-x' }, '✕'),
          },
        ),
      ]),

      // 5. Extra variants for DOM coverage
      h(
        'div',
        {
          'data-testid': 'btn-secondary',
          style: { display: 'inline-block', margin: '4px' },
        },
        [h(HfbButton, { variant: 'secondary' }, () => 'Secondary')],
      ),
      h(
        'div',
        {
          'data-testid': 'btn-ghost',
          style: { display: 'inline-block', margin: '4px' },
        },
        [h(HfbButton, { variant: 'ghost' }, () => 'Ghost')],
      ),
      h(
        'div',
        {
          'data-testid': 'btn-danger',
          style: { display: 'inline-block', margin: '4px' },
        },
        [h(HfbButton, { variant: 'danger' }, () => 'Danger')],
      ),

      // 6. Large block button
      h('div', { 'data-testid': 'btn-block' }, [
        h(HfbButton, { size: 'lg', block: true }, () => 'Block Button'),
      ]),

      // Click counter display — updated via native DOM listeners
      h('pre', { id: 'click-output', 'data-testid': 'click-output' }, '{}'),
    ]);
  },
};

createApp(App).mount('#app');
