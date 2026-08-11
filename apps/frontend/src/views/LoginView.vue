<template>
  <div class="login-page">
    <div class="login-layout">
      <!-- 左侧：皇甫谧研究关系子图 -->
      <section class="login-graph-section">
        <CuratedLandingGraph />
      </section>

      <!-- 右侧：专业登录卡片 -->
      <aside class="login-auth-section">
        <div class="login-card">
          <h1>{{ t('auth.loginTitle') }}</h1>
          <p class="login-subtitle">{{ t('auth.loginSubtitle') }}</p>

          <LoginForm @success="handleSuccess" />

          <p class="register-link">
            {{ t('auth.noAccount') }}
            <router-link :to="{ name: 'register' }">{{ t('auth.register') }}</router-link>
          </p>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter, useRoute } from 'vue-router';
import { useI18n } from 'vue-i18n';
import LoginForm from '@/components/auth/LoginForm.vue';
import CuratedLandingGraph from '@/components/graph/CuratedLandingGraph.vue';

const { t } = useI18n();
const router = useRouter();
const route = useRoute();

function handleSuccess(): void {
  const raw = (route.query.redirect as string) ?? '/';
  // Prevent open redirect: only allow relative paths starting with /
  const redirect = raw.startsWith('/') && !raw.startsWith('//') ? raw : '/';
  router.push(redirect);
}
</script>

<style scoped>
.login-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--space-8) var(--space-6);
  min-height: calc(100vh - 120px);
  display: flex;
  align-items: center;
  justify-content: center;
}

.login-layout {
  display: grid;
  grid-template-columns: 1fr 400px;
  gap: var(--space-8);
  align-items: start;
  width: 100%;
}

.login-graph-section {
  width: 100%;
}

.login-auth-section {
  position: sticky;
  top: var(--space-6);
}

.login-card {
  padding: var(--space-8) var(--space-7);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-2xl);
  box-shadow: var(--shadow-sm);
  text-align: center;
}

.login-card h1 {
  font-size: var(--text-2xl, 24px);
  font-weight: var(--font-bold);
  color: var(--color-text-primary);
  margin: 0 0 var(--space-1);
}

.login-subtitle {
  color: var(--color-text-muted);
  font-size: var(--text-sm);
  margin: 0 0 var(--space-6);
}

.register-link {
  margin-top: var(--space-6);
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.register-link a {
  color: var(--color-accent);
  text-decoration: none;
  font-weight: var(--font-bold);
}

.register-link a:hover {
  text-decoration: underline;
}

@media (max-width: 1024px) {
  .login-layout {
    grid-template-columns: 1fr;
  }

  .login-auth-section {
    position: static;
  }
}
</style>

