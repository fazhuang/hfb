<template>
  <div v-if="comparison">
    <section class="vc-step vc-evidence-step" aria-labelledby="vc-evidence-title">
      <div class="vc-step-heading">
        <div>
          <p class="vc-step-number">04</p>
          <h2 id="vc-evidence-title">验证语料</h2>
        </div>
      </div>

      <div
        v-for="item in [comparison.source, comparison.target]"
        :key="item.passage_id"
        class="vc-evidence-row"
      >
        <div>
          <strong>{{ item.version.name }}</strong>
          <p>{{ item.version.repository || '馆藏信息缺失' }}</p>
          <small>{{ item.version.shelf_mark || '排架号缺失' }}</small>
        </div>
        <span :class="['vc-evidence-status', { complete: item.evidence_complete }]">
          {{ item.evidence_complete ? '完整' : '不完整' }}
        </span>
      </div>
    </section>

    <section class="vc-step vc-note-step" aria-labelledby="vc-note-title">
      <div class="vc-step-heading">
        <div>
          <p class="vc-step-number">05</p>
          <h2 id="vc-note-title">编写笔记</h2>
        </div>
      </div>
      <label for="vc-note-input">研究笔记</label>
      <textarea
        id="vc-note-input"
        v-model="noteModel"
        rows="7"
        placeholder="记录你的研究发现..."
      ></textarea>
      <button
        class="button button--primary"
        :disabled="!noteModel.trim() || savingNote"
        @click="$emit('saveNote')"
      >
        {{ savingNote ? '保存中...' : '保存笔记' }}
      </button>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { ComparisonState } from '@/composables/useVersionComparison';

const props = defineProps<{
  comparison: ComparisonState | null;
  noteContent: string;
  savingNote: boolean;
}>();

const emit = defineEmits<{
  'update:noteContent': [value: string];
  saveNote: [];
}>();

const noteModel = computed({
  get: () => props.noteContent,
  set: (v) => emit('update:noteContent', v),
});
</script>
