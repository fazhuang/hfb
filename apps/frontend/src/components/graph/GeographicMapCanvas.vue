<template>
  <div class="geo-canvas">
    <div v-if="loading" class="geo-state">
      <span class="spinner"></span>
      {{ t('common.loading') }}
    </div>
    <div v-else-if="error" class="geo-state geo-state--error">
      {{ error }}
      <button class="geo-retry" @click="$emit('retry')">{{ t('common.retry') }}</button>
    </div>
    <div v-else-if="points.length === 0" class="geo-state">{{ emptyText }}</div>
    <div v-else class="geo-body">
      <div v-if="eras.length > 1" class="geo-filter">
        <select v-model="eraFilter" class="geo-select" :aria-label="t('graph.geoEraFilter')">
          <option value="">{{ t('graph.geoAllEras') }}</option>
          <option v-for="era in eras" :key="era" :value="era">{{ era }}</option>
        </select>
      </div>
      <div class="geo-map">
        <div
          v-for="pt in filteredPoints"
          :key="pt.id"
          class="geo-point"
          :class="[
            `geo-point--${pt.category}`,
            { 'geo-point--active': activeId === pt.id },
          ]"
          :style="positionStyle(pt)"
          :title="`${pt.name} · ${pt.location}`"
          role="button"
          :tabindex="0"
          @click="$emit('select', pt)"
          @keydown.enter="$emit('select', pt)"
        >
          <span class="geo-dot"></span>
          <span class="geo-label">{{ pt.name }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import type { GeoDistributionPoint } from '@/types/graph';

const { t } = useI18n();

const props = defineProps<{
  points: Array<GeoDistributionPoint>;
  loading?: boolean;
  error?: string | null;
  emptyText?: string;
  activeId?: string | null;
}>();

defineEmits<{
  (e: 'select', point: GeoDistributionPoint): void;
  (e: 'retry'): void;
}>();

const eraFilter = ref('');

const eras = computed(() =>
  Array.from(new Set(props.points.map((p) => p.era).filter((e): e is string => !!e))).sort(),
);

const filteredPoints = computed(() => {
  if (!eraFilter.value) return props.points;
  return props.points.filter((p) => p.era === eraFilter.value);
});

// East-Asia bound (display only). Maps geographic coords onto the container.
const BOUNDS = { west: 105.0, east: 130.0, north: 42.0, south: 24.0 };

function positionStyle(pt: GeoDistributionPoint): Record<string, string> {
  const lon = Math.min(BOUNDS.east, Math.max(BOUNDS.west, pt.lng));
  const lat = Math.min(BOUNDS.north, Math.max(BOUNDS.south, pt.lat));
  const x = ((lon - BOUNDS.west) / (BOUNDS.east - BOUNDS.west)) * 100;
  const y = ((BOUNDS.north - lat) / (BOUNDS.north - BOUNDS.south)) * 100;
  return { left: `${x}%`, top: `${y}%` };
}
</script>

<style scoped>
.geo-canvas {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 500px;
  background: var(--color-page-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.geo-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 500px;
  gap: var(--space-3);
  color: var(--color-text-secondary, var(--color-text-muted));
  font-size: 14px;
}

.geo-state--error {
  color: var(--color-error, var(--color-error-text));
}

.geo-retry {
  padding: var(--space-1-5) 16px;
  border: 1px solid var(--color-accent);
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--color-accent);
  cursor: pointer;
  font-size: 13px;
}

.geo-map {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 60% 40%, var(--color-accent-light), transparent 70%);
}

.geo-body {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 500px;
}

.geo-filter {
  position: absolute;
  top: var(--space-3);
  left: var(--space-3);
  z-index: 1;
}

.geo-select {
  padding: var(--space-1) var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface, var(--color-page-bg));
  color: var(--color-text-primary);
  font-size: 12px;
  outline: none;
}

.geo-point {
  position: absolute;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  cursor: pointer;
}

.geo-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--color-accent);
  border: 2px solid var(--color-page-bg);
  box-shadow: 0 0 0 2px var(--color-border);
}

.geo-point--repository .geo-dot {
  background: var(--color-warning);
}

.geo-point--active .geo-dot {
  box-shadow: 0 0 0 3px var(--color-accent);
}

.geo-label {
  margin-top: var(--space-1);
  font-size: 11px;
  color: var(--color-text-secondary, var(--color-text-muted));
  background: var(--color-surface, var(--color-page-bg));
  padding: 1px 6px;
  border-radius: var(--radius-sm);
  white-space: nowrap;
}

.spinner {
  width: 24px;
  height: 24px;
  border: 3px solid var(--color-border);
  border-top-color: var(--color-accent);
  border-radius: 50%;
  animation: spin var(--transition-spinner) linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
