<template>
  <div class="hfb-dropdown" ref="dropdownRef">
    <div
      class="hfb-dropdown__trigger"
      :aria-expanded="open"
      :aria-haspopup="'menu'"
      @click="onTriggerClick"
      @mouseenter="trigger === 'hover' ? openMenu() : undefined"
    >
      <slot />
    </div>
    <ul
      v-if="open"
      ref="menuRef"
      :class="menuClass"
      role="menu"
      @mouseleave="trigger === 'hover' ? closeMenu() : undefined"
      @keydown="onMenuKey"
    >
      <template v-for="(item, idx) in items" :key="idx">
        <li v-if="item.divider" class="hfb-dropdown__divider" role="separator" />
        <li v-else>
          <button
            type="button"
            :class="itemClass(item)"
            :disabled="item.disabled"
            :role="'menuitem'"
            :tabindex="item.disabled ? -1 : 0"
            @click="onItemClick(item)"
          >
            <span v-if="item.icon" aria-hidden="true">{{ item.icon }}</span>
            {{ item.label }}
          </button>
        </li>
      </template>
    </ul>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from 'vue';

export interface HfbDropdownItem {
  value: string;
  label: string;
  icon?: string;
  disabled?: boolean;
  danger?: boolean;
  divider?: boolean;
}

const props = withDefaults(
  defineProps<{
    items: HfbDropdownItem[];
    placement?: 'bottom-start' | 'bottom-end' | 'top-start' | 'top-end';
    trigger?: 'click' | 'hover';
    disabled?: boolean;
  }>(),
  {
    placement: 'bottom-start',
    trigger: 'click',
  },
);

const emit = defineEmits<{
  select: [value: string];
}>();

const dropdownRef = ref<HTMLElement | null>(null);
const menuRef = ref<HTMLElement | null>(null);
const open = ref(false);

const menuClass = computed(() =>
  ['hfb-dropdown__menu', `hfb-dropdown__menu--${props.placement}`].join(' '),
);

function itemClass(item: HfbDropdownItem) {
  return ['hfb-dropdown__item', item.danger ? 'hfb-dropdown__item--danger' : '']
    .filter(Boolean)
    .join(' ');
}

function onTriggerClick() {
  if (props.disabled) return;
  if (props.trigger === 'click') {
    open.value = !open.value;
  }
}

function openMenu() {
  if (props.disabled) return;
  open.value = true;
}

function closeMenu() {
  open.value = false;
}

function onItemClick(item: HfbDropdownItem) {
  if (item.disabled || item.divider) return;
  emit('select', item.value);
  closeMenu();
}

function onMenuKey(event: KeyboardEvent) {
  if (event.key === 'Escape') {
    closeMenu();
  }
}

function onClickOutside(event: MouseEvent) {
  if (dropdownRef.value && !dropdownRef.value.contains(event.target as Node)) {
    closeMenu();
  }
}

onMounted(() => document.addEventListener('click', onClickOutside, true));
onUnmounted(() => document.removeEventListener('click', onClickOutside, true));
</script>

<style scoped>
@import '../../styles/base/dropdown.css';
</style>
