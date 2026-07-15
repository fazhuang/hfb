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
  margin: 80px auto;
  padding: 0 20px;
}

.new-card {
  background: var(--color-navbar-bg, #fff);
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 12px;
  padding: 36px 32px;
}

h1 {
  font-size: 22px;
  font-weight: 700;
  color: var(--color-text-primary, #1a365d);
  margin: 0 0 6px;
}

.new-subtitle {
  color: var(--color-text-muted, #718096);
  font-size: 14px;
  margin: 0 0 28px;
}

.new-form {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

label {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-secondary, #4a5568);
}

.form-input {
  padding: 10px 14px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 8px;
  font-size: 14px;
  font-family: inherit;
  color: var(--color-text-primary, #1a365d);
  background: var(--color-page-bg, #fafafa);
  transition: border-color 0.15s;
}

.form-input:focus {
  outline: none;
  border-color: var(--color-accent, #4299e1);
  box-shadow: 0 0 0 3px rgba(66, 153, 225, 0.15);
}

textarea.form-input {
  resize: vertical;
}

.form-actions {
  display: flex;
  gap: 12px;
  padding-top: 6px;
}

.btn {
  padding: 10px 24px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  border: none;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  transition: all 0.15s;
}

.btn--primary {
  background: var(--color-accent, #4299e1);
  color: #fff;
}

.btn--primary:hover:not(:disabled) {
  background: var(--color-accent-hover, #3182ce);
}

.btn--primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn--ghost {
  background: transparent;
  color: var(--color-text-secondary, #4a5568);
  border: 1px solid var(--color-border, #e2e8f0);
}

.btn--ghost:hover {
  background: var(--color-hover, #edf2f7);
}
</style>
