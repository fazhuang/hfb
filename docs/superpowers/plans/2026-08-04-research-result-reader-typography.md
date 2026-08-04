# Research Result Reader Typography — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 优化 `ResearchReportViewer.vue` 正文排版：收敛行宽、强化章节锚点、拉开段落节奏、修正引用标记基线对齐与触控区域。

**Architecture:** 单文件样式修改。仅改 `ResearchReportViewer.vue` 的 `<style scoped>` 区块，不碰 template、script、composable、路由、状态管理。

**Tech Stack:** Vue 3 SFC scoped CSS, CSS custom properties (design tokens)

## Global Constraints

- 白名单：仅 `apps/frontend/src/components/research/result/ResearchReportViewer.vue`
- 禁止后端、持久化、路由、RBAC、V4 API、Workspace、Knowledge Explorer
- Citation → Evidence → SourceRef trace_id / passage_id 绑定保持不动
- 375×812、1280×800、200% zoom 通过
- 无直接 hex、无新增 any
- 单原子提交，不推送，不改历史

---

## 文件结构

| 动作 | 文件 | 职责 |
|------|------|------|
| Modify | `apps/frontend/src/components/research/result/ResearchReportViewer.vue` (lines 250-317) | 所有四组排版优化 |

---

### Task 1: 四组排版优化 (A4 + A2 + A1 + A3)

**Files:**
- Modify: `apps/frontend/src/components/research/result/ResearchReportViewer.vue:250-317`

**Interfaces:**
- Consumes: 无（纯样式修改，不改变任何 props/emits/slots）
- Produces: 无新接口。现有 `select-citation` emit、citation marker button 行为、`isSelectedCitation()` 逻辑全部不变

---

- [ ] **Step 1: A4 — 阅读栏宽度收敛**

修改 `.rrv-report`（当前 lines 250-252）：
```css
.rrv-report {
  max-width: 680px;
  margin-inline: auto;
  padding-inline: var(--space-4);
}
```

旧值：
```css
.rrv-report {
  padding: 0;
}
```

- [ ] **Step 2: A2 — 章节层级与扫读锚点**

修改 `.rrv-section-block`（当前 lines 262-264）：
```css
.rrv-section-block {
  margin-bottom: 32px;
}
```
旧值：`margin-bottom: 20px;`

修改 `.rrv-section-heading`（当前 lines 266-273）：
```css
.rrv-section-heading {
  font-size: 17px;
  font-weight: 600;
  color: var(--color-text-primary, var(--color-hover));
  margin: 16px 0 var(--space-3);
  border-left: 4px solid var(--color-accent);
  padding-left: 12px;
}
```
旧值：`font-size: 16px`，`margin: 0 0 var(--space-3)`，`border-left: 3px`

- [ ] **Step 3: A1 — 段落节奏**

修改 `.rrv-paragraph`（当前 line 276）：
```css
.rrv-paragraph {
  margin: 0 0 var(--space-3);
  font-size: 14px;
  color: var(--color-text-primary);
  line-height: 1.8;
}
```
旧值：`margin: 0 0 var(--space-2-5);`

- [ ] **Step 4: A3 — 引用标记可读性与交互稳定性**

修改 `.rrv-citation-marker`（当前 lines 286-300）：
```css
.rrv-citation-marker {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  vertical-align: middle;
  position: relative;
  top: -1px;
  margin: 0 3px;
  padding: 1px 6px;
  border: 1px solid var(--color-accent);
  border-radius: 3px;
  background: var(--color-accent-light);
  color: var(--color-accent);
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  transition: all var(--transition-base);
}
```

旧值差异：
- `display: inline` → `inline-flex`，新增 `align-items: center; justify-content: center;`
- `vertical-align: super` → `middle`
- 新增 `position: relative; top: -1px;`
- `margin: 0 var(--space-0-25)` → `0 3px`
- `padding: var(--space-0-25) 5px` → `1px 6px`
- `border-radius: var(--radius-sm)` → `3px`
- `font-size: 11px` → `12px`
- 删除 `line-height: 1;`

在 `.rrv-citation-marker:hover` 之前（当前 line 301 前）插入伪元素命中区：
```css
.rrv-citation-marker::before {
  content: '';
  position: absolute;
  inset: -4px -2px;
}
```

- [ ] **Step 5: 确认 hover / focus-visible / active 状态不动**

Lines 302-317（`.rrv-citation-marker:hover`、`.rrv-citation-marker:focus-visible`、`.rrv-citation-marker--active`）保持原样，不修改。

- [ ] **Step 6: 运行现有测试确认不回归**

```bash
cd apps/frontend && npx vitest run src/__tests__/research-result-page.test.ts
```
预期：全部 PASS。

- [ ] **Step 7: Type-check**

```bash
cd apps/frontend && npx vue-tsc --noEmit
```
预期：零错误。

- [ ] **Step 8: 提交**

```bash
git add apps/frontend/src/components/research/result/ResearchReportViewer.vue
git commit -m "style: optimize ResearchReportViewer typography — line width, section anchors, paragraph rhythm, citation markers

- A4: max-width 680px + padding-inline for narrow viewport
- A2: section heading 17px, border-left 4px, margin-top 16px
- A1: paragraph margin-bottom var(--space-3)
- A3: inline-flex baseline alignment, ::before hit area, no vertical-align:super"
```

---

## 验证清单

- [ ] 1280×800 桌面视口：报告正文居中 680px 栏，左右留白，段落/节间距舒适
- [ ] 375×812 移动视口：报告正文有左右 padding 不贴边
- [ ] 200% zoom：引用标记可辨读、可点击，不重叠
- [ ] 键盘 Tab 到引用标记 → Enter/Space 选中，focus-visible 样式正常
- [ ] 点击引用标记 → CitationPanel 同步高亮对应条目
- [ ] 引用标记 [1][2] 紧邻时点击不误触发
- [ ] 所有 88 条 E2E 通过（仅影响报告正文视觉，无逻辑变更）
