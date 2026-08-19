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

    <!-- 候选证据（Phase A0 接入）：该经文段落的待审批候选 → 证据原生发布 -->
    <section class="vc-step vc-candidate-step" aria-labelledby="vc-candidate-title">
      <div class="vc-step-heading">
        <div>
          <p class="vc-step-number">04a</p>
          <h2 id="vc-candidate-title">候选证据</h2>
        </div>
      </div>

      <div v-if="loadingCounts" class="vc-candidate-loading">正在查询候选证据…</div>

      <div v-else class="vc-candidate-rows">
        <div
          v-for="item in [comparison.source, comparison.target]"
          :key="`cand-${item.passage_id}`"
          class="vc-candidate-row"
        >
          <div class="vc-candidate-info">
            <strong>{{ item.version.name }}</strong>
            <span class="vc-candidate-count">
              {{ pendingCounts[item.passage_id] ?? 0 }} 条待审批
            </span>
          </div>
          <router-link
            :to="{ path: '/candidate-review', query: { passage_id: item.passage_id } }"
            class="vc-candidate-link"
          >
            查看 / 审批
          </router-link>
        </div>
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
import { computed, ref, watch } from 'vue';
import api from '@/api/client';
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

const pendingCounts = ref<Record<string, number>>({});
const loadingCounts = ref(false);

async function fetchPendingCount(passageId: string): Promise<number> {
  try {
    const { data } = await api.get('/api/v1/extractions', {
      params: { passage_id: passageId, status: 'pending', limit: 1 },
    });
    return (data?.total as number) ?? 0;
  } catch {
    return 0;
  }
}

watch(
  () => props.comparison,
  async (comp) => {
    if (!comp) return;
    loadingCounts.value = true;
    const counts: Record<string, number> = {};
    for (const item of [comp.source, comp.target]) {
      counts[item.passage_id] = await fetchPendingCount(item.passage_id);
    }
    pendingCounts.value = counts;
    loadingCounts.value = false;
  },
  { immediate: true },
);
</script>

<style scoped>
.vc-candidate-loading {
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  padding: var(--space-2) 0;
}

.vc-candidate-rows {
  display: grid;
  gap: var(--space-3);
}

.vc-candidate-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-3);
  box-shadow: var(--shadow-card-xs);
}

.vc-candidate-info {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.vc-candidate-count {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.vc-candidate-link {
  font-size: var(--text-sm);
  color: var(--color-accent);
  text-decoration: none;
  padding: var(--space-1-5) var(--space-3);
  border: 1px solid var(--color-accent);
  border-radius: var(--radius-md);
  flex-shrink: 0;
}

.vc-candidate-link:hover {
  background: var(--color-accent-light);
}
</style>
