import { createApp, h } from 'vue';
import HfbInput from '../../../src/components/common/HfbInput.vue';
import HfbSelect from '../../../src/components/common/HfbSelect.vue';
import '../../../src/assets/main.css';

/**
 * B3-2 Input/Select standalone accessibility fixture.
 * Renders HfbInput + HfbSelect state variations for Playwright E2E.
 * No backend, no router.
 */

const App = {
  setup() {
    return () =>
      h('div', { style: { padding: '24px', fontFamily: 'sans-serif', maxWidth: '480px' } }, [
        h('h2', 'B3-2 Input / Select Accessibility Fixture'),

        // ── Input ──
        h('div', { 'data-testid': 'input-normal' }, [
          h(HfbInput, { modelValue: '', label: 'Name', placeholder: 'Enter name' }),
        ]),

        h('div', { 'data-testid': 'input-error' }, [
          h(HfbInput, { modelValue: 'bad', label: 'Email', error: 'Invalid email' }),
        ]),

        h('div', { 'data-testid': 'input-disabled' }, [
          h(HfbInput, { modelValue: 'locked', label: 'Disabled', disabled: true }),
        ]),

        h('div', { 'data-testid': 'input-clearable' }, [
          h(HfbInput, { modelValue: 'text', label: 'Clearable', clearable: true }),
        ]),

        h('div', { 'data-testid': 'input-hint' }, [
          h(HfbInput, { modelValue: '', label: 'Hint', hint: 'Your full name' }),
        ]),

        // ── Select ──
        h('div', { 'data-testid': 'select-normal' }, [
          h(HfbSelect, {
            modelValue: null,
            options: [
              { value: 'a', label: 'Option A' },
              { value: 'b', label: 'Option B' },
              { value: 'c', label: 'Option C' },
            ],
            label: 'Choice',
            placeholder: 'Choose...',
          }),
        ]),

        h('div', { 'data-testid': 'select-error' }, [
          h(HfbSelect, {
            modelValue: null,
            options: [{ value: 'x', label: 'X' }],
            label: 'Err',
            error: 'Required',
          }),
        ]),

        h('div', { 'data-testid': 'select-disabled' }, [
          h(HfbSelect, {
            modelValue: 'a',
            options: [{ value: 'a', label: 'A' }],
            label: 'Disabled Select',
            disabled: true,
          }),
        ]),
      ]);
  },
};

createApp(App).mount('#app');
