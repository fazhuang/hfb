<template>
  <form @submit.prevent="handleLogin" class="login-form" novalidate>
    <div class="form-group">
      <label for="login-username">{{ t('auth.username') }}</label>
      <input
        id="login-username"
        v-model="username"
        type="text"
        autocomplete="username"
        :disabled="auth.loading"
        :placeholder="t('auth.usernamePlaceholder')"
        required
      />
    </div>

    <div class="form-group">
      <label for="login-password">{{ t('auth.password') }}</label>
      <input
        id="login-password"
        v-model="password"
        type="password"
        autocomplete="current-password"
        :disabled="auth.loading"
        :placeholder="t('auth.passwordPlaceholder')"
        required
      />
    </div>

    <div v-if="displayError" class="error-message" role="alert">
      {{ displayError }}
    </div>

    <button
      type="submit"
      class="login-btn"
      :disabled="auth.loading || !username.trim() || !password"
    >
      <span v-if="auth.loading" class="spinner" aria-hidden="true"></span>
      {{ auth.loading ? t('auth.loggingIn') : t('auth.login') }}
    </button>
  </form>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { useAuthStore } from '@/stores/auth';

const emit = defineEmits<{
  (e: 'success'): void;
}>();

const { t } = useI18n();
const auth = useAuthStore();

const username = ref<string>('');
const password = ref<string>('');
const localError = ref<string>('');

const displayError = computed<string>(() => {
  return localError.value || auth.error || '';
});

async function handleLogin(): Promise<void> {
  localError.value = '';
  const trimmedUser = username.value.trim();

  if (!trimmedUser) {
    localError.value = t('auth.usernameRequired') || '请输入用户名';
    return;
  }
  if (!password.value) {
    localError.value = t('auth.passwordRequired') || '请输入密码';
    return;
  }

  const ok = await auth.login(trimmedUser, password.value);
  if (ok) {
    emit('success');
  }
}
</script>

<style scoped>
.login-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  text-align: left;
  width: 100%;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-1-5);
}

.form-group label {
  font-size: var(--text-xs);
  font-weight: var(--font-bold);
  color: var(--color-text-secondary);
}

.form-group input {
  padding: var(--space-2-5) var(--space-3);
  border: 1px solid var(--color-input-border);
  border-radius: var(--radius-lg);
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  background: var(--color-input-bg);
  outline: none;
  transition: border-color var(--transition-base);
}

.form-group input:focus {
  border-color: var(--color-accent);
  box-shadow: var(--color-input-focus-ring);
}

.form-group input:disabled {
  opacity: 0.6;
  background: var(--color-disabled-bg);
  color: var(--color-disabled-text);
  cursor: not-allowed;
}

.error-message {
  padding: var(--space-2-5) var(--space-3-5);
  background: var(--color-error-bg);
  color: var(--color-error-text);
  border-radius: var(--radius-lg);
  font-size: var(--text-xs);
  line-height: 1.4;
}

.login-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: var(--space-3);
  background: var(--color-accent);
  color: var(--color-on-accent);
  border: none;
  border-radius: var(--radius-lg);
  font-size: var(--text-base);
  font-weight: var(--font-bold);
  cursor: pointer;
  transition: background var(--transition-base);
  margin-top: var(--space-2);
}

.login-btn:hover:not(:disabled) {
  background: var(--color-accent-hover);
}

.login-btn:disabled {
  opacity: 0.6;
  background: var(--color-disabled-bg);
  color: var(--color-disabled-text);
  cursor: not-allowed;
}

.spinner {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid var(--color-accent-alpha-15);
  border-top-color: var(--color-on-accent);
  border-radius: 50%;
  animation: spin var(--transition-spinner) var(--ease-linear) infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
