<template>
  <div class="research-new">
    <div class="new-card">
      <h1>{{ t('researchEntry.newTitle') }}</h1>
      <p class="new-subtitle">{{ t('researchEntry.newSubtitle') }}</p>

      <form @submit.prevent="handleSubmit" class="new-form">
        <div class="form-group">
          <label for="topic-name">{{ t('researchEntry.topicName') }}</label>
          <input
            id="topic-name"
            v-model.trim="topicName"
            type="text"
            :placeholder="t('researchEntry.topicNamePlaceholder')"
            required
            autofocus
            class="form-input"
          />
        </div>

        <div class="form-group">
          <label for="topic-desc">{{ t('researchEntry.topicDesc') }}</label>
          <textarea
            id="topic-desc"
            v-model.trim="topicDesc"
            :placeholder="t('researchEntry.topicDescPlaceholder')"
            rows="4"
            class="form-input"
          ></textarea>
        </div>

        <div class="form-actions">
          <button type="submit" class="btn btn--primary" :disabled="!topicName">
            {{ t('researchEntry.create') }}
          </button>
          <router-link :to="{ name: 'home' }" class="btn btn--ghost">
            {{ t('common.cancel') }}
          </router-link>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { useResearchStore } from '@/stores/research';

const { t } = useI18n();
const router = useRouter();
const researchStore = useResearchStore();

const topicName = ref('');
const topicDesc = ref('');

function handleSubmit() {
  if (!topicName.value) return;
  researchStore.setTopic(topicName.value, topicDesc.value);
  router.push({ name: 'research-home' });
}
</script>

<style scoped>
.research-new {
  max-width: 520px;
  margin: var(--space-20) auto;
  padding: 0 var(--space-5);
}

.new-card {
  background: var(--color-navbar-bg, var(--color-surface));
  border: 1px solid var(--color-border);
  border-radius: var(--radius-2xl);
  padding: var(--space-9) 32px;
}

h1 {
  font-size: 22px;
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0 0 var(--space-1-5);
}

.new-subtitle {
  color: var(--color-text-muted);
  font-size: 14px;
  margin: 0 0 var(--space-7);
}

.new-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-4-5);
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-1-5);
}

label {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-secondary);
}

.form-input {
  padding: var(--space-2-5) 14px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  font-size: 14px;
  font-family: inherit;
  color: var(--color-text-primary);
  background: var(--color-page-bg);
  transition: border-color var(--transition-base);
}

.form-input:focus {
  outline: none;
  border-color: var(--color-accent);
  box-shadow: var(--shadow-focus-ring);
}

textarea.form-input {
  resize: vertical;
}

.form-actions {
  display: flex;
  gap: var(--space-3);
  padding-top: 6px;
}

.btn {
  padding: var(--space-2-5) 24px;
  border-radius: var(--radius-lg);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  border: none;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  transition: all var(--transition-base);
}

.btn--primary {
  background: var(--color-accent);
  color: var(--color-surface);
}

.btn--primary:hover:not(:disabled) {
  background: var(--color-accent-hover, var(--color-info));
}

.btn--primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn--ghost {
  background: transparent;
  color: var(--color-text-secondary);
  border: 1px solid var(--color-border);
}

.btn--ghost:hover {
  background: var(--color-hover);
}
</style>
