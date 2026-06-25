<template>
  <div class="login-page">
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

        <button type="submit" class="login-btn" :disabled="auth.loading || !username || !password">
          <span v-if="auth.loading" class="spinner"></span>
          {{ auth.loading ? t('auth.loggingIn') : t('auth.login') }}
        </button>
      </form>

      <p class="register-link">
        {{ t('auth.noAccount') }}
        <router-link :to="{ name: 'register' }">{{ t('auth.register') }}</router-link>
      </p>
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
    const redirect = (route.query.redirect as string) ?? '/';
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
  padding: 24px;
}

.login-card {
  width: 100%;
  max-width: 400px;
  padding: 40px 32px;
  background: var(--color-navbar-bg, #fff);
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 12px;
  text-align: center;
}

.login-card h1 {
  font-size: 24px;
  font-weight: 700;
  color: var(--color-text-primary, #1a365d);
  margin: 0 0 4px;
}

.login-subtitle {
  color: var(--color-text-muted, #718096);
  font-size: 14px;
  margin: 0 0 32px;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
  text-align: left;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-group label {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-secondary, #4a5568);
}

.form-group input {
  padding: 10px 12px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 8px;
  font-size: 14px;
  color: var(--color-text-primary, #1a365d);
  background: var(--color-page-bg, #f7fafc);
  outline: none;
  transition: border-color 0.15s;
}

.form-group input:focus {
  border-color: var(--color-accent, #2b6cb0);
}

.form-group input:disabled {
  opacity: 0.6;
}

.error-message {
  padding: 10px 14px;
  background: var(--color-error-bg, #fff5f5);
  color: var(--color-error-text, #c53030);
  border-radius: 8px;
  font-size: 13px;
}

.login-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px;
  background: var(--color-accent, #2b6cb0);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;
  margin-top: 8px;
}

.login-btn:hover:not(:disabled) {
  background: var(--color-accent-hover, #1a4f8a);
}

.login-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.register-link {
  margin-top: 24px;
  font-size: 13px;
  color: var(--color-text-muted, #a0aec0);
}

.register-link a {
  color: var(--color-accent, #2b6cb0);
  text-decoration: none;
  font-weight: 600;
}

.register-link a:hover {
  text-decoration: underline;
}

.spinner {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
