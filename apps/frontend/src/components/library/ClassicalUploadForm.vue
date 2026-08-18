<template>
  <div class="upload-blocked" role="status">
    <HfbAlert variant="warning" title="古籍全文上传暂未开放">
      <p>
        需 Research Lead 完成来源准入（填写并签署
        <a href="/docs/03-data/0306_Manual_Research_Source_Admission_Checklist.md">来源准入清单</a>）后方可上传古籍 PDF。
      </p>
    </HfbAlert>
    <div class="upload-actions">
      <HfbButton type="button" variant="ghost" @click="$emit('cancel')">关闭</HfbButton>
    </div>
  </div>
</template>

<script setup lang="ts">
import HfbAlert from '@/components/common/HfbAlert.vue';
import HfbButton from '@/components/common/HfbButton.vue';

defineEmits<{ cancel: [] }>();
</script>

<style scoped>
.upload-blocked { display: grid; gap: var(--space-4); max-width: 560px; padding: var(--space-4); }
.upload-blocked p { margin: 0; color: var(--color-text-secondary); font-size: var(--text-sm); }
.upload-blocked a { color: var(--color-accent); }
.upload-actions { display: flex; gap: var(--space-2); }
</style>
