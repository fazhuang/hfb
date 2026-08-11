<template>
  <span
    v-if="roleInfo"
    class="person-role-badge"
    :style="roleInfo.style"
  >
    {{ roleInfo.label }}
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue';

export interface RoleBadgeConfig {
  label: string;
  style: Record<string, string>;
}

const props = defineProps<{
  role?: string | null;
}>();

const ROLE_MAP: Record<string, RoleBadgeConfig> = {
  huangfu_mi_self: {
    label: '皇甫谧本人',
    style: {
      backgroundColor: 'var(--color-accent-light)',
      color: 'var(--color-accent)',
      borderColor: 'var(--color-accent)',
    },
  },
  master_predecessor: {
    label: '师承渊源',
    style: {
      backgroundColor: 'var(--color-info-bg)',
      color: 'var(--color-info-text)',
      borderColor: 'var(--color-info)',
    },
  },
  friend_contemporary: {
    label: '魏晋交游',
    style: {
      backgroundColor: 'var(--color-success-bg)',
      color: 'var(--color-success-text)',
      borderColor: 'var(--color-success)',
    },
  },
  annotator_editor: {
    label: '历代注校',
    style: {
      backgroundColor: 'var(--color-warning-bg)',
      color: 'var(--color-warning-text)',
      borderColor: 'var(--color-warning)',
    },
  },
  transmission_scholar: {
    label: '学术传播',
    style: {
      backgroundColor: 'var(--color-hover)',
      color: 'var(--color-text-primary)',
      borderColor: 'var(--color-border)',
    },
  },
  modern_researcher: {
    label: '现代研究',
    style: {
      backgroundColor: 'var(--color-tag-bg)',
      color: 'var(--color-text-secondary)',
      borderColor: 'var(--color-border)',
    },
  },
};

const roleInfo = computed<RoleBadgeConfig | null>(() => {
  if (!props.role) return null;
  const entry = ROLE_MAP[props.role];
  if (entry) {
    return entry;
  }
  return {
    label: props.role,
    style: {
      backgroundColor: 'var(--color-tag-bg)',
      color: 'var(--color-text-muted)',
      borderColor: 'var(--color-border)',
    },
  };
});
</script>

<style scoped>
.person-role-badge {
  display: inline-flex;
  align-items: center;
  padding: var(--space-0-5, 2px) var(--space-2, 8px);
  border-width: 1px;
  border-style: solid;
  border-radius: var(--radius-sm, 4px);
  font-size: var(--text-xs, 12px);
  font-weight: var(--font-semibold, 600);
  line-height: 1.4;
  white-space: nowrap;
}
</style>
