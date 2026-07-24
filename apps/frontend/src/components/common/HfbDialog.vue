<template>
  <Teleport to="body">
    <div
      v-if="isOpen"
      class="hfb-dialog__overlay"
      @click.self="onBackdropClick"
      @keydown.escape="onEscape"
    >
      <div
        ref="focusTrap.containerRef"
        :class="dialogClass"
        role="dialog"
        aria-modal="true"
        :aria-labelledby="titleId"
        :aria-describedby="props.description ? descriptionId : undefined"
      >
        <!-- Header -->
        <div v-if="hasHeader" class="hfb-dialog__header">
          <div>
            <slot name="header">
              <h2 v-if="title" :id="titleId" class="hfb-dialog__title">{{ title }}</h2>
              <p v-if="description" :id="descriptionId" class="hfb-dialog__description">{{ description }}</p>
            </slot>
          </div>
          <button
            v-if="closable"
            class="hfb-dialog__close"
            type="button"
            aria-label="Close dialog"
            @click="close"
          >
            ✕
          </button>
        </div>

        <!-- Body -->
        <div class="hfb-dialog__body">
          <slot />
        </div>

        <!-- Footer -->
        <div v-if="$slots.footer" class="hfb-dialog__footer">
          <slot name="footer" />
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, watch, ref, useId, nextTick, useSlots } from 'vue';
import { useFocusTrap } from '@/composables/useFocusTrap';

const slots = useSlots();

const props = withDefaults(defineProps<{
  open: boolean;
  title?: string;
  description?: string;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  closable?: boolean;
  closeOnBackdrop?: boolean;
  closeOnEscape?: boolean;
  variant?: 'default' | 'danger' | 'info';
}>(), {
  size: 'md',
  closable: true,
  closeOnBackdrop: true,
  closeOnEscape: true,
  variant: 'default',
});

const emit = defineEmits<{
  'update:open': [value: boolean];
}>();

const focusTrap = useFocusTrap();
const isOpen = ref(props.open);

const uid = useId();
const titleId = computed(() => `hfb-dialog-title-${uid}`);
const descriptionId = computed(() => `hfb-dialog-desc-${uid}`);
const hasHeader = computed(() => !!(props.title || props.closable || slots?.header));

const dialogClass = computed(() => [
  'hfb-dialog',
  `hfb-dialog--${props.size}`,
  props.variant !== 'default' ? `hfb-dialog--${props.variant}` : '',
].filter(Boolean).join(' '));

function close() {
  emit('update:open', false);
}

function onBackdropClick() {
  if (props.closeOnBackdrop) close();
}

function onEscape() {
  if (props.closeOnEscape) close();
}

// Sync external open prop changes
watch(() => props.open, async (val) => {
  isOpen.value = val;
  if (val) {
    await nextTick();
    document.body.style.overflow = 'hidden';
    focusTrap.activate();
  } else {
    document.body.style.overflow = '';
    focusTrap.deactivate();
  }
}, { immediate: true });

// Cleanup body overflow on unmount
watch(isOpen, (val) => {
  if (!val) {
    document.body.style.overflow = '';
    focusTrap.deactivate();
  }
});
</script>

<style scoped>
@import '../../styles/base/dialog.css';
</style>
