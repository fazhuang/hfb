<template>
  <section class="lib-stats-panel">
    <h3>文献统计</h3>
    <div class="lib-stats-grid">
      <div class="lib-stat">
        <span class="lib-stat-label">分块数量</span>
        <span class="lib-stat-value">{{ stats.total_chunks }}</span>
      </div>
      <div class="lib-stat">
        <span class="lib-stat-label">OCR 状态</span>
        <span class="lib-stat-value">
          <span v-if="stats.ocr_text_available" class="lib-ocr-ok">✅ 可用</span>
          <span v-else class="lib-ocr-none">⛔ 无 OCR</span>
        </span>
      </div>
      <div class="lib-stat">
        <span class="lib-stat-label">OCR 分块</span>
        <span class="lib-stat-value">{{ stats.ocr_chunks }} / {{ stats.total_chunks }}</span>
      </div>
      <div v-if="stats.avg_ocr_confidence != null" class="lib-stat">
        <span class="lib-stat-label">平均 OCR 可信度</span>
        <span class="lib-stat-value">{{ (stats.avg_ocr_confidence * 100).toFixed(1) }}%</span>
      </div>
      <div class="lib-stat">
        <span class="lib-stat-label">引文数量</span>
        <span class="lib-stat-value lib-stat-link">{{ stats.citation_count }}</span>
      </div>
      <div class="lib-stat">
        <span class="lib-stat-label">证据数量</span>
        <span class="lib-stat-value lib-stat-link">{{ stats.evidence_count }}</span>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { LibraryDocumentStats } from '@/types/library';

defineProps<{ stats: LibraryDocumentStats }>();
</script>

<style scoped>
.lib-stats-panel {
  margin-bottom: 24px;
  padding: var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  background: var(--color-navbar-bg, var(--color-surface));
}

.lib-stats-panel h3 {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 var(--space-3);
  padding-bottom: 8px;
  border-bottom: 2px solid var(--color-accent);
}

.lib-stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: var(--space-2-5);
}

.lib-stat {
  display: flex;
  flex-direction: column;
  gap: var(--space-0-5);
  padding: var(--space-2);
  border-radius: var(--radius-md);
  background: var(--color-page-bg);
}

.lib-stat-label {
  font-size: 12px;
  color: var(--color-text-muted);
}

.lib-stat-value {
  font-size: 18px;
  font-weight: 700;
  color: var(--color-text-primary);
}

.lib-stat-link {
  color: var(--color-accent);
}

.lib-ocr-ok {
  color: var(--color-success-text);
  font-size: 14px;
}

.lib-ocr-none {
  color: var(--color-text-muted);
  font-size: 14px;
}
</style>
