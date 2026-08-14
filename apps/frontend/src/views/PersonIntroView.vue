<template>
  <div class="person-intro-view">
    <!-- 开篇 Hero 综述区块 -->
    <header class="hero-header">
      <div class="hero-badge">皇甫谧数字人文研究域</div>
      <h1 class="hero-title">皇甫谧学术人物网络与中医经典传播考据</h1>
      <p class="hero-subtitle">
        皇甫谧（215-282，字士安，号玄晏先生），魏晋时期著名医学家、史学家、文学家。其所辑撰《针灸甲乙经》十二卷，总结汉魏以前针灸学成就，确立经络腧穴规范，被尊为“中国针灸学之父”。
      </p>

      <div class="hero-stats-bar">
        <div class="stat-item">
          <span class="stat-value">215 - 282</span>
          <span class="stat-label">生卒年份 (魏晋)</span>
        </div>
        <div class="stat-item">
          <span class="stat-value">12 卷 128 篇</span>
          <span class="stat-label">《针灸甲乙经》经典定本</span>
        </div>
        <div class="stat-item">
          <span class="stat-value">N ≤ 3</span>
          <span class="stat-label">学术关联回溯深度上限</span>
        </div>
        <div class="stat-item">
          <span class="stat-value">5 大维度</span>
          <span class="stat-label">考据人物全景分类</span>
        </div>
      </div>
    </header>

    <!-- 生平与学术地位详细卡片 -->
    <section class="biography-card-section">
      <div class="bio-card">
        <div class="bio-card-header">
          <h2 class="section-heading">皇甫谧生平考据与学术地位</h2>
          <span class="bio-tag">玄晏先生考据</span>
        </div>
        <div class="bio-card-body">
          <div class="bio-text-block">
            <h3 class="bio-subheading">医学贡献与《针灸甲乙经》</h3>
            <p>
              皇甫谧身患风痹，笃志于医。他考订《黄帝内经》（包括《素问》与《九卷》）及《明堂孔穴针灸治要》，将三部中医经典分类厘订、删繁去重复，撰成中国第一部针灸学系统专著《针灸甲乙经》。书中收录 349 个腧穴，厘定归经与主治，为中医针灸学立下了千古规范。
            </p>
          </div>
          <div class="bio-text-block">
            <h3 class="bio-subheading">史学与文史巨著</h3>
            <p>
              皇甫谧不仅是医学宗师，亦为魏晋著名史学家。撰有《帝王世纪》、《高士传》、《逸士传》、《列女传》及《玄晏春秋》等，晋武帝多次征召其入朝为官，皇甫谧皆辞不就，专心著述，史称“耽玩典籍，忘寝食，时人谓之书淫”。
            </p>
          </div>
        </div>
      </div>
    </section>

    <!-- 五大研究维度卡片展台 (Interactive Category Grid) -->
    <section class="category-grid-section">
      <div class="section-header">
        <h2 class="section-heading">五大研究维度卡片展台</h2>
        <p class="section-subtext">
          点击卡片中的“探索该维度人物”，即可按考据维度筛选并浏览研究域人物名录
        </p>
      </div>

      <div class="category-grid">
        <div
          v-for="card in dimensionCards"
          :key="card.id"
          class="category-card"
        >
          <div class="card-top">
            <div class="card-icon-title">
              <HfbIcon :icon="card.icon" :size="24" class="card-icon" />
              <div>
                <h3 class="card-title">{{ card.title }}</h3>
                <span class="card-subtitle">{{ card.subtitle }}</span>
              </div>
            </div>
            <span class="card-role-badge">{{ card.badge }}</span>
          </div>

          <p class="card-description">{{ card.description }}</p>

          <div class="card-highlights">
            <span
              v-for="(item, idx) in card.highlights"
              :key="idx"
              class="highlight-tag"
            >
              {{ item }}
            </span>
          </div>

          <div class="card-action">
            <button
              class="explore-btn"
              @click="navigateToCategory(card.roleKey)"
            >
              <span>探索该维度人物</span>
              <HfbIcon icon="arrow-right" :size="14" class="arrow-icon" />
            </button>
          </div>
        </div>
      </div>
    </section>

    <!-- 学术准入与证据分级指南区块 (Domain Admission Standard) -->
    <section class="domain-standard-section">
      <div class="standard-container">
        <div class="section-header">
          <h2 class="section-heading">学术准入与证据分级指南</h2>
          <p class="section-subtext">
            皇甫谧数字人文研究域的数据收录与隔离考据标准
          </p>
        </div>

        <div class="standard-grid">
          <!-- 回溯逻辑与隔离机制 -->
          <div class="standard-block">
            <h3 class="block-title">
              <span class="block-number">01</span>
              <span>\(N \le 3\) 主锚点回溯逻辑</span>
            </h3>
            <p class="block-desc">
              人物节点入库必须存在与主锚点（皇甫谧本人或《针灸甲乙经》）关联深度不超过 3 步（\(N \le 3\)）的直接或间接学术关系链。超过 3 步或无学术实证纽带的人物将自动排除在研究域之外，确保存世文献网络的精准聚焦。
            </p>
          </div>

          <div class="standard-block">
            <h3 class="block-title">
              <span class="block-number">02</span>
              <span>考据状态三态隔离机制</span>
            </h3>
            <div class="status-triad-list">
              <div class="triad-item verified-border">
                <span class="triad-tag verified">verified 已验证</span>
                <p>经双重传世正史或权威刻本文献考验确切，入选核心学术网格。</p>
              </div>
              <div class="triad-item pending-border">
                <span class="triad-tag pending">pending 待考资料</span>
                <p>孤证、后世伪托或记载存在争议的人物史料，警示隔离并等待后续考据。</p>
              </div>
              <div class="triad-item quarantine-border">
                <span class="triad-tag quarantine">quarantine 隔离</span>
                <p>严重缺乏文献佐证或与皇甫谧无关的杂乱数据，严格隔离防污染。</p>
              </div>
            </div>
          </div>
        </div>

        <!-- A/B/C 三级古籍证据标准 -->
        <div class="evidence-grade-container">
          <h3 class="block-title">
            <span class="block-number">03</span>
            <span>A/B/C 三级古籍证据标准</span>
          </h3>

          <div class="evidence-cards-grid">
            <div
              v-for="std in evidenceStandards"
              :key="std.grade"
              class="evidence-grade-card"
            >
              <div class="grade-header">
                <span class="grade-pill" :class="std.gradeClass">{{ std.grade }} 级证据</span>
                <h4 class="grade-title">{{ std.title }}</h4>
              </div>
              <p class="grade-desc">{{ std.description }}</p>
              <div class="grade-examples">
                <span class="example-label">代表考据来源：</span>
                <div class="example-tags">
                  <span
                    v-for="(ex, idx) in std.examples"
                    :key="idx"
                    class="example-tag"
                  >
                    {{ ex }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router';
import HfbIcon from '@/components/common/HfbIcon.vue';
import type { LucideIconName } from '@/components/common/HfbIcon.vue';

export interface ResearchDimensionCard {
  id: string;
  roleKey: string;
  title: string;
  subtitle: string;
  description: string;
  icon: LucideIconName;
  badge: string;
  highlights: Array<string>;
}

export interface EvidenceStandard {
  grade: string;
  gradeClass: string;
  title: string;
  description: string;
  examples: Array<string>;
}

const router = useRouter();

const dimensionCards: Array<ResearchDimensionCard> = [
  {
    id: 'huangfu_mi_self',
    roleKey: 'huangfu_mi_self',
    title: '皇甫谧主锚点',
    subtitle: '奠基人与《针灸甲乙经》',
    description: '以皇甫谧（215-282，号玄晏先生）为核心主锚点，统摄《针灸甲乙经》十二卷考据，阐明针灸经络腧穴理论规范与经典地位。',
    icon: 'user',
    badge: '主锚点',
    highlights: ['皇甫谧本人', '《针灸甲乙经》原作者', '玄晏先生', '针灸学鼻祖'],
  },
  {
    id: 'master_predecessor',
    roleKey: 'master_predecessor',
    title: '魏晋师承与渊源',
    subtitle: '汉魏针灸脉络与家学渊源',
    description: '追溯从扁鹊、仓公（淳于意）、华佗、张仲景至魏晋名医之汉魏针灸脉络与家学渊源，揭示《甲乙经》学术思想承袭与理论源头。',
    icon: 'scroll-text',
    badge: '师承渊源',
    highlights: ['扁鹊', '仓公', '华佗', '张仲景', '汉魏名医'],
  },
  {
    id: 'friend_contemporary',
    roleKey: 'friend_contemporary',
    title: '魏晋交游与名士',
    subtitle: '与魏晋名士及朝臣的交游考据',
    description: '考证皇甫谧与魏晋名士（如嵇康、阮籍、张华）、朝臣及晋武帝司马炎等人的书信往来、玄学论辩与学术交游。',
    icon: 'users',
    badge: '魏晋交游',
    highlights: ['嵇康', '阮籍', '张华', '晋武帝司马炎', '竹林七贤'],
  },
  {
    id: 'annotator_editor',
    roleKey: 'annotator_editor',
    title: '历代注校与辑佚',
    subtitle: '北宋校正医书局及黄龙祥考证',
    description: '整理自唐宋至明清历代医家对《甲乙经》的校勘与辑佚，包含北宋校正医书局（林亿、高保衡等）权威校定及现代黄龙祥教授学术考订。',
    icon: 'pen-line',
    badge: '历代注校',
    highlights: ['林亿', '高保衡', '北宋校正医书局', '黄龙祥考证'],
  },
  {
    id: 'transmission_scholar',
    roleKey: 'transmission_scholar',
    title: '学术传播与现代研究',
    subtitle: '东亚传播史与数字人文考据',
    description: '呈现《针灸甲乙经》向日本、朝鲜半岛（如《医心方》、《东医宝鉴》引用）等东亚世界的跨国学术传播史及现代数字人文考据。',
    icon: 'network',
    badge: '学术传播',
    highlights: ['丹波康赖', '《医心方》', '《东医宝鉴》', '数字人文图谱'],
  },
];

const evidenceStandards: Array<EvidenceStandard> = [
  {
    grade: 'A',
    gradeClass: 'grade-a',
    title: '核心正史与出土文献',
    description: '最高级别学术权威，包含二十四史正史记录以及汉魏晋简帛出土医书资料。',
    examples: ['《晋书·皇甫谧传》', '《三国志》', '《隋书·经籍志》', '汉魏简帛医书'],
  },
  {
    grade: 'B',
    gradeClass: 'grade-b',
    title: '权威医籍与早期注本',
    description: '次高级别学术引用，包含宋代及以前权威医学典籍、官方校正刻本与早期传本。',
    examples: ['北宋校正医书局刻本', '《备急千金要方》', '《外台秘要》', '《医心方》'],
  },
  {
    grade: 'C',
    gradeClass: 'grade-c',
    title: '地方志、晚近野史与学者推断',
    description: '辅助考据资料，包含明清地方志、族谱记载以及现代学者合理推测，标注待考。',
    examples: ['明清县志', '皇甫氏族谱', '晚近野史笔记', '现代学术假说'],
  },
];

function navigateToCategory(roleKey: string): void {
  router.push({
    path: '/persons',
    query: { role: roleKey },
  });
}
</script>

<style scoped>
.person-intro-view {
  max-width: 1100px;
  margin: 0 auto;
  padding: var(--space-8, 32px) var(--space-6, 24px);
}

/* 1. Hero 综述样式 */
.hero-header {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl, 12px);
  padding: var(--space-8, 32px);
  margin-bottom: var(--space-6, 24px);
  box-shadow: var(--shadow-sm, 0 1px 3px rgba(0,0,0,0.05));
}

.hero-badge {
  display: inline-block;
  font-size: var(--text-xs, 12px);
  font-weight: var(--font-bold, 700);
  background: var(--color-accent-light);
  color: var(--color-accent);
  padding: var(--space-1, 4px) var(--space-3, 12px);
  border-radius: var(--radius-md, 6px);
  margin-bottom: var(--space-3, 12px);
}

.hero-title {
  font-size: var(--text-3xl, 28px);
  font-weight: var(--font-bold, 700);
  color: var(--color-text-primary);
  margin: 0 0 var(--space-3, 12px);
  line-height: 1.3;
}

.hero-subtitle {
  font-size: var(--text-base, 16px);
  color: var(--color-text-secondary);
  line-height: 1.7;
  margin: 0 0 var(--space-6, 24px);
}

.hero-stats-bar {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: var(--space-4, 16px);
  padding-top: var(--space-6, 24px);
  border-top: 1px solid var(--color-border);
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-1, 4px);
}

.stat-value {
  font-size: var(--text-xl, 20px);
  font-weight: var(--font-bold, 700);
  color: var(--color-accent);
}

.stat-label {
  font-size: var(--text-xs, 12px);
  color: var(--color-text-muted);
}

/* 2. 生平卡片样式 */
.biography-card-section {
  margin-bottom: var(--space-8, 32px);
}

.bio-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl, 12px);
  padding: var(--space-6, 24px);

  box-shadow: var(--shadow-card-xs, 0 2px 8px rgba(0, 0, 0, 0.05));}

.bio-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-4, 16px);

}

.section-heading {
  font-size: var(--text-2xl, 22px);
  font-weight: var(--font-bold, 700);
  color: var(--color-text-primary);
  margin: 0;
}

.bio-tag {
  font-size: var(--text-xs, 12px);
  padding: var(--space-1, 4px) var(--space-2-5, 10px);
  background: var(--color-hover);
  color: var(--color-text-secondary);
  border-radius: var(--radius-sm, 4px);
  border: 1px solid var(--color-border);
}

.bio-card-body {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: var(--space-5, 20px);
}

.bio-text-block {
  display: flex;
  flex-direction: column;
  gap: var(--space-2, 8px);
}

.bio-subheading {
  font-size: var(--text-base, 16px);
  font-weight: var(--font-bold, 700);
  color: var(--color-accent);
  margin: 0;
}

.bio-text-block p {
  font-size: var(--text-sm, 14px);
  color: var(--color-text-secondary);
  line-height: 1.6;
  margin: 0;
}

/* 3. 五大维度展台 Grid */
.category-grid-section {
  margin-bottom: var(--space-10, 40px);
}

.section-header {
  margin-bottom: var(--space-6, 24px);
}

.section-subtext {
  font-size: var(--text-sm, 14px);
  color: var(--color-text-muted);
  margin: var(--space-1, 4px) 0 0;
}

.category-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: var(--space-5, 20px);
}

.category-card {
  display: flex;
  flex-direction: column;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl, 12px);
  padding: var(--space-5, 20px);
  transition: all var(--transition-base, 0.2s);

  box-shadow: var(--shadow-card-xs, 0 2px 8px rgba(0, 0, 0, 0.05));}

.category-card:hover {
  border-color: var(--color-accent);
  box-shadow: var(--shadow-sm, 0 2px 8px rgba(0,0,0,0.08));
}

.card-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: var(--space-3, 12px);
}

.card-icon-title {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3, 12px);
}

.card-icon {
  font-size: var(--text-2xl, 24px);
}

.card-title {
  font-size: var(--text-lg, 18px);
  font-weight: var(--font-bold, 700);
  color: var(--color-text-primary);
  margin: 0;
}

.card-subtitle {
  font-size: var(--text-xs, 12px);
  color: var(--color-text-muted);
  display: block;
}

.card-role-badge {
  font-size: var(--text-xs, 12px);
  font-weight: var(--font-semibold, 600);
  padding: var(--space-0-5, 2px) var(--space-2, 8px);
  background: var(--color-accent-light);
  color: var(--color-accent);
  border-radius: var(--radius-sm, 4px);
  white-space: nowrap;
}

.card-description {
  font-size: var(--text-sm, 14px);
  color: var(--color-text-secondary);
  line-height: 1.6;
  margin: 0 0 var(--space-4, 16px);
  flex-grow: 1;
}

.card-highlights {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1-5, 6px);
  margin-bottom: var(--space-4, 16px);
}

.highlight-tag {
  font-size: var(--text-xs, 12px);
  padding: var(--space-0-5, 2px) var(--space-2, 8px);
  background: var(--color-tag-bg);
  color: var(--color-text-secondary);
  border-radius: var(--radius-sm, 4px);
}

.card-action {
  margin-top: auto;
}

.explore-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2, 8px);
  padding: var(--space-2-5, 10px) var(--space-4, 16px);
  background: var(--color-page-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg, 8px);
  color: var(--color-text-primary);
  font-size: var(--text-sm, 14px);
  font-weight: var(--font-semibold, 600);
  cursor: pointer;
  transition: all var(--transition-base, 0.2s);
}

.explore-btn:hover {
  background: var(--color-accent);
  color: var(--color-surface);
  border-color: var(--color-accent);
}

.arrow-icon {
  font-weight: var(--font-bold, 700);
  transition: transform var(--transition-base, 0.2s);
}

.explore-btn:hover .arrow-icon {
  transform: translateX(4px);
}

/* 4. 学术准入标准区块 */
.domain-standard-section {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl, 12px);
  padding: var(--space-8, 32px);
}

.standard-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: var(--space-6, 24px);
  margin-bottom: var(--space-8, 32px);
}

.standard-block {
  display: flex;
  flex-direction: column;
  gap: var(--space-3, 12px);
}

.block-title {
  display: flex;
  align-items: center;
  gap: var(--space-3, 12px);
  font-size: var(--text-lg, 18px);
  font-weight: var(--font-bold, 700);
  color: var(--color-text-primary);
  margin: 0;
}

.block-number {
  font-size: var(--text-xs, 12px);
  font-weight: var(--font-bold, 700);
  background: var(--color-accent);
  color: var(--color-surface);
  padding: var(--space-0-5, 2px) var(--space-2, 8px);
  border-radius: var(--radius-sm, 4px);
}

.block-desc {
  font-size: var(--text-sm, 14px);
  color: var(--color-text-secondary);
  line-height: 1.6;
  margin: 0;
}

.status-triad-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3, 12px);
}

.triad-item {
  padding: var(--space-3, 12px);
  border-radius: var(--radius-md, 6px);
  background: var(--color-page-bg);
}

.triad-item p {
  font-size: var(--text-xs, 12px);
  color: var(--color-text-secondary);
  margin: var(--space-1, 4px) 0 0;
  line-height: 1.5;
}

.verified-border {
  border-left: 3px solid var(--color-success);
}

.pending-border {
  border-left: 3px solid var(--color-warning);
}

.quarantine-border {
  border-left: 3px solid var(--color-border);
}

.triad-tag {
  font-size: var(--text-xs, 12px);
  font-weight: var(--font-semibold, 600);
  padding: var(--space-0-5, 2px) var(--space-2, 8px);
  border-radius: var(--radius-sm, 4px);
}

.triad-tag.verified {
  background: var(--color-success-bg);
  color: var(--color-success-text);
}

.triad-tag.pending {
  background: var(--color-warning-bg);
  color: var(--color-warning-text);
}

.triad-tag.quarantine {
  background: var(--color-hover);
  color: var(--color-text-muted);
}

/* Evidence Cards */
.evidence-grade-container {
  display: flex;
  flex-direction: column;
  gap: var(--space-4, 16px);
  padding-top: var(--space-6, 24px);
  border-top: 1px solid var(--color-border);
}

.evidence-cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: var(--space-4, 16px);
}

.evidence-grade-card {
  padding: var(--space-4, 16px);
  background: var(--color-page-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg, 8px);
  display: flex;
  flex-direction: column;
  gap: var(--space-2, 8px);

  box-shadow: var(--shadow-card-xs, 0 2px 8px rgba(0, 0, 0, 0.05));}

.grade-header {
  display: flex;
  align-items: center;
  gap: var(--space-2, 8px);
}

.grade-pill {
  font-size: var(--text-xs, 12px);
  font-weight: var(--font-bold, 700);
  padding: var(--space-0-5, 2px) var(--space-2, 8px);
  border-radius: var(--radius-sm, 4px);
}

.grade-title {
  font-size: var(--text-base, 15px);
  font-weight: var(--font-bold, 700);
  color: var(--color-text-primary);
  margin: 0;
}

.grade-desc {
  font-size: var(--text-xs, 12px);
  color: var(--color-text-secondary);
  line-height: 1.5;
  margin: 0;
}

.grade-examples {
  margin-top: var(--space-2, 8px);
  display: flex;
  flex-direction: column;
  gap: var(--space-1, 4px);
}

.example-label {
  font-size: var(--text-xs, 12px);
  color: var(--color-text-muted);
}

.example-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1, 4px);
}

.example-tag {
  font-size: var(--text-xs, 12px);
  padding: var(--space-0-5, 2px) var(--space-1-5, 6px);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm, 4px);
  color: var(--color-text-primary);
}
</style>
