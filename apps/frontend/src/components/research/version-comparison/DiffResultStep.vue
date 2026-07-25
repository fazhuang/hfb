<template>
  <section class="vc-step vc-diff-step" aria-labelledby="vc-diff-title">
    <div class="vc-step-heading">
      <div>
        <p class="vc-step-number">03</p>
        <h2 id="vc-diff-title">比较结果</h2>
      </div>
      <div v-if="comparison" class="vc-diff-metrics">
        <span>{{ comparison.comparison.differences }} 处差异</span>
        <span>相似度 {{ formatSimilarity(comparison.comparison.similarity_ratio) }}</span>
      </div>
    </div>

    <div v-if="comparison" class="vc-passage-columns">
      <article class="vc-passage-column">
        <div class="vc-passage-heading">
          <span>源版本</span>
          <strong>{{ comparison.source.version.name }}</strong>
        </div>
        <p class="vc-passage-text">{{ comparison.source.text }}</p>
        <p class="vc-citation">{{ comparison.source.citation }}</p>
      </article>

      <article class="vc-passage-column">
        <div class="vc-passage-heading">
          <span>目标版本</span>
          <strong>{{ comparison.target.version.name }}</strong>
        </div>
        <p class="vc-passage-text">{{ comparison.target.text }}</p>
        <p class="vc-citation">{{ comparison.target.citation }}</p>
      </article>
    </div>

    <div
      v-if="comparison && comparison.comparison.operations.length"
      class="vc-diff-table-wrap"
    >
      <table class="vc-diff-table">
        <thead>
          <tr>
            <th>操作</th>
            <th>源文本</th>
            <th>目标文本</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(op, idx) in comparison.comparison.operations"
            :key="idx"
          >
            <td><span class="vc-diff-type">{{ op.op }}</span></td>
            <td>{{ op.source_text || '—' }}</td>
            <td>{{ op.target_text || '—' }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <p v-else-if="comparison" class="vc-empty-state">无差异。</p>
  </section>
</template>

<script setup lang="ts">
import type { ComparisonState } from '@/composables/useVersionComparison';

defineProps<{
  comparison: ComparisonState | null;
}>();

function formatSimilarity(value: number): string {
  return `${Math.round(value * 100)}%`;
}
</script>
