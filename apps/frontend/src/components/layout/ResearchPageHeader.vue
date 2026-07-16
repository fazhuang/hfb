<template>
  <header class="research-page-header">
    <div class="rph-top">
      <div class="rph-title-group">
        <!-- Breadcrumbs -->
        <nav v-if="breadcrumbs && breadcrumbs.length > 0" class="rph-breadcrumbs" aria-label="Breadcrumb">
          <template v-for="(crumb, idx) in breadcrumbs" :key="idx">
            <router-link v-if="crumb.to" :to="crumb.to" class="rph-breadcrumb-link">
              {{ crumb.label }}
            </router-link>
            <span v-else class="rph-breadcrumb-current">{{ crumb.label }}</span>
            <span v-if="idx < breadcrumbs.length - 1" class="rph-breadcrumb-sep">/</span>
          </template>
        </nav>

        <!-- Title + Description -->
        <div class="rph-heading">
          <h1 class="rph-title">{{ title }}</h1>
          <p v-if="description" class="rph-description">{{ description }}</p>
        </div>
      </div>

      <!-- Actions slot -->
      <div v-if="$slots.actions" class="rph-actions">
        <slot name="actions" />
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
export interface Breadcrumb {
  label: string;
  to?: string | { name: string; params?: Record<string, string> };
}

defineProps<{
  title: string;
  description?: string;
  breadcrumbs?: Breadcrumb[];
}>();
</script>

<style scoped>
.research-page-header {
  padding: 20px 32px;
  border-bottom: 1px solid var(--color-border, #e2e8f0);
  background: var(--color-navbar-bg, #ffffff);
}

.rph-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.rph-title-group {
  flex: 1;
  min-width: 0;
}

.rph-breadcrumbs {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
  font-size: 13px;
  flex-wrap: wrap;
}

.rph-breadcrumb-link {
  color: var(--color-text-muted, #a0aec0);
  text-decoration: none;
}

.rph-breadcrumb-link:hover {
  color: var(--color-accent, #2b6cb0);
  text-decoration: underline;
}

.rph-breadcrumb-current {
  color: var(--color-text-secondary, #4a5568);
}

.rph-breadcrumb-sep {
  color: var(--color-border, #e2e8f0);
}

.rph-heading {
  min-width: 0;
}

.rph-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--color-text-primary, #1a365d);
  margin: 0;
  line-height: 1.3;
}

.rph-description {
  margin: 6px 0 0;
  font-size: 14px;
  color: var(--color-text-muted, #718096);
  line-height: 1.5;
}

.rph-actions {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

/* ---- Responsive ---- */
@media (max-width: 768px) {
  .research-page-header {
    padding: 16px 20px;
  }

  .rph-top {
    flex-direction: column;
  }

  .rph-title {
    font-size: 18px;
  }
}
</style>
