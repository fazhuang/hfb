<!--
  LegacyRedirect — session-aware redirect for old research/workspace URLs.

  Replaces the static `redirect: '/research'` that unconditionally drops
  tab and project context. On mount:
    1. Fetches the user's most recently updated session
    2. Resolves the canonical route based on the legacy route name and
       optional `?tab=` query parameter
    3. Redirects with full project context

  Fallback: if no sessions exist or the API fails, redirect to
  /research (project list).

  Contract (phase3-migration-contract §2.1):
    - /research/workspace      → /research/:projectId/workspace
    - /research/workspace?tab=materials    → /library
    - /research/workspace?tab=versions     → /library
    - /research/workspace?tab=notes        → /research/:projectId/workspace
    - /research/workspace?tab=reports      → /reports
    - /research/workspace?tab=research     → /research/:projectId/version-comparison
    - /research/workspace?tab=v4-research  → /research/:projectId/workflow
    - /workspace               → /research/:projectId/workspace
    - /v4/research             → /research/:projectId/workflow
    - /v4/research-internal    → /research/:projectId/workflow
    - /v4                      → /research/:projectId/workflow
-->
<script setup lang="ts">
import { onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import api from '@/api/client';

const route = useRoute();
const router = useRouter();

// ---------------------------------------------------------------------------
// Tab → canonical route resolver (for ?tab= on /research/workspace)
// ---------------------------------------------------------------------------
type CanonicalResolver = (
  projectId: string,
) => { name: string; params: Record<string, string>; query?: Record<string, string> };

const TAB_MAP: Record<string, CanonicalResolver> = {
  materials: () => ({ name: 'library-search', params: {} }),
  versions: () => ({ name: 'library-search', params: {} }),
  notes: (pid) => ({ name: 'research-project-workspace', params: { projectId: pid } }),
  reports: () => ({ name: 'report-list', params: {} }),
  research: (pid) => ({
    name: 'research-project-version-comparison',
    params: { projectId: pid },
  }),
  'v4-research': (pid) => ({
    name: 'research-project-workflow',
    params: { projectId: pid },
  }),
};

// ---------------------------------------------------------------------------
// Legacy-route-name → canonical route resolver
// (no ?tab= — map directly by route name)
// ---------------------------------------------------------------------------
const ROUTE_NAME_MAP: Record<string, CanonicalResolver> = {
  'legacy-workspace': (pid) => ({
    name: 'research-project-workspace',
    params: { projectId: pid },
  }),
  'legacy-v4-research': (pid) => ({
    name: 'research-project-workflow',
    params: { projectId: pid },
  }),
  'legacy-v4-research-internal': (pid) => ({
    name: 'research-project-workflow',
    params: { projectId: pid },
  }),
  'legacy-v4': (pid) => ({
    name: 'research-project-workflow',
    params: { projectId: pid },
  }),
};

// ---------------------------------------------------------------------------
// Redirect logic
// ---------------------------------------------------------------------------
onMounted(async () => {
  let projectId: string | null = null;

  // Step 1: resolve the most recently updated session
  try {
    // Backend returns sessions ordered by updated_at desc — index 0 is most recent.
    const { data } = await api.get('/api/v1/workspace/sessions', {
      params: { limit: 1 },
    });
    const sessions = (data.data ?? []) as Array<{ id: string }>;
    if (sessions.length > 0 && sessions[0]) {
      projectId = sessions[0].id;
    }
  } catch {
    // API unreachable — fall through to fallback
  }

  // Step 2: resolve canonical target
  const tab = route.query.tab as string | undefined;
  let target: ReturnType<CanonicalResolver> | null = null;

  if (projectId) {
    // Tab-aware redirect (only for old /research/workspace?tab=...)
    if (tab && TAB_MAP[tab]) {
      target = TAB_MAP[tab](projectId);
    } else {
      // Route-name-based redirect
      const legacyName = (route.name as string) || '';
      const mapper = ROUTE_NAME_MAP[legacyName];
      if (mapper) {
        target = mapper(projectId);
      }
    }
  }

  // Step 3: execute redirect
  if (target) {
    await router.replace({
      name: target.name,
      params: target.params,
      query: target.query,
    });
  } else {
    // Fallback: no sessions, unmapped route, or API error → project list
    await router.replace({ name: 'research-project-list' });
  }
});
</script>

<template>
  <div class="legacy-redirect">
    <p class="legacy-redirect-text">正在重定向…</p>
  </div>
</template>

<style scoped>
.legacy-redirect {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 50vh;
}

.legacy-redirect-text {
  color: var(--color-text-muted);
  font-size: var(--text-base);
}
</style>
