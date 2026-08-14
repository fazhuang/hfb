<template>
  <div class="about-page">
    <div class="about-header">
      <h1>{{ t('system.title') }}</h1>
      <p class="about-subtitle">{{ t('system.subtitle') }}</p>
    </div>

    <div class="about-section">
      <h2>愿景</h2>
      <p>
        以数字人文方法，深入挖掘皇甫谧《针灸甲乙经》及中医经典文献， 构建知识图谱、语义检索与 AI
        辅助研究平台。
      </p>
    </div>

    <div class="about-section">
      <h2>技术栈</h2>
      <div class="tech-grid">
        <div class="tech-card">
          <HfbIcon icon="flask-conical" :size="24" class="tech-icon" />
          <strong>FastAPI</strong>
          <span>异步 Python 后端</span>
        </div>
        <div class="tech-card">
          <HfbIcon icon="diff" :size="24" class="tech-icon" />
          <strong>Vue 3</strong>
          <span>响应式前端框架</span>
        </div>
        <div class="tech-card">
          <HfbIcon icon="inbox" :size="24" class="tech-icon" />
          <strong>PostgreSQL</strong>
          <span>关系型数据库</span>
        </div>
        <div class="tech-card">
          <HfbIcon icon="search" :size="24" class="tech-icon" />
          <strong>Elasticsearch</strong>
          <span>全文检索</span>
        </div>
        <div class="tech-card">
          <HfbIcon icon="network" :size="24" class="tech-icon" />
          <strong>Neo4j</strong>
          <span>知识图谱</span>
        </div>
        <div class="tech-card">
          <HfbIcon icon="bot" :size="24" class="tech-icon" />
          <strong>Milvus</strong>
          <span>智能文献检索</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import HfbIcon from '@/components/common/HfbIcon.vue';
const { t } = useI18n();
</script>

<style scoped>
.about-page {
  max-width: 800px;
  margin: 0 auto;
  padding: var(--space-12) 24px;
}

.about-header {
  text-align: center;
  margin-bottom: 48px;
}

.about-header h1 {
  font-size: 28px;
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0 0 var(--space-2);
}

.about-subtitle {
  color: var(--color-text-muted);
  font-size: 14px;
  margin: 0;
}

.about-section {
  margin-bottom: 40px;
}

.about-section h2 {
  font-size: 18px;
  font-weight: 600;
  color: var(--color-text-primary, var(--color-hover));
  margin: 0 0 var(--space-4);
  padding-bottom: 8px;
  border-bottom: 2px solid var(--color-accent);
}

.about-section p {
  font-size: 15px;
  line-height: 1.8;
  color: var(--color-text-secondary);
  margin: 0;
}

.tech-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: var(--space-3);
}

.tech-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-4) 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  text-align: center;
  transition: border-color var(--transition-base);

  box-shadow: var(--shadow-card-xs, 0 2px 8px rgba(0, 0, 0, 0.05));}

.tech-card:hover {
  border-color: var(--color-accent);
}

.tech-icon {
  font-size: 24px;
}

.tech-card strong {
  font-size: 14px;
  color: var(--color-text-primary, var(--color-hover));
}

.tech-card span:last-child {
  font-size: 12px;
  color: var(--color-text-muted);
}
</style>
