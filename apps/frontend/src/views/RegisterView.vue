<template>
  <div class="register-page">
    <div class="register-layout">
      <div class="register-card">
      <h1>{{ t('auth.registerTitle') }}</h1>
      <p class="register-subtitle">{{ t('auth.registerSubtitle') }}</p>

      <form @submit.prevent="handleRegister" class="register-form">
        <div class="form-group">
          <label for="username">{{ t('auth.username') }}</label>
          <input
            id="username"
            v-model="username"
            type="text"
            autocomplete="username"
            :disabled="auth.loading"
            :placeholder="t('auth.usernamePlaceholder')"
            :class="{ 'input-error': auth.validationErrors['username'] }"
          />
          <span v-if="auth.validationErrors['username']" class="field-error">{{ auth.validationErrors['username'] }}</span>
        </div>

        <div class="form-group">
          <label for="email">{{ t('auth.email') }}</label>
          <input
            id="email"
            v-model="email"
            type="email"
            autocomplete="email"
            :disabled="auth.loading"
            placeholder="email@example.com"
            :class="{ 'input-error': auth.validationErrors['email'] }"
          />
          <span v-if="auth.validationErrors['email']" class="field-error">{{ auth.validationErrors['email'] }}</span>
        </div>

        <div class="form-group">
          <label for="displayName">{{ t('auth.displayName') }}</label>
          <input
            id="displayName"
            v-model="displayName"
            type="text"
            autocomplete="name"
            :disabled="auth.loading"
            :placeholder="t('auth.displayNamePlaceholder')"
            :class="{ 'input-error': auth.validationErrors['display_name'] }"
          />
          <span v-if="auth.validationErrors['display_name']" class="field-error">{{ auth.validationErrors['display_name'] }}</span>
        </div>

        <div class="form-group">
          <label for="password">{{ t('auth.password') }}</label>
          <input
            id="password"
            v-model="password"
            type="password"
            autocomplete="new-password"
            :disabled="auth.loading"
            :placeholder="t('auth.passwordPlaceholder')"
            :class="{ 'input-error': passwordError || auth.validationErrors['password'] }"
          />
          <span v-if="passwordError" class="field-error">{{ passwordError }}</span>
          <span v-else-if="auth.validationErrors['password']" class="field-error">{{ auth.validationErrors['password'] }}</span>
        </div>

        <div v-if="auth.error" class="error-message">{{ auth.error }}</div>

        <button type="submit" class="register-btn" :disabled="auth.loading || !username || !email || !password || !!passwordError">
          <span v-if="auth.loading" class="spinner"></span>
          {{ auth.loading ? t('auth.registering') : t('auth.register') }}
        </button>
      </form>

      <p class="login-link">
        {{ t('auth.hasAccount') }}
        <router-link :to="{ name: 'login' }">{{ t('auth.login') }}</router-link>
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
import { ref, computed } from 'vue';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { useAuthStore } from '@/stores/auth';

const { t } = useI18n();
const router = useRouter();
const auth = useAuthStore();

const username = ref('');
const email = ref('');
const displayName = ref('');
const password = ref('');

// Client-side validation — catches min-length before hitting the server
const passwordError = computed(() => {
  if (!password.value) return '';
  if (password.value.length < 8) return '密码至少需要 8 个字符';
  return '';
});

async function handleRegister(): Promise<void> {
  if (passwordError.value) return;
  const ok = await auth.register(username.value.trim(), email.value.trim(), password.value, displayName.value.trim() || undefined);
  if (ok) {
    // After registration, log the user in
    const loginOk = await auth.login(username.value.trim(), password.value);
    if (loginOk) {
      router.push({ name: 'home' });
    } else {
      router.push({ name: 'login' });
    }
  }
}
</script>

<style scoped>
.register-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: calc(100vh - 120px);
  padding: 24px;
}

.register-layout {
  display: flex;
  gap: 32px;
  align-items: flex-start;
  max-width: 820px;
  width: 100%;
}

.register-card {
  flex: 1;
  max-width: 400px;
  padding: 40px 32px;
  background: var(--color-navbar-bg, #fff);
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 12px;
  text-align: center;
}

.register-card h1 {
  font-size: 24px;
  font-weight: 700;
  color: var(--color-text-primary, #1a365d);
  margin: 0 0 4px;
}

.register-subtitle {
  color: var(--color-text-muted, #718096);
  font-size: 14px;
  margin: 0 0 32px;
}

.register-form {
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

.input-error {
  border-color: var(--color-error-text, #c53030) !important;
}

.field-error {
  font-size: 12px;
  color: var(--color-error-text, #c53030);
  margin-top: 2px;
}

.error-message {
  padding: 10px 14px;
  background: var(--color-error-bg, #fff5f5);
  color: var(--color-error-text, #c53030);
  border-radius: 8px;
  font-size: 13px;
}

.register-btn {
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

.register-btn:hover:not(:disabled) {
  background: var(--color-accent-hover, #1a4f8a);
}

.register-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.login-link {
  margin-top: 24px;
  font-size: 13px;
  color: var(--color-text-muted, #a0aec0);
}

.login-link a {
  color: var(--color-accent, #2b6cb0);
  text-decoration: none;
  font-weight: 600;
}

.login-link a:hover {
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

/* --- Value card (shared with LoginView) --- */
.login-value-card {
  flex: 0 0 260px;
  padding: 28px 24px;
  background: linear-gradient(135deg, #f0f4ff, #faf5ff);
  border: 1px solid rgba(43, 108, 176, 0.12);
  border-radius: 12px;
}

.login-value-card h3 {
  font-size: 15px;
  font-weight: 700;
  color: var(--color-text-primary, #1a365d);
  margin: 0 0 14px;
}

.login-value-card ul {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.login-value-card li {
  font-size: 13px;
  color: var(--color-text-secondary, #4a5568);
  line-height: 1.5;
  padding-left: 16px;
  position: relative;
}

.login-value-card li::before {
  content: '✓';
  position: absolute;
  left: 0;
  color: var(--color-accent, #2b6cb0);
  font-weight: 700;
  font-size: 12px;
}

@media (max-width: 768px) {
  .register-layout {
    flex-direction: column;
    align-items: stretch;
  }

  .login-value-card {
    flex: none;
    order: -1;
  }
}
</style>
