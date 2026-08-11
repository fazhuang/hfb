<template>
  <div class="home-landing-page">
    <div class="landing-layout">
      <!-- 左侧：产品引导 + 静态学术图谱 -->
      <section class="landing-main">
        <div class="hero-header">
          <h1 class="hero-title">{{ t('system.title') }}</h1>
          <p class="hero-subtitle">{{ t('onboarding.welcomeAnonymous') }}</p>
        </div>

        <!-- 静态 SVG 图谱 -->
        <CuratedLandingGraph />

        <!-- 核心引导：研究谁、能做什么、如何进入 -->
        <div class="onboarding-guide-grid">
          <div class="guide-card">
            <div class="card-header">
              <span class="card-icon" aria-hidden="true">📜</span>
              <h3>研究谁</h3>
            </div>
            <p>
              聚焦魏晋时期著名医学家与文献学家<strong>皇甫谧（215–282）</strong>及其名著<strong>《针灸甲乙经》</strong>，汇聚多源版本与典籍方书。
            </p>
          </div>

          <div class="guide-card">
            <div class="card-header">
              <span class="card-icon" aria-hidden="true">🔬</span>
              <h3>能做什么</h3>
            </div>
            <p>
              提供出处驱动的版本异文比较、多源考据图谱拓扑、全文结构化阅读与 AI 辅助研究工作流。
            </p>
          </div>

          <div class="guide-card">
            <div class="card-header">
              <span class="card-icon" aria-hidden="true">🚀</span>
              <h3>如何进入</h3>
            </div>
            <p>
              登录或免费注册账号，建立专属研究课题，一键开启数字人文深度考据与文献研究。
            </p>
          </div>
        </div>

        <!-- Phase 2 Prototype: 匿名草稿输入 (Page 1) -->
        <div v-if="!auth.isAuthenticated" class="prototype-draft-section">
          <div class="draft-card">
            <div class="draft-header">
              <span class="draft-icon" aria-hidden="true">✏️</span>
              <h3 class="draft-title">先写下你的研究问题</h3>
              <p class="draft-subtitle">草稿临时保存，登录后自动迁移到你的研究项目</p>
            </div>
            <textarea
              v-model="draftInput"
              class="draft-textarea"
              :maxlength="DRAFT_MAX_LENGTH"
              placeholder="例如：皇甫谧《针灸甲乙经》中有关呼吸系统疾病的穴位记载有哪些？..."
              rows="3"
              :disabled="draftSaved"
            />
            <div class="draft-footer">
              <span class="draft-char-count">{{ draftInput.length }} / {{ DRAFT_MAX_LENGTH }}</span>
              <button
                class="draft-save-btn"
                :disabled="!draftInput.trim() || draftSaved"
                @click="saveDraft"
              >
                {{ draftSaved ? '已保存' : '保存草稿' }}
              </button>
            </div>
            <div v-if="draftSaved" class="draft-saved-hint">
              <span aria-hidden="true">📝</span>
              草稿已暂存。登录后自动迁移至你的研究项目。未保存，登录后重新输入。
            </div>
            <div v-if="storageFailed" class="draft-saved-hint draft-saved-hint--error" role="alert">
              <span aria-hidden="true">⚠️</span>
              未保存，登录后重新输入。浏览器存储不可用。
            </div>
          </div>
        </div>
      </section>

      <!-- 右侧：登录卡片 -->
      <aside class="landing-auth">
        <div class="auth-card">
          <h2 class="auth-title">{{ t('auth.loginTitle') }}</h2>
          <p class="auth-subtitle">{{ t('auth.loginSubtitle') }}</p>

          <LoginForm @success="handleSuccess" />

          <p class="auth-footer">
            {{ t('auth.noAccount') }}
            <router-link :to="{ name: 'register' }" class="register-link">
              {{ t('auth.register') }}
            </router-link>
          </p>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { useAuthStore } from '@/stores/auth';
import LoginForm from '@/components/auth/LoginForm.vue';
import CuratedLandingGraph from '@/components/graph/CuratedLandingGraph.vue';

const { t } = useI18n();
const router = useRouter();
const route = useRoute();
const auth = useAuthStore();

// ---- Phase 2 Prototype: anonymous draft input (Page 1) ----
const DRAFT_MAX_LENGTH = 2000;
const TEMP_KEY = 'hfb_temp_pending_question';
const draftInput = ref('');
const draftSaved = ref(false);
const storageFailed = ref(false);

function loadDraft(): void {
  try {
    const stored = sessionStorage.getItem(TEMP_KEY);
    if (stored) {
      draftInput.value = stored;
      draftSaved.value = true;
    }
  } catch {
    // sessionStorage unavailable — silent
  }
}

function saveDraft(): void {
  const trimmed = draftInput.value.trim().slice(0, DRAFT_MAX_LENGTH);
  if (!trimmed) return;
  try {
    sessionStorage.setItem(TEMP_KEY, trimmed);
    draftInput.value = trimmed;
    draftSaved.value = true;
    storageFailed.value = false;
  } catch {
    storageFailed.value = true;
  }
}

function checkAuthedRedirect(): void {
  if (auth.isAuthenticated) {
    router.replace({ name: 'research-project-list' });
  }
}

onMounted(() => {
  checkAuthedRedirect();
  loadDraft();
});

watch(
  () => auth.isAuthenticated,
  (authed) => {
    if (authed) {
      checkAuthedRedirect();
    }
  },
);

function handleSuccess(): void {
  const raw = (route.query.redirect as string) ?? '/';
  // 防 Open Redirect: 仅允许 / 开头且非 // 开头
  const redirect = raw.startsWith('/') && !raw.startsWith('//') ? raw : '/';
  if (redirect === '/') {
    router.replace({ name: 'research-project-list' });
  } else {
    router.push(redirect);
  }
}
</script>

<style scoped>
.home-landing-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--space-8) var(--space-6);
  min-height: calc(100vh - 120px);
}

.landing-layout {
  display: grid;
  grid-template-columns: 1fr 380px;
  gap: var(--space-8);
  align-items: start;
}

.landing-main {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}

.hero-header {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.hero-title {
  font-size: var(--text-3xl, 30px);
  font-weight: var(--font-bold);
  color: var(--color-text-primary);
  margin: 0;
  line-height: 1.25;
}

.hero-subtitle {
  font-size: var(--text-base);
  color: var(--color-text-secondary);
  margin: 0;
}

/* 引导卡片网格 */
.onboarding-guide-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-4);
}

.guide-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  padding: var(--space-4-5);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  transition:
    transform var(--transition-base),
    box-shadow var(--transition-base);
}

.guide-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-sm);
  border-color: var(--color-accent-alpha-15);
}

.card-header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.card-icon {
  font-size: 20px;
}

.guide-card h3 {
  margin: 0;
  font-size: var(--text-sm);
  font-weight: var(--font-bold);
  color: var(--color-text-primary);
}

.guide-card p {
  margin: 0;
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
  line-height: 1.6;
}

.guide-card strong {
  color: var(--color-accent);
}

/* 右侧登录区 */
.landing-auth {
  position: sticky;
  top: var(--space-6);
}

.auth-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-2xl);
  padding: var(--space-8) var(--space-7);
  box-shadow: var(--shadow-sm);
  display: flex;
  flex-direction: column;
  text-align: center;
}

.auth-title {
  font-size: var(--text-xl, 20px);
  font-weight: var(--font-bold);
  color: var(--color-text-primary);
  margin: 0 0 var(--space-1);
}

.auth-subtitle {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  margin: 0 0 var(--space-6);
}

.auth-footer {
  margin-top: var(--space-5);
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.register-link {
  color: var(--color-accent);
  text-decoration: none;
  font-weight: var(--font-bold);
  margin-left: var(--space-1);
}

.register-link:hover {
  text-decoration: underline;
}

/* 响应式断点适配 */
@media (max-width: 1024px) {
  .landing-layout {
    grid-template-columns: 1fr;
  }

  .landing-auth {
    position: static;
  }
}

@media (max-width: 640px) {
  .onboarding-guide-grid {
    grid-template-columns: 1fr;
  }
}

/* ---- Phase 2 Prototype: 匿名草稿输入 ---- */
.prototype-draft-section {
  margin-top: var(--space-4);
}

.draft-card {
  background: var(--color-surface);
  border: 1px solid var(--color-accent-alpha-15);
  border-radius: var(--radius-xl);
  padding: var(--space-5);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.draft-header {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.draft-icon {
  font-size: 20px;
}

.draft-title {
  margin: 0;
  font-size: var(--text-base);
  font-weight: var(--font-bold);
  color: var(--color-text-primary);
}

.draft-subtitle {
  margin: 0;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.draft-textarea {
  width: 100%;
  box-sizing: border-box;
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-page-bg);
  color: var(--color-text-primary);
  font-family: var(--font-sans);
  font-size: var(--text-base);
  line-height: var(--leading-normal);
  resize: vertical;
}

.draft-textarea:focus {
  outline: none;
  border-color: var(--color-accent);
  box-shadow: var(--focus-ring);
}

.draft-textarea:disabled {
  background: var(--color-disabled-bg);
  color: var(--color-disabled-text);
  cursor: not-allowed;
}

.draft-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
}

.draft-char-count {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.draft-save-btn {
  padding: var(--space-2) var(--space-4-5);
  border: 1px solid var(--color-accent);
  border-radius: var(--radius-md);
  background: var(--color-accent);
  color: var(--color-on-accent);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  cursor: pointer;
  transition: all var(--transition-base);
}

.draft-save-btn:hover:not(:disabled) {
  background: var(--color-accent-hover);
}

.draft-save-btn:disabled {
  background: var(--color-disabled-bg);
  border-color: var(--color-disabled-bg);
  color: var(--color-disabled-text);
  cursor: not-allowed;
}

.draft-saved-hint {
  display: flex;
  gap: var(--space-2);
  align-items: center;
  font-size: var(--text-xs);
  color: var(--color-info-text);
  background: var(--color-info-bg);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-info);
}

.draft-saved-hint--error {
  color: var(--color-error-light-text);
  background: var(--color-error-bg);
  border-color: var(--color-error-icon-bg);
}
</style>
