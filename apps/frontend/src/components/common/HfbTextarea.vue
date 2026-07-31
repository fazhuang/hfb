<template>
  <div class="hfb-input-wrapper">
    <label v-if="label" :for="textareaId" class="hfb-input__label">
      {{ label }}
      <span v-if="required" class="hfb-input__required" aria-hidden="true">*</span>
    </label>
    <textarea
      :id="textareaId"
      :class="textareaClass"
      :value="modelValue"
      :placeholder="placeholder"
      :disabled="disabled"
      :readonly="readonly"
      :required="required"
      :rows="rows"
      :maxlength="maxlength"
      :aria-invalid="!!error"
      :aria-describedby="describedBy"
      :style="autoResize ? autoResizeStyle : undefined"
      @input="onInput"
      @focus="$emit('focus', $event)"
      @blur="$emit('blur', $event)"
    />
    <div v-if="(showCount && maxlength) || error || hint" class="hfb-input__footer">
      <p v-if="error" :id="errorId" class="hfb-input__error" role="alert">
        {{ error }}
      </p>
      <p v-else-if="hint" :id="hintId" class="hfb-input__hint">
        {{ hint }}
      </p>
      <span v-if="showCount && maxlength" class="hfb-textarea__count">
        {{ modelValue.length }} / {{ maxlength }}
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, useId, nextTick } from 'vue';

const props = withDefaults(
  defineProps<{
    modelValue: string;
    label?: string;
    placeholder?: string;
    disabled?: boolean;
    readonly?: boolean;
    error?: string;
    hint?: string;
    required?: boolean;
    rows?: number;
    maxlength?: number;
    showCount?: boolean;
    autoResize?: boolean;
  }>(),
  {
    rows: 4,
    autoResize: false,
    showCount: false,
  },
);

const emit = defineEmits<{
  'update:modelValue': [value: string];
  focus: [event: FocusEvent];
  blur: [event: FocusEvent];
}>();

const textareaRef = ref<HTMLTextAreaElement | null>(null);
const uid = useId();
const textareaId = computed(() => `hfb-textarea-${uid}`);
const errorId = computed(() => `hfb-textarea-error-${uid}`);
const hintId = computed(() => `hfb-textarea-hint-${uid}`);

const describedBy = computed(() => {
  const ids: string[] = [];
  if (props.error) ids.push(errorId.value);
  else if (props.hint) ids.push(hintId.value);
  return ids.join(' ') || undefined;
});

const textareaClass = computed(() =>
  ['hfb-input__field', 'hfb-textarea__field', props.error ? 'hfb-input__field--error' : '']
    .filter(Boolean)
    .join(' '),
);

const autoResizeStyle = computed(() => ({
  resize: 'none' as const,
  overflow: 'hidden' as const,
}));

function onInput(event: Event) {
  const target = event.target as HTMLTextAreaElement;
  emit('update:modelValue', target.value);
  if (props.autoResize) {
    nextTick(() => {
      if (textareaRef.value) {
        textareaRef.value.style.height = 'auto';
        textareaRef.value.style.height = `${textareaRef.value.scrollHeight}px`;
      }
    });
  }
}
</script>

<style scoped>
@import '../../styles/base/input.css';

.hfb-textarea__field {
  resize: vertical;
  min-height: 80px;
}

.hfb-input__footer {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--space-2);
}

.hfb-textarea__count {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  white-space: nowrap;
  flex-shrink: 0;
  margin-top: 2px;
}
</style>
