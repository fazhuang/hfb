<template>
  <div class="hfb-select-wrapper" ref="wrapperRef">
    <label v-if="label" :for="selectLabelId" class="hfb-select__label">
      {{ label }}
      <span v-if="required" class="hfb-select__required" aria-hidden="true">*</span>
    </label>
    <div class="hfb-select__container">
      <button
        :id="selectLabelId"
        ref="triggerRef"
        type="button"
        :class="triggerClass"
        :disabled="disabled"
        :aria-expanded="open"
        :aria-invalid="!!error"
        :aria-describedby="describedBy"
        @click="toggleOpen"
        @keydown="onTriggerKey"
      >
        <span v-if="selectedOption" class="hfb-select__value">
          <slot name="option" :option="selectedOption">
            {{ selectedOption.label }}
          </slot>
        </span>
        <span v-else class="hfb-select__placeholder">{{ placeholder }}</span>
        <span class="hfb-select__controls">
          <button
            v-if="clearable && selectedOption && !disabled"
            class="hfb-select__clear"
            type="button"
            aria-label="Clear selection"
            @click.stop="clearSelection"
          >
            <HfbIcon icon="lucide:x" :size="10" />
          </button>
          <span
            :class="['hfb-select__chevron', open ? 'hfb-select__chevron--open' : '']"
            aria-hidden="true"
            ><HfbIcon icon="lucide:chevron-down" :size="14" /></span
          >
        </span>
      </button>
      <ul
        v-if="open"
        ref="menuRef"
        class="hfb-select__menu"
        role="listbox"
        :aria-label="label || 'Select option'"
        @keydown="onMenuKey"
      >
        <li
          v-for="(opt, idx) in options"
          :key="opt.value"
          :id="`${uid}-option-${idx}`"
          :class="optionClass(opt)"
          role="option"
          :aria-selected="opt.value === modelValue"
          :aria-disabled="opt.disabled"
          @click="selectOption(opt)"
          @mouseenter="highlightedIdx = idx"
        >
          {{ opt.label }}
          <HfbIcon
            v-if="opt.value === modelValue"
            icon="lucide:check"
            :size="12"
            class="hfb-select__check"
          />
        </li>
        <li v-if="options.length === 0" class="hfb-select__option hfb-select__option--disabled">
          No options
        </li>
      </ul>
    </div>
    <p v-if="error" :id="errorId" class="hfb-select__error" role="alert">{{ error }}</p>
    <p v-else-if="hint" :id="hintId" class="hfb-select__hint">{{ hint }}</p>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted, useId, nextTick } from 'vue';
import HfbIcon from './HfbIcon.vue';

export interface HfbSelectOption {
  value: string | number;
  label: string;
  disabled?: boolean;
}

const props = withDefaults(
  defineProps<{
    modelValue: string | number | null;
    options: HfbSelectOption[];
    label?: string;
    placeholder?: string;
    disabled?: boolean;
    error?: string;
    hint?: string;
    required?: boolean;
    clearable?: boolean;
  }>(),
  {
    placeholder: 'Select...',
    clearable: false,
  },
);

const emit = defineEmits<{
  'update:modelValue': [value: string | number | null];
  focus: [];
  blur: [];
  open: [];
  close: [];
}>();

const wrapperRef = ref<HTMLElement | null>(null);
const triggerRef = ref<HTMLElement | null>(null);
const menuRef = ref<HTMLElement | null>(null);
const highlightedIdx = ref(0);

const open = ref(false);
const uid = useId();
const selectLabelId = computed(() => `hfb-select-${uid}`);
const errorId = computed(() => `hfb-select-error-${uid}`);
const hintId = computed(() => `hfb-select-hint-${uid}`);

const describedBy = computed(() => {
  const ids: string[] = [];
  if (props.error) ids.push(errorId.value);
  else if (props.hint) ids.push(hintId.value);
  return ids.join(' ') || undefined;
});

const selectedOption = computed(
  () => props.options.find((o) => o.value === props.modelValue) ?? null,
);

const triggerClass = computed(() =>
  ['hfb-select__trigger', props.error ? 'hfb-select__trigger--error' : '']
    .filter(Boolean)
    .join(' '),
);

function optionClass(opt: HfbSelectOption) {
  return [
    'hfb-select__option',
    opt.value === props.modelValue ? 'hfb-select__option--selected' : '',
    opt.disabled ? 'hfb-select__option--disabled' : '',
  ]
    .filter(Boolean)
    .join(' ');
}

function toggleOpen() {
  if (props.disabled) return;
  open.value = !open.value;
  if (open.value) {
    highlightedIdx.value = props.options.findIndex((o) => o.value === props.modelValue);
    if (highlightedIdx.value < 0) highlightedIdx.value = 0;
    emit('open');
    nextTick(() => menuRef.value?.focus());
  } else {
    emit('close');
    triggerRef.value?.focus();
  }
}

function closeMenu() {
  if (!open.value) return;
  open.value = false;
  emit('close');
  triggerRef.value?.focus();
}

function selectOption(opt: HfbSelectOption) {
  if (opt.disabled) return;
  emit('update:modelValue', opt.value);
  closeMenu();
}

function clearSelection() {
  emit('update:modelValue', null);
}

function onTriggerKey(event: KeyboardEvent) {
  if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
    event.preventDefault();
    if (!open.value) toggleOpen();
  }
}

function onMenuKey(event: KeyboardEvent) {
  if (event.key === 'ArrowDown') {
    event.preventDefault();
    highlightedIdx.value = (highlightedIdx.value + 1) % props.options.length;
  } else if (event.key === 'ArrowUp') {
    event.preventDefault();
    highlightedIdx.value = (highlightedIdx.value - 1 + props.options.length) % props.options.length;
  } else if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault();
    const opt = props.options[highlightedIdx.value];
    if (opt && !opt.disabled) selectOption(opt);
  } else if (event.key === 'Escape') {
    event.preventDefault();
    closeMenu();
  }
}

function onClickOutside(event: MouseEvent) {
  if (wrapperRef.value && !wrapperRef.value.contains(event.target as Node)) {
    closeMenu();
  }
}

onMounted(() => document.addEventListener('click', onClickOutside, true));
onUnmounted(() => document.removeEventListener('click', onClickOutside, true));
</script>

<style scoped>
@import '../../styles/base/select.css';
</style>
