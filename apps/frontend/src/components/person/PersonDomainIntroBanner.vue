<template>
  <div class="person-domain-intro-banner">
    <div class="banner-content">
      <div class="banner-header">
        <h2 class="banner-title">皇甫谧学术人物网络</h2>
        <span class="banner-badge">数字人文考据</span>
      </div>
      <p class="banner-description">
        基于 $N \le 3$ 主锚点回溯逻辑与三级文献证据分级标准，系统收录魏晋至今与皇甫谧及《针灸甲乙经》相关的师承渊源、魏晋交游、历代注校与学术传播人物。
      </p>
      <div class="banner-actions">
        <button class="action-btn primary-btn" @click="goToIntroView">
          <HfbIcon icon="book-open" :size="16" class="btn-icon" />
          <span>人物研究网络导览 (查看专题)</span>
        </button>
        <button class="action-btn secondary-btn" @click="showStandardModal = true">
          <HfbIcon icon="info" :size="16" class="btn-icon" />
          <span>查看准入规则</span>
        </button>
      </div>
    </div>

    <!-- 学术准入与证据分级指南弹窗 -->
    <HfbDialog
      v-model:open="showStandardModal"
      title="皇甫谧研究域学术准入与证据分级标准"
      size="lg"
    >
      <div class="dialog-standard-content">
        <section class="standard-section">
          <h4 class="section-title">1. \(N \le 3\) 主锚点回溯逻辑</h4>
          <p class="section-text">
            所有纳入研究域的人物节点，必须与核心主锚点（皇甫谧本人或《针灸甲乙经》）保持在 3 步以内的关联深度（\(N \le 3\)），确保学术网络的聚焦性与严谨性。
          </p>
        </section>

        <section class="standard-section">
          <h4 class="section-title">2. 考据状态三态隔离机制</h4>
          <div class="status-isolation-grid">
            <div class="isolation-item verified-item">
              <span class="status-tag verified">verified 已验证</span>
              <p>经双重正史或权威医籍交验确凿，纳入核心研究网络。</p>
            </div>
            <div class="isolation-item pending-item">
              <span class="status-tag pending">pending 待考资料</span>
              <p>属于孤证、晚近野史或存疑记载，在视图中高亮提示待考。</p>
            </div>
            <div class="isolation-item quarantine-item">
              <span class="status-tag quarantine">quarantine 隔离</span>
              <p>完全缺乏文献考证的数据予以隔离防污染。</p>
            </div>
          </div>
        </section>

        <section class="standard-section">
          <h4 class="section-title">3. A/B/C 三级古籍证据标准</h4>
          <ul class="evidence-list">
            <li class="evidence-item">
              <strong class="grade-badge grade-a">A 级证据</strong>
              <span class="evidence-desc">正史与出土文献（如《晋书·皇甫谧传》、《三国志》及汉魏简帛医书）</span>
            </li>
            <li class="evidence-item">
              <strong class="grade-badge grade-b">B 级证据</strong>
              <span class="evidence-desc">权威医籍与早期刻本（如北宋校正医书局《针灸甲乙经》、《备急千金要方》）</span>
            </li>
            <li class="evidence-item">
              <strong class="grade-badge grade-c">C 级证据</strong>
              <span class="evidence-desc">地方志、晚近野史与学者推断（如明清地方志、家谱及现代假说，标记待考）</span>
            </li>
          </ul>
        </section>
      </div>

      <template #footer>
        <button class="dialog-close-btn" @click="showStandardModal = false">
          关闭
        </button>
      </template>
    </HfbDialog>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import HfbIcon from '@/components/common/HfbIcon.vue';
import HfbDialog from '@/components/common/HfbDialog.vue';

const router = useRouter();
const showStandardModal = ref<boolean>(false);

function goToIntroView(): void {
  router.push('/persons/intro');
}
</script>

<style scoped>
.person-domain-intro-banner {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl, 12px);
  padding: var(--space-6, 24px);
  margin-bottom: var(--space-6, 24px);
  box-shadow: var(--shadow-sm, 0 1px 3px rgba(0,0,0,0.05));
}

.banner-header {
  display: flex;
  align-items: center;
  gap: var(--space-3, 12px);
  margin-bottom: var(--space-2, 8px);
}

.banner-title {
  font-size: var(--text-2xl, 24px);
  font-weight: var(--font-bold, 700);
  color: var(--color-text-primary);
  margin: 0;
}

.banner-badge {
  font-size: var(--text-xs, 12px);
  font-weight: var(--font-semibold, 600);
  background: var(--color-accent-light);
  color: var(--color-accent);
  padding: var(--space-0-5, 2px) var(--space-2, 8px);
  border-radius: var(--radius-sm, 4px);
  border: 1px solid var(--color-accent);
}

.banner-description {
  font-size: var(--text-sm, 14px);
  color: var(--color-text-secondary);
  line-height: 1.6;
  margin: 0 0 var(--space-4, 16px);
}

.banner-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3, 12px);
}

.action-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2, 8px);
  padding: var(--space-2, 8px) var(--space-4, 16px);
  font-size: var(--text-sm, 14px);
  font-weight: var(--font-semibold, 600);
  border-radius: var(--radius-lg, 8px);
  cursor: pointer;
  transition: all var(--transition-base, 0.2s);
}

.primary-btn {
  background: var(--color-accent);
  color: var(--color-surface);
  border: 1px solid var(--color-accent);
}

.primary-btn:hover {
  background: var(--color-accent-hover);
  border-color: var(--color-accent-hover);
}

.secondary-btn {
  background: var(--color-page-bg);
  color: var(--color-text-primary);
  border: 1px solid var(--color-border);
}

.secondary-btn:hover {
  background: var(--color-hover);
  border-color: var(--color-accent);
}

.btn-icon {
  font-size: var(--text-base, 16px);
}

/* Dialog content styles */
.dialog-standard-content {
  display: flex;
  flex-direction: column;
  gap: var(--space-5, 20px);
}

.standard-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-2, 8px);
}

.section-title {
  font-size: var(--text-base, 16px);
  font-weight: var(--font-bold, 700);
  color: var(--color-text-primary);
  margin: 0;
}

.section-text {
  font-size: var(--text-sm, 14px);
  color: var(--color-text-secondary);
  line-height: 1.6;
  margin: 0;
}

.status-isolation-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: var(--space-3, 12px);
}

.isolation-item {
  padding: var(--space-3, 12px);
  border-radius: var(--radius-md, 6px);
  border: 1px solid var(--color-border);
  background: var(--color-page-bg);
}

.isolation-item p {
  font-size: var(--text-xs, 12px);
  color: var(--color-text-muted);
  margin: var(--space-2, 8px) 0 0;
  line-height: 1.4;
}

.status-tag {
  display: inline-block;
  font-size: var(--text-xs, 12px);
  font-weight: var(--font-semibold, 600);
  padding: var(--space-0-5, 2px) var(--space-2, 8px);
  border-radius: var(--radius-sm, 4px);
}

.status-tag.verified {
  background: var(--color-success-bg);
  color: var(--color-success-text);
  border: 1px solid var(--color-success);
}

.status-tag.pending {
  background: var(--color-warning-bg);
  color: var(--color-warning-text);
  border: 1px solid var(--color-warning);
}

.status-tag.quarantine {
  background: var(--color-hover);
  color: var(--color-text-muted);
  border: 1px solid var(--color-border);
}

.evidence-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2-5, 10px);
}

.evidence-item {
  display: flex;
  align-items: center;
  gap: var(--space-3, 12px);
}

.grade-badge {
  font-size: var(--text-xs, 12px);
  font-weight: var(--font-bold, 700);
  padding: var(--space-1, 4px) var(--space-2, 8px);
  border-radius: var(--radius-sm, 4px);
  white-space: nowrap;
}

.grade-a {
  background: var(--color-accent-light);
  color: var(--color-accent);
  border: 1px solid var(--color-accent);
}

.grade-b {
  background: var(--color-info-bg);
  color: var(--color-info-text);
  border: 1px solid var(--color-info);
}

.grade-c {
  background: var(--color-warning-bg);
  color: var(--color-warning-text);
  border: 1px solid var(--color-warning);
}

.evidence-desc {
  font-size: var(--text-sm, 14px);
  color: var(--color-text-secondary);
}

.dialog-close-btn {
  padding: var(--space-2, 8px) var(--space-4, 16px);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md, 6px);
  color: var(--color-text-primary);
  font-size: var(--text-sm, 14px);
  font-weight: var(--font-medium, 500);
  cursor: pointer;
  transition: all var(--transition-base, 0.2s);
}

.dialog-close-btn:hover {
  background: var(--color-hover);
}
</style>
