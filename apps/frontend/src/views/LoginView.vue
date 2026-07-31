<template>
  <div class="login-page">
    <div class="login-layout">
      <div class="login-card">
        <h1>{{ t('auth.loginTitle') }}</h1>
        <p class="login-subtitle">{{ t('auth.loginSubtitle') }}</p>

        <form @submit.prevent="handleLogin" class="login-form">
          <div class="form-group">
            <label for="username">{{ t('auth.username') }}</label>
            <input
              id="username"
              v-model="username"
              type="text"
              autocomplete="username"
              :disabled="auth.loading"
              :placeholder="t('auth.usernamePlaceholder')"
            />
          </div>

          <div class="form-group">
            <label for="password">{{ t('auth.password') }}</label>
            <input
              id="password"
              v-model="password"
              type="password"
              autocomplete="current-password"
              :disabled="auth.loading"
              :placeholder="t('auth.passwordPlaceholder')"
            />
          </div>

          <div v-if="auth.error" class="error-message">{{ auth.error }}</div>

          <button
            type="submit"
            class="login-btn"
            :disabled="auth.loading || !username || !password"
          >
            <span v-if="auth.loading" class="spinner"></span>
            {{ auth.loading ? t('auth.loggingIn') : t('auth.login') }}
          </button>
        </form>

        <p class="register-link">
          {{ t('auth.noAccount') }}
          <router-link :to="{ name: 'register' }">{{ t('auth.register') }}</router-link>
        </p>
      </div>

      <aside class="login-value-card">
        <h3>{{ t('onboarding.loginValueTitle') }}</h3>
        <ul>
          <li>{{ t('onboarding.loginValue1') }}</li>
          <li>{{ t('onboarding.loginValue2') }}</li>
          <li>{{ t('onboarding.loginValue3') }}</li>
        </ul>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { useAuthStore } from '@/stores/auth';

const { t } = useI18n();
const router = useRouter();
const route = useRoute();
const auth = useAuthStore();

const username = ref('');
const password = ref('');

async function handleLogin(): Promise<void> {
  const ok = await auth.login(username.value.trim(), password.value);
  if (ok) {
    const raw = (route.query.redirect as string) ?? '/';
    // Prevent open redirect: only allow relative paths starting with /
    const redirect = raw.startsWith('/') && !raw.startsWith('//') ? raw : '/';
    router.push(redirect);
  }
}
</script>

<style scoped>
.login-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: calc(100vh - 120px);
  padding: var(--space-6);
}

.login-layout {
  display: flex;
  gap: var(--space-8);
  align-items: flex-start;
  max-width: 820px;
  width: 100%;
}

.login-card {
  flex: 1;
  max-width: 400px;
  padding: var(--space-10) 32px;
  background: var(--color-navbar-bg, var(--color-surface));
  border: 1px solid var(--color-border);
  border-radius: var(--radius-2xl);
  text-align: center;
}

.login-card h1 {
  font-size: 24px;
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0 0 var(--space-1);
}

.login-subtitle {
  color: var(--color-text-muted);
  font-size: 14px;
  margin: 0 0 var(--space-8);
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  text-align: left;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-1-5);
}

.form-group label {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-secondary);
}

.form-group input {
  padding: var(--space-2-5) 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  font-size: 14px;
  color: var(--color-text-primary);
  background: var(--color-page-bg);
  outline: none;
  transition: border-color var(--transition-base);
}

.form-group input:focus {
  border-color: var(--color-accent);
}

.form-group input:disabled {
  opacity: 0.6;
}

.error-message {
  padding: var(--space-2-5) 14px;
  background: var(--color-error-bg);
  color: var(--color-error-text);
  border-radius: var(--radius-lg);
  font-size: 13px;
}

.login-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: var(--space-3);
  background: var(--color-accent);
  color: white;
  border: none;
  border-radius: var(--radius-lg);
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: background var(--transition-base);
  margin-top: 8px;
}

.login-btn:hover:not(:disabled) {
  background: var(--color-accent-hover);
}

.login-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.register-link {
  margin-top: 24px;
  font-size: 13px;
  color: var(--color-text-muted);
}

.register-link a {
  color: var(--color-accent);
  text-decoration: none;
  font-weight: 600;
}

.register-link a:hover {
  text-decoration: underline;
}

/* --- Value card --- */
.login-value-card {
  flex: 0 0 260px;
  padding: var(--space-7) 24px;
  background: linear-gradient(135deg, var(--color-accent-light), var(--color-accent-light));
  border: 1px solid var(--color-accent-alpha-12);
  border-radius: var(--radius-2xl);
}

.login-value-card h3 {
  font-size: 15px;
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0 0 var(--space-3-5);
}

.login-value-card ul {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2-5);
}

.login-value-card li {
  font-size: 13px;
  color: var(--color-text-secondary);
  line-height: 1.5;
  padding-left: 16px;
  position: relative;
}

.login-value-card li::before {
  content: '✓';
  position: absolute;
  left: 0;
  color: var(--color-accent);
  font-weight: 700;
  font-size: 12px;
}

.spinner {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid var(--color-surface);
  border-top-color: white;
  border-radius: 50%;
  animation: spin var(--transition-spinner) var(--ease-linear) infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 768px) {
  .login-layout {
    flex-direction: column;
    align-items: stretch;
  }

  .login-value-card {
    flex: none;
    order: -1;
  }
}
</style>
