<template>
  <component :is="IconComponent" :size="size" :color="color" :class="iconClass" :aria-hidden="ariaHidden" :aria-label="ariaLabel" role="img" />
</template>

<script setup lang="ts">
import { computed } from 'vue';
import {
  BookOpen,
  Search,
  FileText,
  ChevronRight,
  House,
  Library,
  FlaskConical,
  BarChart3,
  Building2,
  User,
  ScrollText,
  Link,
  Shield,
  Lock,
  Check,
  ClipboardList,
  Settings,
  X,
  TriangleAlert,
  Info,
  Inbox,
  PackageOpen,
  ArrowRight,
  ArrowLeft,
  Bot,
  PenLine,
  Diff,
  Users,
  CircleAlert,
  CheckCircle,
  XCircle,
  BookMarked,
  GitBranch,
  ChevronDown,
  ChevronUp,
  CheckCheck,
  Dna,
} from '@lucide/vue';

type LucideIconName =
  | 'book-open'
  | 'search'
  | 'file-text'
  | 'chevron-right'
  | 'house'
  | 'library'
  | 'flask-conical'
  | 'bar-chart-3'
  | 'building-2'
  | 'user'
  | 'scroll-text'
  | 'link'
  | 'shield'
  | 'lock'
  | 'check'
  | 'clipboard-list'
  | 'settings'
  | 'x'
  | 'triangle-alert'
  | 'info'
  | 'inbox'
  | 'package-open'
  | 'arrow-right'
  | 'arrow-left'
  | 'bot'
  | 'pen-line'
  | 'diff'
  | 'users'
  | 'circle-alert'
  | 'check-circle'
  | 'x-circle'
  | 'book-marked'
  | 'git-branch'
  | 'chevron-down'
  | 'chevron-up'
  | 'check-check'
  | 'dna';

export type { LucideIconName };

const ICON_MAP: Record<LucideIconName, unknown> = {
  'book-open': BookOpen,
  search: Search,
  'file-text': FileText,
  'chevron-right': ChevronRight,
  house: House,
  library: Library,
  'flask-conical': FlaskConical,
  'bar-chart-3': BarChart3,
  'building-2': Building2,
  user: User,
  'scroll-text': ScrollText,
  link: Link,
  shield: Shield,
  lock: Lock,
  check: Check,
  'clipboard-list': ClipboardList,
  settings: Settings,
  x: X,
  'triangle-alert': TriangleAlert,
  info: Info,
  inbox: Inbox,
  'package-open': PackageOpen,
  'arrow-right': ArrowRight,
  'arrow-left': ArrowLeft,
  bot: Bot,
  'pen-line': PenLine,
  diff: Diff,
  users: Users,
  'circle-alert': CircleAlert,
  'check-circle': CheckCircle,
  'x-circle': XCircle,
  'book-marked': BookMarked,
  'git-branch': GitBranch,
  'chevron-down': ChevronDown,
  'chevron-up': ChevronUp,
  'check-check': CheckCheck,
  dna: Dna,
};

const props = withDefaults(
  defineProps<{
    /** Icon name from the approved Lucide set (kebab-case Lucide name) */
    icon: LucideIconName;
    /** Icon size in px (applied to Lucide's size prop) */
    size?: number;
    /** Token-based CSS color only; no direct hex */
    color?: string;
    /** Accessible label for standalone icon buttons or icon-only controls */
    ariaLabel?: string;
    /** Hide from screen readers; default true per icon-only convention */
    ariaHidden?: boolean;
  }>(),
  {
    size: 20,
    color: 'currentColor',
    ariaHidden: true,
  },
);

const IconComponent = computed(() => ICON_MAP[props.icon]);

const ariaHidden = computed(() =>
  props.ariaLabel ? undefined : props.ariaHidden,
);

const iconClass = computed(() => ['hfb-icon', props.ariaLabel ? '' : 'hfb-icon--decorative'].filter(Boolean).join(' '));
</script>

<style scoped>
.hfb-icon {
  display: inline-block;
  vertical-align: middle;
  flex-shrink: 0;
}
</style>
