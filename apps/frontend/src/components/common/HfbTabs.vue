<template>
  <div class="hfb-tabs">
    <div
      :class="navClass"
      role="tablist"
      :aria-label="ariaLabel"
    >
      <button
        v-for="tab in tabs"
        :key="tab.value"
        :class="tabClass(tab)"
        :disabled="tab.disabled"
        :aria-selected="tab.value === modelValue"
        :aria-controls="`${uid}-panel-${tab.value}`"
        :role="'tab'"
        :tabindex="tab.value === modelValue ? 0 : -1"
        @click="!tab.disabled && $emit('update:modelValue', tab.value)"
        @keydown.left.prevent="focusPrev"
        @keydown.right.prevent="focusNext"
        @keydown.home.prevent="focusFirst"
        @keydown.end.prevent="focusLast"
      >
        {{ tab.label }}
        <span
          v-if="tab.badge !== undefined"
          class="hfb-tabs__badge"
          aria-hidden="true"
        >{{ tab.badge }}</span>
      </button>
    </div>
    <slot />
  </div>
</template>

<script setup lang="ts">
import { computed, useId } from 'vue';

export interface HfbTab {
  value: string;
  label: string;
  disabled?: boolean;
  badge?: string | number;
}

const props = withDefaults(defineProps<{
  modelValue: string;
  tabs: HfbTab[];
  variant?: 'underline' | 'pills' | 'buttons';
  align?: 'start' | 'center' | 'end';
  ariaLabel?: string;
}>(), {
  variant: 'underline',
  align: 'start',
});

defineEmits<{
  'update:modelValue': [value: string];
}>();

const uid = useId();

const navClass = computed(() => [
  'hfb-tabs__nav',
  `hfb-tabs__nav--${props.variant}`,
  props.align !== 'start' ? `hfb-tabs__nav--${props.align}` : '',
].filter(Boolean).join(' '));

function tabClass(tab: HfbTab) {
  return [
    'hfb-tabs__tab',
    tab.value === props.modelValue ? 'hfb-tabs__tab--active' : '',
  ].filter(Boolean).join(' ');
}

// Keyboard navigation helpers
function getTabbableTabs(): HTMLButtonElement[] {
  const container = document.getElementById(uid);
  if (!container) return [];
  return Array.from(container.querySelectorAll('.hfb-tabs__tab:not([disabled])'));
}

function focusPrev() { moveFocus(-1); }
function focusNext() { moveFocus(1); }
function focusFirst() { moveFocus('first'); }
function focusLast() { moveFocus('last'); }

function moveFocus(dir: -1 | 1 | 'first' | 'last') {
  const tabs = getTabbableTabs();
  const current = document.activeElement as HTMLButtonElement;
  const idx = tabs.indexOf(current);
  let nextIdx = 0;
  if (dir === 'first') nextIdx = 0;
  else if (dir === 'last') nextIdx = tabs.length - 1;
  else nextIdx = (idx + dir + tabs.length) % tabs.length;
  tabs[nextIdx]?.focus();
}
</script>

<style scoped>
@import '../../styles/base/tabs.css';
</style>
