# Sprint 2 → Phase 3 Domain Component Extraction Specification

**版本:** v1.0
**日期:** 2026-08-12
**基线:** 29/30 test files pass, 752/762 tests pass (10 pre-existing failures unrelated to Phase 3)
**vue-tsc:** 零错误

---

## 1. 准入决策

三条分类规则：

1. **既有组件升级契约** — `SourceReferenceCard.vue` 已存在于 `src/components/research/result/`，不适用"新建需 2+ 复用"门禁。Phase 3 修补其路由构造契约。

2. **从零新建的准入门禁** — `EvidenceBadge.vue` 允许新建。底层 100% 包装 `HfbBadge.vue`，零新建 Primitive/CSS。两个挂载点：Result 结果列表页（`EvidenceDetail.vue`）与 Reader 证据区（`ReaderPage.vue`）。

3. **不倒退原则** — Phase 2 已冻结，不回退伪造原型节点。

---

## 2. EvidenceBadge.vue

**路径:** `src/components/common/EvidenceBadge.vue`

**Props 接口:**

```ts
interface EvidenceBadgeProps {
  sourceType: 'primary_source' | 'edition' | 'annotation' | 'modern_scholarship';
  verificationStatus: 'verified' | 'unverified' | 'disputed';
  locatorCompleteness: 'complete' | 'partial' | 'missing';
}
```

**v4.2 映射表:**

| verificationStatus | HfbBadge variant | 显示文案 | dot 指示器 |
|---|---|---|---|
| `verified` | `success` | "已核验" | 否 |
| `unverified` | `neutral` | "未核验" | 否（单独时） |
| `disputed` | `error` | "存疑" | 是 |

| locatorCompleteness | 行为 | dot |
|---|---|---|
| `complete` | 无额外标记 | 否 |
| `partial` | 追加 "· 定位不完整" | 是 |
| `missing` | 追加 "· 无定位" | 是 |

**铁律:**
- `verificationStatus !== 'verified'` 时严禁 `variant === 'success'`
- `verificationStatus !== 'verified'` 时严禁出现 "已核验/已证实" 字样
- 内部仅渲染 `<HfbBadge>`，零新建 CSS 类，零 `<style>` 块

**消费点:**

| 页面 | 文件 | sourceType | verificationStatus | locatorCompleteness |
|---|---|---|---|---|
| Result 列表页 | `EvidenceDetail.vue` | `'primary_source'` | `'unverified'` (硬约束) | 按 passage_id/chunk_id 计算 |
| Reader 证据区 | `ReaderPage.vue` | `readerEvidenceSourceType()` | `'unverified'` (硬约束) | 按 source_passage_id/anchor_chunk_ids 计算 |

---

## 3. SourceReferenceCard.vue（修补）

**路径:** `src/components/research/result/SourceReferenceCard.vue`

**新增 Prop:**

```ts
readerAddressable?: boolean
```

**路由构造契约:**

| readerAddressable | document_id | chunk_id | 路由 |
|---|---|---|---|
| `true` | 存在 | 存在 | `/reader/:documentId#chunk-<chunk_id>` |
| `true` | 存在 | 无 | `/library/:documentId`（回退） |
| `true` | 无 | — | 无内部路由（降级至外部链接/缺失态） |
| `false`/`undefined` | — | — | 无内部路由（走外部链接或缺失态） |

`chunk_id` 不以 `chunk-` 开头时自动补前缀，保证 hash anchor 一致性。

**消费点:** `EvidenceDetail.vue` — 传入 `reader-addressable` prop。

---

## 4. 受影响的文件

| 文件 | 变更类型 | 说明 |
|---|---|---|
| `src/components/common/EvidenceBadge.vue` | 新建 | 领域 Badge 组件 |
| `src/components/research/result/SourceReferenceCard.vue` | 修补 | 新增 `readerAddressable` prop |
| `src/components/research/result/EvidenceDetail.vue` | 修补 | 导入 EvidenceBadge，传入 readerAddressable |
| `src/pages/reader/ReaderPage.vue` | 修补 | 导入 EvidenceBadge，替换 evidence_level 内联文本 |
| `src/__tests__/reader-page.test.ts` | 修补 | 更新断言文本 "证据等级: L2" → "一手文献 · 未核验" |

---

## 5. 门禁状态

| 门禁 | 状态 |
|---|---|
| `npx vue-tsc --noEmit` | ✅ 零错误 |
| `npx eslint` (changed files) | ✅ 零警告 |
| `domain-semantic-regression.test.ts` | ✅ 17/17 |
| `reader-page.test.ts` | ✅ 30/30 |
| `research-result-page.test.ts` | ✅ 111/111 |
| 存量测试（4 失败文件） | ⚠️ 10 项已有失败，非 Phase 3 引入 |
| Design Token 合规 | ✅ 零硬编码 hex |
| HfbBadge wrapper 铁律 | ✅ 100% 包装，零新建 CSS |

---

## 6. 待办/已知局限

1. **verificationStatus 硬约束为 `'unverified'`** — `ResultEvidence` 和 `ReaderEvidence` 均无显式 verification 字段。后端补充字段后，`evidenceVerificationStatus` computed 改为读取该字段。
2. **Reader sourceType 硬编码 `'primary_source'`** — `ReaderEvidence` 无 source_type 字段。后端补充后 `readerEvidenceSourceType()` 读取该字段。
3. **Reader "选区 Context 抽屉" 尚未实现** — 当前 Reader 证据区为内联面板而非抽屉。抽屉化应为独立 Phase，不在本次范围。
