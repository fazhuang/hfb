<template>
  <div class="person-list-view">
    <!-- 头部导览 Hero 组件 -->
    <PersonDomainIntroBanner />

    <div class="page-header">
      <div class="header-titles">
        <h1>{{ t('nav.persons', '人物名录') }}</h1>
        <p class="subtitle">皇甫谧数字人文研究域学术人物考据与学术关联</p>
      </div>
      <div class="search-box">
        <input
          v-model="query"
          type="text"
          :placeholder="t('common.search', '搜索姓名、字号、摘要或专长...') + '...'"
          @keyup.enter="handleSearch"
        />
        <button class="search-btn" @click="handleSearch">
          {{ t('common.search', '搜索') }}
        </button>
      </div>
    </div>

    <!-- 筛选切片控制栏 -->
    <div class="filter-bar">
      <!-- 皇甫谧研究域角色分类筛选切片 -->
      <div class="role-filter-group">
        <span class="filter-label">研究域角色：</span>
        <div class="filter-tabs">
          <button
            v-for="roleOption in roleOptions"
            :key="roleOption.key"
            class="filter-tab-btn"
            :class="{ active: activeRoleFilter === roleOption.key }"
            @click="selectRoleFilter(roleOption.key)"
          >
            {{ roleOption.label }}
          </button>
        </div>
      </div>

      <!-- 研究域数据验证状态切片 -->
      <div class="status-filter-group">
        <span class="filter-label">考据状态：</span>
        <div class="filter-tabs">
          <button
            v-for="statusOption in statusOptions"
            :key="statusOption.key"
            class="filter-tab-btn status-btn"
            :class="{ active: activeStatusFilter === statusOption.key }"
            @click="selectStatusFilter(statusOption.key)"
          >
            {{ statusOption.label }}
          </button>
        </div>
      </div>
    </div>

    <!-- 状态视图 -->
    <div v-if="loading" class="loading-state">
      {{ t('common.loading', '正在加载研究域人物数据...') }}
    </div>
    <div v-else-if="error" class="error-state">
      <p class="error-text">{{ error }}</p>
      <button v-if="isAuthError" class="login-redirect-btn" @click="goToLogin">
        {{ t('auth.login', '前往登录') }}
      </button>
    </div>
    <div v-else-if="items.length === 0" class="empty-state">
      {{ t('common.noData', '未找到符合条件的研究域人物') }}
    </div>

    <!-- 人物卡片网格 -->
    <div v-else class="person-grid">
      <div
        v-for="person in items"
        :key="person.id"
        class="person-card"
        @click="navigateToDetail(person.id)"
      >
        <div class="card-header">
          <div class="title-group">
            <h3 class="person-name">{{ person.name }}</h3>
            <span v-if="person.name_zh" class="person-name-zh">({{ person.name_zh }})</span>
          </div>

          <div class="badge-group">
            <PersonRoleBadge :role="person.research_relation_role" />
            <span
              class="domain-status-tag"
              :class="person.domain_status === 'verified' ? 'status-verified' : 'status-pending'"
            >
              {{ person.domain_status === 'verified' ? '已验证研究域' : '待考资料' }}
            </span>
          </div>
        </div>

        <div class="card-meta">
          <span v-if="person.dynasty" class="meta-item">{{ person.dynasty }}</span>
          <span v-if="formatLifespan(person)" class="meta-item">{{ formatLifespan(person) }}</span>
          <span v-if="person.courtesy_name" class="meta-item">字 {{ person.courtesy_name }}</span>
          <span v-if="person.expertise" class="meta-item expertise">{{ person.expertise }}</span>
        </div>

        <!-- 皇甫谧研究域关系摘要 -->
        <div v-if="person.domain_relation_summary" class="relation-summary-box">
          <span class="summary-label">研究域关系摘要：</span>
          <p class="summary-text">{{ person.domain_relation_summary }}</p>
        </div>

        <!-- 生平或著作预览 -->
        <p v-else-if="person.biography" class="biography-preview">
          {{ person.biography }}
        </p>

        <!-- 锚点路径简写 -->
        <AnchorPathBreadcrumb
          v-if="person.anchor_path"
          :anchor-path="person.anchor_path"
        />
      </div>
    </div>

    <!-- 分页 -->
    <div v-if="total > limit" class="pagination">
      <button :disabled="page <= 1" @click="changePage(page - 1)">
        {{ t('common.back', '上一页') }}
      </button>
      <span class="page-info">{{ page }} / {{ totalPages }}</span>
      <button :disabled="page >= totalPages" @click="changePage(page + 1)">
        {{ t('common.next', '下一页') }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRouter, useRoute } from 'vue-router';
import api, { getErrorMessage } from '@/api/client';
import PersonRoleBadge from '@/components/person/PersonRoleBadge.vue';
import AnchorPathBreadcrumb from '@/components/person/AnchorPathBreadcrumb.vue';
import PersonDomainIntroBanner from '@/components/person/PersonDomainIntroBanner.vue';

export interface PersonListItem {
  id: string;
  name: string;
  name_zh?: string | null;
  name_pinyin?: string | null;
  courtesy_name?: string | null;
  pseudonym?: string | null;
  dynasty?: string | null;
  birth_year?: number | null;
  death_year?: number | null;
  expertise?: string | null;
  biography?: string | null;
  domain_status: 'verified' | 'pending' | string;
  research_relation_role?: string | null;
  domain_relation_summary?: string | null;
  anchor_path?: string | null;
}

interface FilterOption {
  key: string;
  label: string;
}

const { t } = useI18n();
const router = useRouter();
const route = useRoute();

const items = ref<Array<PersonListItem>>([]);
const total = ref<number>(0);
const loading = ref<boolean>(false);
const error = ref<string | null>(null);

const isAuthError = computed<boolean>(() => {
  if (!error.value) return false;
  return (
    error.value.includes('未登录') ||
    error.value.includes('登录会话已过期') ||
    error.value.includes('401')
  );
});

function goToLogin(): void {
  router.push({ name: 'login', query: { redirect: route.fullPath } });
}

const query = ref<string>('');
const page = ref<number>(1);
const limit = ref<number>(20);

// 默认过滤检索 domain_status == 'verified' 数据
const activeStatusFilter = ref<string>('verified');
const activeRoleFilter = ref<string>('all');

const roleOptions: Array<FilterOption> = [
  { key: 'all', label: '全部分类' },
  { key: 'huangfu_mi_self', label: '皇甫谧本人' },
  { key: 'master_predecessor,friend_contemporary', label: '师承/交游' },
  { key: 'annotator_editor', label: '历代注校' },
  { key: 'transmission_scholar', label: '学术传播' },
  { key: 'modern_researcher', label: '现代研究' },
];

const statusOptions: Array<FilterOption> = [
  { key: 'verified', label: '已验证研究域' },
  { key: 'pending', label: '待考资料' },
  { key: 'all', label: '全部数据' },
];

const totalPages = computed<number>(() => Math.max(1, Math.ceil(total.value / limit.value)));

function formatLifespan(person: PersonListItem): string | null {
  if (person.birth_year && person.death_year) {
    return `${person.birth_year} - ${person.death_year}`;
  }
  if (person.birth_year) {
    return `${person.birth_year} - ?`;
  }
  return null;
}

async function fetchPersons(): Promise<void> {
  loading.value = true;
  error.value = null;
  try {
    const params: Record<string, string | number> = {
      page: page.value,
      limit: limit.value,
    };
    if (query.value.trim()) {
      params.q = query.value.trim();
    }
    if (activeStatusFilter.value !== 'all') {
      params.domain_status = activeStatusFilter.value;
    }
    if (activeRoleFilter.value !== 'all') {
      params.research_relation_role = activeRoleFilter.value;
    }

    const { data } = await api.get('/api/v1/persons', { params });
    const body = data.data ?? data;
    items.value = body.items ?? [];
    total.value = body.total ?? 0;
  } catch (err: unknown) {
    error.value = getErrorMessage(err, '获取人物数据失败');
  } finally {
    loading.value = false;
  }
}

function handleSearch(): void {
  page.value = 1;
  fetchPersons();
}

function selectRoleFilter(key: string): void {
  activeRoleFilter.value = key;
  page.value = 1;
  fetchPersons();
}

function selectStatusFilter(key: string): void {
  activeStatusFilter.value = key;
  page.value = 1;
  fetchPersons();
}

function changePage(p: number): void {
  page.value = p;
  fetchPersons();
}

function navigateToDetail(id: string): void {
  router.push(`/persons/${id}`);
}

onMounted(() => {
  const queryRole = (route.query.role || route.query.research_relation_role) as string | undefined;
  if (queryRole && roleOptions.some((opt) => opt.key === queryRole)) {
    activeRoleFilter.value = queryRole;
  }
  fetchPersons();
});

watch(
  () => route.query.role,
  (newRole) => {
    if (typeof newRole === 'string' && roleOptions.some((opt) => opt.key === newRole)) {
      activeRoleFilter.value = newRole;
      page.value = 1;
      fetchPersons();
    }
  }
);
</script>

<style scoped>
.person-list-view {
  max-width: 1100px;
  margin: 0 auto;
  padding: var(--space-8, 32px) var(--space-6, 24px);
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: var(--space-6, 24px);
  flex-wrap: wrap;
  gap: var(--space-4, 16px);
}

.header-titles h1 {
  font-size: var(--text-3xl, 28px);
  font-weight: var(--font-bold, 700);
  color: var(--color-text-primary);
  margin: 0 0 var(--space-1, 4px);
}

.subtitle {
  font-size: var(--text-sm, 14px);
  color: var(--color-text-muted);
  margin: 0;
}

.search-box {
  display: flex;
  gap: var(--space-2, 8px);
}

.search-box input {
  padding: var(--space-2, 8px) var(--space-3, 12px);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg, 8px);
  font-size: var(--text-base, 14px);
  min-width: 260px;
  background: var(--color-page-bg);
  color: var(--color-text-primary);
}

.search-btn {
  padding: var(--space-2, 8px) var(--space-4, 16px);
  background: var(--color-accent);
  color: var(--color-surface);
  border: none;
  border-radius: var(--radius-lg, 8px);
  cursor: pointer;
  font-size: var(--text-sm, 14px);
  font-weight: var(--font-semibold, 600);
}

.search-btn:hover {
  background: var(--color-accent-hover);
}

/* 筛选切片栏 */
.filter-bar {
  display: flex;
  flex-direction: column;
  gap: var(--space-3, 12px);
  padding: var(--space-4, 16px);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl, 12px);
  margin-bottom: var(--space-6, 24px);
}

.role-filter-group,
.status-filter-group {
  display: flex;
  align-items: center;
  gap: var(--space-3, 12px);
  flex-wrap: wrap;
}

.filter-label {
  font-size: var(--text-sm, 14px);
  font-weight: var(--font-semibold, 600);
  color: var(--color-text-muted);
  min-width: 90px;
}

.filter-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2, 8px);
}

.filter-tab-btn {
  padding: var(--space-1-5, 6px) var(--space-3, 12px);
  font-size: var(--text-xs, 12px);
  font-weight: var(--font-medium, 500);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md, 6px);
  background: var(--color-page-bg);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all var(--transition-base, 0.2s);
}

.filter-tab-btn:hover {
  background: var(--color-hover);
  color: var(--color-text-primary);
}

.filter-tab-btn.active {
  background: var(--color-accent);
  color: var(--color-surface);
  border-color: var(--color-accent);
}

.filter-tab-btn.status-btn.active {
  background: var(--color-info);
  border-color: var(--color-info);
}

/* 网格与卡片 */
.person-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: var(--space-5, 20px);
}

.person-card {
  display: flex;
  flex-direction: column;
  padding: var(--space-5, 20px);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl, 12px);
  background: var(--color-surface);
  cursor: pointer;
  transition: border-color var(--transition-base, 0.2s), box-shadow var(--transition-base, 0.2s);
}

.person-card:hover {
  border-color: var(--color-accent);
  box-shadow: var(--shadow-sm, 0 1px 3px rgba(0,0,0,0.1));
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--space-2, 8px);
  margin-bottom: var(--space-2, 8px);
}

.title-group {
  display: flex;
  align-items: baseline;
  gap: var(--space-1-5, 6px);
}

.person-name {
  font-size: var(--text-xl, 20px);
  font-weight: var(--font-bold, 700);
  color: var(--color-text-primary);
  margin: 0;
}

.person-name-zh {
  font-size: var(--text-sm, 14px);
  color: var(--color-text-muted);
}

.badge-group {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: var(--space-1, 4px);
}

.domain-status-tag {
  font-size: var(--text-xs, 12px);
  padding: var(--space-0-5, 2px) var(--space-2, 8px);
  border-radius: var(--radius-sm, 4px);
  font-weight: var(--font-medium, 500);
}

.status-verified {
  background: var(--color-success-bg);
  color: var(--color-success-text);
  border: 1px solid var(--color-success);
}

.status-pending {
  background: var(--color-warning-bg);
  color: var(--color-warning-text);
  border: 1px solid var(--color-warning);
}

.card-meta {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2, 8px);
  margin-bottom: var(--space-3, 12px);
}

.meta-item {
  font-size: var(--text-xs, 12px);
  padding: var(--space-0-5, 2px) var(--space-2, 8px);
  background: var(--color-tag-bg);
  border-radius: var(--radius-sm, 4px);
  color: var(--color-text-secondary);
}

.meta-item.expertise {
  color: var(--color-accent);
  background: var(--color-accent-light);
}

.relation-summary-box {
  padding: var(--space-3, 12px);
  background: var(--color-hover);
  border-left: 3px solid var(--color-accent);
  border-radius: var(--radius-md, 6px);
  margin-bottom: var(--space-3, 12px);
}

.summary-label {
  font-size: var(--text-xs, 12px);
  font-weight: var(--font-bold, 700);
  color: var(--color-accent);
  display: block;
  margin-bottom: var(--space-1, 4px);
}

.summary-text {
  font-size: var(--text-sm, 14px);
  color: var(--color-text-primary);
  margin: 0;
  line-height: 1.5;
}

.biography-preview {
  font-size: var(--text-sm, 14px);
  color: var(--color-text-secondary);
  line-height: 1.5;
  margin: 0 0 var(--space-3, 12px);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.loading-state,
.error-state,
.empty-state {
  text-align: center;
  padding: var(--space-15, 60px) var(--space-5, 20px);
  color: var(--color-text-muted);
  font-size: var(--text-base, 16px);
}

.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-3, 12px);
}

.error-text {
  margin: 0;
}

.login-redirect-btn {
  padding: var(--space-2, 8px) var(--space-4, 16px);
  background: var(--color-accent);
  color: var(--color-surface);
  border: none;
  border-radius: var(--radius-lg, 8px);
  cursor: pointer;
  font-size: var(--text-sm, 14px);
  font-weight: var(--font-semibold, 600);
  transition: background var(--transition-base, 0.2s);
}

.login-redirect-btn:hover {
  background: var(--color-accent-hover);
}

.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-4, 16px);
  margin-top: var(--space-8, 32px);
  font-size: var(--text-sm, 14px);
  color: var(--color-text-secondary);
}

.pagination button {
  padding: var(--space-2, 8px) var(--space-4, 16px);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md, 6px);
  background: var(--color-surface);
  color: var(--color-text-primary);
  cursor: pointer;
  font-size: var(--text-sm, 14px);
}

.pagination button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
</style>
