# Research Result Reader — 阅读体验优化

> 日期：2026-08-04 | 范围：`ResearchReportViewer.vue` `<style scoped>` 仅

## 动机

`ResearchResultPage` 作为 Reader，首要任务是让用户持续、轻松地读懂报告。当前报告正文排版存在四个问题：行宽过宽（约 68 字/行）、章节层级不分明、段落间距密、引用标记上标跳跃且触控目标偏小。

## 设计

### A4 — 阅读栏宽度收敛

```css
.rrv-report {
  max-width: 680px;
  margin-inline: auto;
  padding-inline: var(--space-4);
}
```

14px 字号、680px 宽 = 约 48 字/行，落在中文阅读舒适区（25-45 字/行）上限。保持页面 960px 框架，仅报告正文区域收窄。下方 CitationPanel 双栏布局不受影响。

`padding-inline: var(--space-4)` 防止 375px 窄屏下文字贴边。

### A2 — 章节层级与扫读锚点

| 属性 | 当前 | 改后 |
|------|------|------|
| `.rrv-section-block` margin-bottom | `20px` | `32px` |
| `.rrv-section-heading` font-size | `16px` | `17px` |
| `.rrv-section-heading` border-left | `3px` | `4px` |
| `.rrv-section-heading` margin-top | `0` | `16px` |

节标题在滚动中形成清晰的"停顿点"，不改现有设计语言。

使用 `margin-top: 16px` 而非 `padding-top`，避免左侧 `border-left` 竖线向上拉长变形。

### A1 — 段落节奏

| 属性 | 当前 | 改后 |
|------|------|------|
| `.rrv-paragraph` margin-bottom | `var(--space-2-5)` | `var(--space-3)` |

段间距从约 10-12px 增至约 14px，相对于 14px 字号、1.8 行高（每行约 25px），视觉分隔清晰但不夸张。

### A3 — 引用标记可读性与交互稳定性

| 属性 | 当前 | 改后 |
|------|------|------|
| `display` | `inline` | `inline-flex` |
| `align-items` | — | `center` |
| `justify-content` | — | `center` |
| `vertical-align` | `super` | `middle` |
| `position` | — | `relative` |
| `top` | — | `-1px` |
| `font-size` | `11px` | `12px` |
| `padding` | `var(--space-0-25) 5px` | `1px 6px` |
| `margin` | `0 var(--space-0-25)` | `0 3px` |
| `border-radius` | `var(--radius-sm)` | `3px` |

`inline-flex` + `vertical-align: middle` 替代原 `display: inline`，保证 `<button>` 在 WebKit / Blink / Gecko 上垂直居中和基线对齐行为一致。

新增伪元素命中区扩展（仅垂直方向，保持相邻标记水平不重叠）：

```css
.rrv-citation-marker::before {
  content: '';
  position: absolute;
  inset: -4px -2px;
}
```

相邻引用标记间距 = 2 × 3px margin = 6px 真实物理间隙。两侧 ::before 各向外水平扩展 2px（总计 4px），在 6px 间隙中不重叠。垂直各扩展 4px 用于增大上下触控容错。父级无 overflow 裁切。

hover / focus-visible / active 状态不变。

### 不动

- 页面 960px 框架
- CitationPanel `.rcp-body` 双栏 layout
- 字号 14px、行高 1.8
- 所有 `v-if` / `v-else` 状态守卫、composable、路由逻辑
- Citation → Evidence → SourceRef trace_id / passage_id 绑定
- 键盘焦点、选中状态、aria-label、role 语义

### 跳过

- Sticky header、节间横线、首行缩进、drop cap
- 全局页面宽度调整
- 字号 / 行高 / 颜色 / token 系统变更
- 后端、路由、RBAC、V4 API、Workspace、Knowledge Explorer

## 约束

- 白名单：`pages/research/` + `components/research/result/` 直接展示组件
- 禁止后端、持久化、路由、RBAC、V4 API、Workspace、Knowledge Explorer
- Citation 选择与 Evidence / SourceRef 的 trace_id / passage_id 绑定保持
- 375×812、1280×800、200% zoom 通过
- 无直接 hex、无新增 any
- 单原子提交，不推送，不改历史
