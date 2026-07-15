<template>
  <div class="about-page">
    <div class="about-header">
      <h1>{{ t('system.title') }}</h1>
      <p class="about-subtitle">{{ t('system.subtitle') }}</p>
    </div>

    <div class="about-section">
      <h2>愿景</h2>
      <p>
        以数字人文方法，深入挖掘皇甫谧《针灸甲乙经》及中医经典文献，
        构建知识图谱、语义检索与 AI 辅助研究平台。
      </p>
    </div>

    <div class="about-section">
      <h2>技术栈</h2>
      <div class="tech-grid">
        <div class="tech-card">
          <span class="tech-icon">⚡</span>
          <strong>FastAPI</strong>
          <span>异步 Python 后端</span>
        </div>
        <div class="tech-card">
          <span class="tech-icon">🟢</span>
          <strong>Vue 3</strong>
          <span>响应式前端框架</span>
        </div>
        <div class="tech-card">
          <span class="tech-icon">🐘</span>
          <strong>PostgreSQL</strong>
          <span>关系型数据库</span>
        </div>
        <div class="tech-card">
          <span class="tech-icon">🔍</span>
          <strong>Elasticsearch</strong>
          <span>全文检索</span>
        </div>
        <div class="tech-card">
          <span class="tech-icon">🧬</span>
          <strong>Neo4j</strong>
          <span>知识图谱</span>
        </div>
        <div class="tech-card">
          <span class="tech-icon">🧠</span>
          <strong>Milvus</strong>
          <span>智能文献检索</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n';
const { t } = useI18n();
</script>

<style scoped>
.about-page {
  max-width: 800px;
  margin: 0 auto;
  padding: 48px 24px;
}

.about-header {
  text-align: center;
  margin-bottom: 48px;
}

.about-header h1 {
  font-size: 28px;
  font-weight: 700;
  color: var(--color-text-primary, #1a365d);
  margin: 0 0 8px;
}

.about-subtitle {
  color: var(--color-text-muted, #718096);
  font-size: 14px;
  margin: 0;
}

.about-section {
  margin-bottom: 40px;
}

.about-section h2 {
  font-size: 18px;
  font-weight: 600;
  color: var(--color-text-primary, #2d3748);
  margin: 0 0 16px;
  padding-bottom: 8px;
  border-bottom: 2px solid var(--color-accent, #4299e1);
}

.about-section p {
  font-size: 15px;
  line-height: 1.8;
  color: var(--color-text-secondary, #4a5568);
  margin: 0;
}

.tech-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px;
}

.tech-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 16px 12px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 8px;
  text-align: center;
  transition: border-color 0.15s;
}

.tech-card:hover {
  border-color: var(--color-accent, #4299e1);
}

.tech-icon {
  font-size: 24px;
}

.tech-card strong {
  font-size: 14px;
  color: var(--color-text-primary, #2d3748);
}

.tech-card span:last-child {
  font-size: 12px;
  color: var(--color-text-muted, #a0aec0);
}
</style>
