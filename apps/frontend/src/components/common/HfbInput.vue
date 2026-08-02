<template>
  <div class="hfb-input-wrapper">
    <label v-if="label" :for="inputId" class="hfb-input__label">
      {{ label }}
      <span v-if="required" class="hfb-input__required" aria-hidden="true">*</span>
    </label>
    <div :class="inputContainerClass">
      <span v-if="$slots.prefix" class="hfb-input__prefix" aria-hidden="true">
        <slot name="prefix" />
      </span>
      <input
        :id="inputId"
        ref="inputRef"
        :class="inputClass"
        :type="type"
        :value="modelValue"
        :placeholder="placeholder"
        :disabled="disabled"
        :readonly="readonly"
        :required="required"
        :aria-invalid="!!error"
        :aria-describedby="describedBy"
        @input="onInput"
        @focus="$emit('focus', $event)"
        @blur="$emit('blur', $event)"
      />
      <button
        v-if="clearable && modelValue && !disabled"
        class="hfb-input__clear"
        type="button"
        aria-label="Clear input"
        @click="onClear"
      >
        <HfbIcon icon="lucide:x" :size="12" />
      </button>
      <span v-if="$slots.suffix" class="hfb-input__suffix" aria-hidden="true">
        <slot name="suffix" />
      </span>
    </div>
    <p v-if="error" :id="errorId" class="hfb-input__error" role="alert">
      {{ error }}
    </p>
    <p v-else-if="hint" :id="hintId" class="hfb-input__hint">
      {{ hint }}
    </p>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, useId, useSlots } from 'vue';
import HfbIcon from './HfbIcon.vue';

const slots = useSlots();

const props = withDefaults(
  defineProps<{
    modelValue: string;
    type?: 'text' | 'email' | 'password' | 'number' | 'url' | 'search';
    label?: string;
    placeholder?: string;
    disabled?: boolean;
    readonly?: boolean;
    error?: string;
    hint?: string;
    required?: boolean;
    size?: 'sm' | 'md' | 'lg';
    clearable?: boolean;
  }>(),
  {
    type: 'text',
    size: 'md',
    clearable: false,
  },
);

const emit = defineEmits<{
  'update:modelValue': [value: string];
  focus: [event: FocusEvent];
  blur: [event: FocusEvent];
  clear: [];
}>();

const inputRef = ref<HTMLInputElement | null>(null);
const uid = useId();
const inputId = computed(() => `hfb-input-${uid}`);
const errorId = computed(() => `hfb-input-error-${uid}`);
const hintId = computed(() => `hfb-input-hint-${uid}`);

const describedBy = computed(() => {
  const ids: string[] = [];
  if (props.error) ids.push(errorId.value);
  else if (props.hint) ids.push(hintId.value);
  return ids.join(' ') || undefined;
});

const inputContainerClass = computed(() =>
  [
    'hfb-input__container',
    slots?.prefix ? 'hfb-input__container--with-prefix' : '',
    slots?.suffix ? 'hfb-input__container--with-suffix' : '',
  ]
    .filter(Boolean)
    .join(' '),
);

const inputClass = computed(() =>
  [
    'hfb-input__field',
    props.size !== 'md' ? `hfb-input__field--${props.size}` : '',
    props.error ? 'hfb-input__field--error' : '',
  ]
    .filter(Boolean)
    .join(' '),
);

function onInput(event: Event) {
  const target = event.target as HTMLInputElement;
  emit('update:modelValue', target.value);
}

function onClear() {
  emit('update:modelValue', '');
  emit('clear');
  inputRef.value?.focus();
}
</script>

<style scoped>
@import '../../styles/base/input.css';
</style>
