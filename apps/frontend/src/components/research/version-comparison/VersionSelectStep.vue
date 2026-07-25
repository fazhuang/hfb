<template>
  <section class="vc-step vc-select-step" aria-labelledby="vc-select-title">
    <div class="vc-step-heading">
      <p class="vc-step-number">02</p>
      <h2 id="vc-select-title">选择版本</h2>
    </div>

    <div class="vc-selection-slots">
      <div class="vc-selection-slot">
        <span class="vc-slot-label">源版本</span>
        <template v-if="sourcePassage">
          <strong>{{ sourcePassage.metadata.version_name }}</strong>
          <p>{{ sourcePassage.title }}</p>
          <button class="vc-text-button" @click="$emit('clearSource')">移除</button>
        </template>
        <p v-else class="vc-slot-empty">请在上方搜索结果中选择源版本</p>
      </div>

      <div class="vc-selection-slot">
        <span class="vc-slot-label">目标版本</span>
        <template v-if="targetPassage">
          <strong>{{ targetPassage.metadata.version_name }}</strong>
          <p>{{ targetPassage.title }}</p>
          <button class="vc-text-button" @click="$emit('clearTarget')">移除</button>
        </template>
        <p v-else class="vc-slot-empty">请在上方搜索结果中选择目标版本</p>
      </div>
    </div>

    <p v-if="sameVersion" class="vc-inline-warning" role="alert">
      请选择不同的版本进行比较。
    </p>

    <button
      class="button button--primary button--wide"
      :disabled="!canCompare || comparing"
      @click="$emit('compare')"
    >
      {{ comparing ? '比较中...' : '开始比较' }}
    </button>
  </section>
</template>

<script setup lang="ts">
import type { PassageSearchResult } from '@/composables/useVersionComparison';

defineProps<{
  sourcePassage: PassageSearchResult | null;
  targetPassage: PassageSearchResult | null;
  sameVersion: boolean;
  canCompare: boolean;
  comparing: boolean;
}>();

defineEmits<{
  clearSource: [];
  clearTarget: [];
  compare: [];
}>();
</script>
