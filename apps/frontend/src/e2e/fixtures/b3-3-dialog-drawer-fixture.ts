import { createApp, h } from 'vue';
import HfbDialog from '../../../src/components/common/HfbDialog.vue';
import HfbDrawer from '../../../src/components/common/HfbDrawer.vue';
import '../../../src/assets/main.css';

/**
 * B3-3 Dialog/Drawer standalone accessibility fixture.
 * Renders Dialog + Drawer variants for Playwright E2E.
 * No backend, no router.
 */

const App = {
  data() {
    return {
      dialogOpen: false,
      drawerOpen: false,
    };
  },
  render() {
    return h('div', { style: { padding: '24px', fontFamily: 'sans-serif' } }, [
      h('h2', 'B3-3 Dialog / Drawer Accessibility Fixture'),

      // Dialog trigger
      h(
        'button',
        {
          'data-testid': 'open-dialog-btn',
          type: 'button',
          onClick: () => {
            (this as unknown as { dialogOpen: boolean }).dialogOpen = true;
          },
        },
        'Open Dialog',
      ),

      // Dialog
      h(HfbDialog, {
        open: (this as unknown as { dialogOpen: boolean }).dialogOpen,
        title: 'Confirm Action',
        description: 'Are you sure you want to proceed?',
        'onUpdate:open': (val: boolean) => {
          (this as unknown as { dialogOpen: boolean }).dialogOpen = val;
        },
      }, () => 'This action cannot be undone. Please confirm.'),

      // Drawer trigger
      h(
        'button',
        {
          'data-testid': 'open-drawer-btn',
          type: 'button',
          onClick: () => {
            (this as unknown as { drawerOpen: boolean }).drawerOpen = true;
          },
          style: { marginLeft: '12px' },
        },
        'Open Settings',
      ),

      // Drawer
      h(HfbDrawer, {
        open: (this as unknown as { drawerOpen: boolean }).drawerOpen,
        title: 'Settings Panel',
        placement: 'right',
        'onUpdate:open': (val: boolean) => {
          (this as unknown as { drawerOpen: boolean }).drawerOpen = val;
        },
      }, () =>
        h('div', [
          h('p', 'Configure your preferences here.'),
        ]),
      ),
    ]);
  },
};

createApp(App).mount('#app');
