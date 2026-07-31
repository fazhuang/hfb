<template>
  <header class="research-page-header">
    <div class="rph-top">
      <div class="rph-title-group">
        <!-- Breadcrumbs -->
        <nav
          v-if="breadcrumbs && breadcrumbs.length > 0"
          class="rph-breadcrumbs"
          aria-label="Breadcrumb"
        >
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
  padding: var(--space-5) var(--space-8);
  border-bottom: 1px solid var(--color-border);
  background: var(--color-surface);
}

.rph-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--space-4);
}

.rph-title-group {
  flex: 1;
  min-width: 0;
}

.rph-breadcrumbs {
  display: flex;
  align-items: center;
  gap: var(--space-1-5);
  margin-bottom: var(--space-2);
  font-size: var(--text-sm);
  flex-wrap: wrap;
}

.rph-breadcrumb-link {
  color: var(--color-text-muted);
  text-decoration: none;
}

.rph-breadcrumb-link:hover {
  color: var(--color-accent);
  text-decoration: underline;
}

.rph-breadcrumb-link:focus-visible {
  color: var(--color-accent);
  text-decoration: underline;
}

.rph-breadcrumb-current {
  color: var(--color-text-secondary);
}

.rph-breadcrumb-sep {
  color: var(--color-border);
}

.rph-heading {
  min-width: 0;
}

.rph-title {
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
  color: var(--color-text-primary);
  margin: 0;
  line-height: var(--leading-tight);
}

.rph-description {
  margin: var(--space-1-5) 0 0;
  font-size: var(--text-base);
  color: var(--color-text-muted);
  line-height: var(--leading-normal);
}

.rph-actions {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

/* ---- Responsive ---- */
@media (max-width: 768px) {
  .research-page-header {
    padding: var(--space-4) var(--space-5);
  }

  .rph-top {
    flex-direction: column;
  }

  .rph-title {
    font-size: 18px;
  }
}
</style>
