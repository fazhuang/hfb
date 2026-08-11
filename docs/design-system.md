# HFB — 皇甫谧数字人文平台

> Category: Humanities & Digital Scholarship
> 学术气质数字人文。沉静蓝调，中西合璧，信息密集而有序。

## 1. Visual Theme & Atmosphere

皇甫谧数字人文平台服务于中医古籍研究——这是一个需要沉静、专注、长时间凝视界面的场景。视觉语言借鉴宋代版刻的温润与秩序感：不是冷漠的极简，而是带着纸墨温度的功能主义。

页面底色 `#F7FAFC` 微偏蓝灰——不是纯白，类似冷调宣纸，比纯白阅读更舒适。主文字色 `#1A365D` 为深蓝墨色，有汉砖碑刻的沉厚感，比纯黑温暖。主色 `#2B6CB0` 取自青金石颜料，克制使用——一个屏幕内红色元素不超过一处：强调操作按钮、选中态、链接。

**核心特征：**
- 4px 基础栅格，24 级间距体系（1px–80px）——信息密集型页面需要精密间距控制
- 文字层级从 11px（标签）到 22px（页面标题），无巨大 display——学术工具不需要喊叫
- 中文优先字体栈，正文 14px 起步——中文笔画密度高，尺寸不能太小
- 圆角克制：卡片 10–12px，按钮 8px，无 9999px pill——学术气质拒绝装饰性圆角
- 浅色/深色双主题完整覆盖，切换通过 `html.dark` 类或 `data-theme` 属性
- 阴影仅两层：默认 `0 2px 8px rgba(0,0,0,0.04)`，hover 浮起 `0 4px 16px rgba(0,0,0,0.08)`——学术工具不需要花哨深度
- Accent 色每次仅用于操作元素，不做纯装饰
- 支持焦点可见性（focus-visible 3px blue ring），满足 WCAG 基础要求

**视觉关键词：** 沉静 / 温润 / 克制 / 秩序 / 纸墨感 / 青金石蓝

## 2. Color Palette & Roles

### 浅色主题 (Light)

| Token | Value | 用途 |
|-------|-------|------|
| `--color-page-bg` | `#F7FAFC` | 页面底色——微蓝灰宣纸色 |
| `--color-surface` | `#FFFFFF` | 卡片、模态框、表格背景 |
| `--color-text-primary` | `#1A365D` | 主文字、标题——深蓝墨色 |
| `--color-text-secondary` | `#4A5568` | 次要文字、描述 |
| `--color-text-muted` | `#A0AEC0` | 辅助信息、占位符 |
| `--color-border` | `#E2E8F0` | 卡片边框、分割线 |
| `--color-hover` | `#EDF2F7` | 表格行 hover、列表 hover |
| `--color-active` | `#EBF8FF` | 选中态底色 |
| `--color-accent` | `#2B6CB0` | 主色——按钮、链接、选中 |
| `--color-accent-hover` | `#1A4F8A` | 主色 hover 态 |
| `--color-accent-light` | `#EBF8FF` | 主色浅底——tag 背景、高亮区 |
| `--color-navbar-bg` | `#FFFFFF` | 导航栏底色 |
| `--color-footer-bg` | `#F8FAFC` | 页脚底色 |

### 语义色 (Light)

| Token | 色值 | 用途 |
|-------|------|------|
| `--color-success` | `#68D391` | 成功图标 |
| `--color-success-text` | `#276749` | 成功文字 |
| `--color-success-bg` | `#F0FFF4` | 成功底色 |
| `--color-warning` | `#D69E2E` | 警告图标 |
| `--color-warning-text` | `#975A16` | 警告文字 |
| `--color-warning-bg` | `#FFFFF0` | 警告底色 |
| `--color-error` | `#FC8181` | 错误图标 |
| `--color-error-text` | `#C53030` | 错误文字 |
| `--color-error-bg` | `#FFF5F5` | 错误底色 |
| `--color-info` | `#3182CE` | 信息图标 |
| `--color-info-text` | `#2C5282` | 信息文字 |
| `--color-info-bg` | `#EBF8FF` | 信息底色 |

### 深色主题 (Dark)

| Token | 值 | 用途 |
|-------|----|------|
| `--color-page-bg` | `#1A202C` | 页面底色——类石墨暗灰 |
| `--color-surface` | `#1A202C` | 卡片底色（与页面同色，靠边框区分） |
| `--color-text-primary` | `#E2E8F0` | 主文字 |
| `--color-text-secondary` | `#A0AEC0` | 次要文字 |
| `--color-text-muted` | `#718096` | 辅助信息 |
| `--color-border` | `#4A5568` | 边框 |
| `--color-hover` | `#2D3748` | Hover 态 |
| `--color-active` | `#2A4365` | 选中态 |
| `--color-accent` | `#63B3ED` | 主色——暗色下提亮 |
| `--color-navbar-bg` | `#1A202C` | 导航栏 |
| `--color-footer-bg` | `#171923` | 页脚 |

### Shadow & 深度

- **Card shadow (level 1)**：`0 2px 8px rgba(0,0,0,0.04)` — 默认轻微浮起
- **Card hover (level 2)**：`0 4px 16px rgba(0,0,0,0.08)` — hover 明显浮起
- **Dropdown/Dialog**：`0 8px 24px rgba(0,0,0,0.08)` — 浮层
- **Accent focus ring**：`0 0 0 3px rgba(66,153,225,0.15)` — 焦点环
- **Modal overlay**：`rgba(0,0,0,0.4)` — 遮罩
- 深色主题阴影：`0 2px 8px rgba(0,0,0,0.25)` / `0 4px 16px rgba(0,0,0,0.4)` — 暗底需更深
- **哲学**：两层深度足够信息密集型页面。三层阴影用于浮层。不用多层阴影叠加、不用内阴影、不用玻璃拟态。

## 3. Typography Rules

### 字体栈
- **Sans（正文/UI）**：`-apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', 'Helvetica Neue', sans-serif`
  - PingFang SC 优先级高——macOS 上中文最优
  - Microsoft YaHei 为 Windows 回退
  - 14px 正文下中文字形清晰度满足长时间阅读
- **Mono（代码/数据）**：`'SF Mono', 'Fira Code', 'Fira Mono', 'Roboto Mono', monospace`

### 层级

| 角色 | 大小 | 字重 | 行高 | 用途 |
|------|------|------|------|------|
| Page Title | 24px | 700 | 1.3 | 页面主标题 |
| Section Title | 22px | 700 | 1.3 | 区域标题 |
| Card Title | 16px | 600 | 1.3 | 卡片标题 |
| Subtitle | 15px | 600 | 1.3 | 子标题 |
| Body | 14px | 400 | 1.5 | 正文 |
| Body Emphasis | 14px | 500 | 1.5 | 强调正文 |
| Small Body | 13px | 400 | 1.5 | 辅助正文 |
| Caption | 12px | 400–500 | 1.5 | 标签、元数据 |
| Micro | 11px | 400 | 1.5 | 极小标签、轴标记 |
| **KPI 大数字** | 24px | 700 | 1.2 | 仪表盘关键指标——tabular-nums |
| **表格文字** | 13px | 400 | 1.4 | 数据表格内容 |

### 排版原则
- **中文优先**：正文 14px 最小——中文笔画密度高，12px 阅读困难
- **粗体克制**：学术场景 700 仅用于最大的两个尺寸，其余用 400–600
- **tabular-nums**：所有数字指标使用等宽数字，保证扫描对齐
- **无负 letter-spacing**：中文不适用（不同于西文 display 尺寸）
- **行高策略**：标题 1.3（紧凑），正文 1.5（舒适阅读），表格 1.4

## 4. Component Stylings

### 按钮 (Buttons)

**Primary（实心主色）**
- 背景：`var(--color-accent)` #2B6CB0，文字：#FFFFFF
- 内边距：sm 6×16 / md 8×20 / lg 10×24
- 圆角：`var(--radius-lg)` 8px
- 字体：13–14px，weight 600
- Hover：`var(--color-accent-hover)` #1A4F8A
- 用途：主 CTA、表单提交

**Secondary（描边次要）**
- 背景：transparent，边框：`var(--color-border)` 1px solid，文字：`var(--color-text-secondary)`
- 同尺寸/圆角
- Hover：`var(--color-hover)` 底色
- 用途：次要操作、取消

**Ghost（无边框）**
- 背景：transparent，文字：`var(--color-accent)`
- Hover：`var(--color-accent-light)` 底色 + 下划线
- 用途：表格内操作、链接式按钮

**Disabled**
- 背景：`#E2E8F0`，文字：`#A0AEC0`，光标：not-allowed

### 卡片 (Cards)

- 背景：`var(--color-surface)` / `var(--color-navbar-bg)`
- 边框：`1px solid var(--color-border)`
- 圆角：`var(--radius-xl)` 10px（默认），`var(--radius-2xl)` 12px（特色卡片）
- 阴影：`var(--shadow-card-sm)` — `0 2px 8px rgba(0,0,0,0.04)`
- Hover：`var(--shadow-card-hover)` — `0 4px 16px rgba(0,0,0,0.08)` + translateY(-1px)
- 内边距：16–20px
- **哲学**：卡片使用可见边框 + 极轻阴影，确保在 `#F7FAFC` 底色上边界清晰

### 输入框 (Inputs)

- 背景：`var(--color-page-bg)` — 输入区比卡片底色略深，形成内凹感
- 边框：`1px solid var(--color-border)`
- 圆角：`var(--radius-md)` 6px 或 `var(--radius-lg)` 8px
- 内边距：8px 12px（垂直/水平）
- Focus：`var(--focus-ring)` — `0 0 0 3px rgba(66,153,225,0.15)` + accent 色 border
- Placeholder：`var(--color-text-muted)`

### 表格 (Tables)

- 头部：`var(--color-hover)` 底色，weight 500–600，12–13px
- 行：`var(--color-surface)` 底色，hover 到 `var(--color-hover)`
- 单元格内边距：10px 12px
- 边框：`1px solid var(--color-border)` 水平分割线，无竖线
- 斑马纹：可选，用 `var(--color-page-bg)` 间隔——学术数据表格默认开启
- 文字：13px weight 400

### 标签/Badge

- **Neutral tag**：`var(--color-tag-bg)` / `#EDF2F7` 背景，`var(--color-text-secondary)` 文字
- **Accent tag**：`var(--color-accent-light)` 背景，`var(--color-accent)` 文字
- **Success/Warning/Error/Info tag**：各自 bg + text token
- 圆角：`var(--radius-sm)` 4px — tag 不做 pill 圆角
- 内边距：2px 8px，字体 11–12px

### 导航 (Navigation)

- **侧边栏**：240px 固定宽，`var(--color-navbar-bg)` 底色，右侧 `1px solid var(--color-border)` 分割
- **顶栏**：56px 高，sticky，`var(--color-navbar-bg)`，底部 1px border
- **链接**：14px weight 500，`var(--color-text-secondary)` 默认，`var(--color-accent)` active/hover
- **Active 态**：侧边栏链接 active 加 `var(--color-accent-light)` 左边框 3px + accent 色文字
- 移动端侧边栏变 overlay + 遮罩，escape/点击关闭

### 对话框 (Dialog/Modal)

- 背景：`var(--color-surface)`，border：`1px solid var(--color-border)`
- 圆角：`var(--radius-2xl)` 12px，阴影：`var(--shadow-dropdown)` `0 8px 24px rgba(0,0,0,0.08)`
- 遮罩：`var(--color-overlay)` `rgba(0,0,0,0.4)`
- 宽度：max 480px（小对话框），max 640px（确认/表单对话框）

### 吐司 (Toast)

- 右下方弹出，`var(--shadow-toast)` `0 4px 12px rgba(0,0,0,0.15)`
- 圆角：`var(--radius-lg)` 8px，动画：fade-in + slide-up
- 四种语义色变体：success / warning / error / info

### 图表 (Charts — inline SVG / CSS bar)

- **柱状图**：8px 高 bar，4px 圆角，`var(--color-accent)` 填充，`var(--color-page-bg)` 轨道
- **标签**：12px weight 400 `var(--color-text-muted)`
- **网格线**：可选，`var(--color-border)` 虚线
- 过渡动画：width 0.6s `cubic-bezier(0.22, 0.61, 0.36, 1)`
- 深色主题使用 `var(--color-border)` 替代 page-bg 做轨道

## 5. Layout Principles

### 间距系统
- **基础单位**：4px
- **尺度**：0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 14, 16, 18, 20, 24, 28, 32, 36, 40, 48, 60, 64, 80
- 小间距精密（1px 步进到 10px），中段 2–4px 步进，大间距翻倍——匹配信息密集页面的排版需求
- 组件内间距：8–16px，区域间间距：24–48px，页面分区：48–64px

### 网格 & 容器
- 最大内容宽度：1200px（桌面），1000px（dashboard / 内容页）
- 侧边栏：240px 固定 + 主内容 flex 剩余
- KPI 卡片：auto-fill, minmax(150px, 1fr) — 3–6 列自适应
- 图表区域：`grid-template-columns: 1fr 1fr`（桌面），`1fr`（平板）
- 信息卡片：`grid-template-columns: repeat(auto-fill, minmax(200px, 1fr))` — 2–4 列

### 留白哲学
- **信息密度优先**：学术工具页面内容密集，不追求大块留白。用间距代替代替视觉分割。
- **分区靠间距，不靠分割线**：页面大区块间用 48–64px 间距自然分隔，只在语义无关的顶级区块间使用 border-top
- **卡片呼吸感**：卡片内部的 padding（16–20px）大于卡片间距（12–14px），内容在卡片内有呼吸空间
- **表格紧凑**：单元格 padding 10px 12px——中国古籍信息密度高，不需要欧美 SaaS 的 16px 单元格

### 圆角尺度
- `2px` (xs)：极小元素
- `4px` (sm)：tag、小按钮
- `6px` (md)：输入框、下拉
- `8px` (lg)：按钮、小卡片
- `10px` (xl)：标准卡片
- `12px` (2xl)：大卡片、对话框、特色区域
- `16px` (3xl)：超大面板
- `9999px` (full)：进度条、头像——仅此两处
- **无 pill 形状按钮/标签**：保持学术严肃性

## 6. Depth & Elevation

学术工具用尽可能少的深度层级——两到三层足以：

| 层级 | 处理 | 用途 |
|------|------|------|
| Flat (0) | 无阴影、无边框 | 页面底色 |
| Card (1) | `0 2px 8px rgba(0,0,0,0.04)` + `1px solid var(--color-border)` | 卡片、面板 |
| Hover (2) | `0 4px 16px rgba(0,0,0,0.08)` + translateY(-1px) | 卡片 hover 浮起 |
| Dropdown/Dialog (3) | `0 8px 24px rgba(0,0,0,0.08)` | 浮层、对话框 |
| Modal Overlay | `rgba(0,0,0,0.4)` | 遮罩 |
| Focus Ring | `0 0 0 3px rgba(66,153,225,0.15)` | 键盘焦点 |

**关键原则**：卡片必须同时有 border + shadow——浅色背景下仅靠阴影边界不清晰。

## 7. Responsive Behavior

| 断点 | 宽度 | 变化 |
|------|------|------|
| Phone | < 640px | 单列，侧边栏变 overlay，卡片堆叠 |
| Tablet | 640–768px | 2 列卡片网格，侧边栏 overlay |
| Tablet Wide | 768–1024px | 侧边栏折叠到 64px 图标态 |
| Desktop | 1024–1440px | 完整布局：240px 侧边栏 + 内容区 |
| Large | > 1440px | 居中，max-width 1200px |

- 移动端侧边栏：fixed overlay + backdrop，toggle 按钮，escape 关闭
- 图表：2 列变 1 列 < 768px
- KPI 卡片：3 列变 2 列 < 768px，变 1 列 < 480px
- 表格：水平滚动 < 768px
- 间距：desktop 48–64px → tablet 32px → phone 24px

## 8. Do's and Don'ts

### ✅ Do
- 用 CSS Design Token（`--color-*`、`--space-*`），绝无硬编码 Hex
- 一个屏幕最多一个 accent 色操作元素（主 CTA）
- 卡片 = border + shadow 双重标记边界
- 中文正文 14px 起步，12px 仅用于标签
- 数字使用 tabular-nums 保证对齐
- 表格默认斑马纹辅助扫描
- 浅/深双主题必须都测试
- 动画用 `transition-base` 0.15s ease-out——快速但不突兀
- 学术数据密集页面用表格/列表，不强行卡片化

### ❌ Don't
- 不用纯黑 `#000` 或纯白 `#FFF` 做背景
- 不用渐变（例外：accent → accent-80% 仅 hero 可选，但不推荐）
- 不用玻璃拟态、无内阴影、无多层投影
- 不用 pill 形按钮或 tag
- 不用装饰性动画——学术场景不需要
- 不引入第三方 UI 库的视觉风格混搭
- 不用 accent 色做纯装饰——只在可操作元素上出现
- 不用负 letter-spacing——中文不适用
- 不用 weight 300 极细字体——中文字形不适用

## 9. Dark Theme Behavior

- 切换通过 `html.dark` class 或 `data-theme="dark"` 属性
- 存储到 localStorage key `hfb-theme`
- 支持三态：light / dark / auto（跟随系统 `prefers-color-scheme`）
- 深色主题的 accent 色自动提亮——`#2B6CB0` → `#63B3ED`
- 阴影在深色下加深——`rgba(0,0,0,0.04)` → `rgba(0,0,0,0.25)`
- 深色下卡片与页面同色，依赖 border 区分
- 过渡动画：`background 0.25s ease, color 0.25s ease`

## 10. Agent Prompt Guide

### 快速色彩参考
- 主 CTA：`#2B6CB0`（accent）文字 `#FFFFFF`
- 页面底色：`#F7FAFC`（冷调宣纸）
- 卡片底色：`#FFFFFF`
- 主文字：`#1A365D`（深蓝墨）
- 次文字：`#4A5568`
- 边框：`#E2E8F0`
- Hover 底色：`#EDF2F7`
- 链接/选中：`#2B6CB0` + `#EBF8FF` 浅底

### 组件 Prompt 示例

**仪表盘 KPI 卡片：**
"Create a stat card: white background, 1px solid #E2E8F0 border, 10px radius, box-shadow 0 2px 8px rgba(0,0,0,0.04). Inside: icon 44×44px with #EBF8FF bg and 8px radius, followed by number at 24px weight 700 tabular-nums #1A365D, label below at 13px #4A5568. Hover: shadow 0 4px 16px rgba(0,0,0,0.08) + translateY(-1px)."

**表格：**
"Build a data table: header row #EDF2F7 bg, 13px weight 600 #1A365D. Body rows #FFFFFF bg alternating with #F7FAFC (zebra). Cell padding 10px 12px, 13px weight 400 #4A5568. Horizontal border 1px solid #E2E8F0 between rows only, no vertical borders. Row hover: #EDF2F7 bg."

**侧边栏导航：**
"Fixed left sidebar: 240px, #FFFFFF bg, right border 1px solid #E2E8F0. Top: brand area with icon 32px + text 18px weight 700 #1A365D. Nav links: 14px weight 500 #4A5568, padding 10px 16px, 6px radius. Active link: #EBF8FF bg, #2B6CB0 text, 3px solid #2B6CB0 left border accent."

**图表：**
"Horizontal bar chart: each bar row is grid(label 64px + track 1fr + 6 grid marks 32px each), gap 8px. Track: #F7FAFC bg, 8px height, 4px radius. Bar fill: #2B6CB0 accent, animates width 0.6s cubic-bezier(0.22,0.61,0.36,1). Label 12px #4A5568 right-aligned. Grid numbers 11px #A0AEC0."

**研究活动列表：**
"Activity list: each item = icon 32×32px rounded 6px in category-colored bg + title 14px #1A365D + subtitle 12px #A0AEC0 + timestamp 12px #A0AEC0. Layout: flex row, gap 16px, padding 10px 12px. Border-bottom 1px solid #E2E8F0 between items. Hover: #EDF2F7 bg."

### 迭代指南
1. 先确认颜色均来自 DESIGN.md 行色 token——不要凭空发明 hex
2. 中文中文面 14px 最小正文字号，12px 仅用于标签和元数据
3. 一个屏幕内 accent 色出现不超过 3 处
4. 卡片 = border + shadow，缺一不可
5. 信息密集页面优先表格/列表排版，不强行卡片化
6. 每次生成后自检浅色/深色双主题
7. 分隔优先用间距（48–64px），不用分割线
8. 动画快速（0.15s），不拖沓
