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
            <span v-if="auth.validationErrors['username']" class="field-error">{{
              auth.validationErrors['username']
            }}</span>
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
            <span v-if="auth.validationErrors['email']" class="field-error">{{
              auth.validationErrors['email']
            }}</span>
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
            <span v-if="auth.validationErrors['display_name']" class="field-error">{{
              auth.validationErrors['display_name']
            }}</span>
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
            <span v-else-if="auth.validationErrors['password']" class="field-error">{{
              auth.validationErrors['password']
            }}</span>
          </div>

          <div v-if="auth.error" class="error-message">{{ auth.error }}</div>

          <button
            type="submit"
            class="register-btn"
            :disabled="auth.loading || !username || !email || !password || !!passwordError"
          >
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
  const ok = await auth.register(
    username.value.trim(),
    email.value.trim(),
    password.value,
    displayName.value.trim() || undefined,
  );
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
  padding: var(--space-6);
}

.register-layout {
  display: flex;
  gap: var(--space-8);
  align-items: flex-start;
  max-width: 820px;
  width: 100%;
}

.register-card {
  flex: 1;
  max-width: 400px;
  padding: var(--space-10) 32px;
  background: var(--color-navbar-bg, var(--color-surface));
  border: 1px solid var(--color-border);
  border-radius: var(--radius-2xl);
  text-align: center;
}

.register-card h1 {
  font-size: 24px;
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0 0 var(--space-1);
}

.register-subtitle {
  color: var(--color-text-muted);
  font-size: 14px;
  margin: 0 0 var(--space-8);
}

.register-form {
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

.input-error {
  border-color: var(--color-error-text) !important;
}

.field-error {
  font-size: 12px;
  color: var(--color-error-text);
  margin-top: 2px;
}

.error-message {
  padding: var(--space-2-5) 14px;
  background: var(--color-error-bg);
  color: var(--color-error-text);
  border-radius: var(--radius-lg);
  font-size: 13px;
}

.register-btn {
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

.register-btn:hover:not(:disabled) {
  background: var(--color-accent-hover);
}

.register-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.login-link {
  margin-top: 24px;
  font-size: 13px;
  color: var(--color-text-muted);
}

.login-link a {
  color: var(--color-accent);
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

/* --- Value card (shared with LoginView) --- */
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
