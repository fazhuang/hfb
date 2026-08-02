<template>
  <Teleport to="body">
    <div
      v-if="isOpen"
      class="hfb-drawer__overlay"
      @click.self="onBackdropClick"
      @keydown.escape="onEscape"
    >
      <div
        ref="focusTrap.containerRef"
        :class="drawerClass"
        role="dialog"
        aria-modal="true"
        :aria-label="title || 'Drawer'"
        tabindex="-1"
      >
        <!-- Header -->
        <div class="hfb-drawer__header">
          <slot name="header">
            <h2 class="hfb-drawer__title">{{ title }}</h2>
          </slot>
          <button
            v-if="closable"
            class="hfb-drawer__close"
            type="button"
            aria-label="Close drawer"
            @click="close"
          >
            <HfbIcon icon="x" :size="18" />
          </button>
        </div>

        <!-- Body -->
        <div class="hfb-drawer__body">
          <slot />
        </div>

        <!-- Footer -->
        <div v-if="$slots.footer" class="hfb-drawer__footer">
          <slot name="footer" />
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, ref, watch, nextTick } from 'vue';
import { useFocusTrap } from '@/composables/useFocusTrap';
import HfbIcon from './HfbIcon.vue';

const props = withDefaults(
  defineProps<{
    open: boolean;
    title?: string;
    placement?: 'left' | 'right' | 'top' | 'bottom';
    size?: 'sm' | 'md' | 'lg' | 'xl';
    closable?: boolean;
    closeOnBackdrop?: boolean;
    closeOnEscape?: boolean;
  }>(),
  {
    placement: 'right',
    size: 'md',
    closable: true,
    closeOnBackdrop: true,
    closeOnEscape: true,
  },
);

const emit = defineEmits<{
  'update:open': [value: boolean];
}>();

const focusTrap = useFocusTrap();
const isOpen = ref(props.open);

const drawerClass = computed(() =>
  ['hfb-drawer', `hfb-drawer--${props.placement}`, `hfb-drawer--${props.size}`].join(' '),
);

function close() {
  emit('update:open', false);
}

function onBackdropClick() {
  if (props.closeOnBackdrop) close();
}

function onEscape() {
  if (props.closeOnEscape) close();
}

watch(
  () => props.open,
  async (val) => {
    isOpen.value = val;
    if (val) {
      await nextTick();
      document.body.style.overflow = 'hidden';
      focusTrap.activate();
    } else {
      document.body.style.overflow = '';
      focusTrap.deactivate();
    }
  },
  { immediate: true },
);

watch(isOpen, (val) => {
  if (!val) {
    document.body.style.overflow = '';
    focusTrap.deactivate();
  }
});
</script>

<style scoped>
@import '../../styles/base/drawer.css';
</style>
