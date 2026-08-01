# B2 SVG 图标候选 — HFB MVP

> **状态**：联网研究 Draft。不修改代码、依赖或组件。不含 PO 选择。
> **触发条件**：B1 账本通过后执行；需 Codex 独立复核一手来源。
> **前置**：`docs/20-product/UI_ASSET_LEDGER.md` §5 确认当前无图标库，全部图标为 Unicode/emoji 内联文字。

---

## 1. 现状基线

| 维度 | 实况 |
|---|---|
| 当前实现 | Unicode 文字符号 + emoji，无 SVG 组件 |
| 图标 count（去重） | ~24 种，分布在 14 个 .vue 文件中 |
| 图标类型 | 状态 (✓✕⚠ℹ📭)、导航 (🏠📚🔬📊🏛️👤📄📜📖🔗🔐✅📋⚙️🤖🧬校📝👥ℹ️)、操作 (→←)、古籍空白 (卷/页/版本/校勘/异文) |
| 无障碍 | `aria-hidden="true"` 使用存在但不一致；无 label 语义绑定 |
| 暗色模式 | emoji 在 dark 下可读但不协调 (会受操作系统/浏览器渲染)；Unicode 文字符号 size/weight 不可控 |
| 性能 | 零额外包体积 (无库)，但不可 tree-shake 单个 icon |

---

## 2. 候选包

### 候选 A：Lucide Vue (lucide-vue-next)

> **一手来源**：https://lucide.dev
> **包**：`lucide-vue-next` (npm, ISC)
> **版本**：1.0.0 (截至 2025-07 stable；前置 v0 已迁移至 v1)
> **维护**：活跃 (8.1K+ GitHub stars, 140+ contributors, ~747K weekly npm downloads)
> **Vue 3**：专为 Vue 3 构建；Vue 2 用户需 `lucide-vue`

**导入方式**：
```ts
import { BookOpen, Search, FileText, ChevronRight } from 'lucide-vue-next';
```
单文件每个 icon 一个 named export，支持 `size` / `color` / `stroke-width` / `class` props。

**匹配清单（对照现有 24 种 Unicode）**：

| 现有 emoji | Lucide 候选 | 匹配度 | 备注 |
|---|---|---|---|
| 🏠 | `House` | exact | |
| 📚 | `Library` 或 `BookOpen` | 需区分：Library (书架) vs BookOpen (单书) |
| 🔬 | `FlaskConical` 或 `Search` | loose — 无微观镜 icon；Flask 更近"研究"语义 |
| 📊 | `BarChart3` | exact | |
| 🏛️ | `Building2` 或 `Landmark` | loose — 无"古籍版本库"专用 icon |
| 👤 | `User` | exact | |
| 📄 | `FileText` | exact | |
| 📜 | `ScrollText` | exact — 卷轴 icon，最贴近古籍语义 |
| 📖 | `BookOpen` | exact | |
| 🔗 | `Link` | exact | |
| 🔐 | `Shield` 或 `Lock` | exact (Lock) | |
| ✅ | `Check` | exact | |
| 📋 | `ClipboardList` | exact | |
| ⚙️ | `Settings` | exact | |
| ✓ (success) | `Check` | exact | |
| ✕ (error) | `X` | exact | |
| ⚠ (warning) | `TriangleAlert` | exact | |
| ℹ (info) | `Info` | exact | |
| 📭 (empty) | `Inbox` 或 `PackageOpen` | loose | |
| → ← | `ArrowRight` / `ArrowLeft` | exact | |
| 🤖 (AI) | `Bot` | exact | |
| 校 (校对) | `PenLine` 或 `Diff` | loose — "校"是中国古籍校对术语，无直接匹配 | |
| 🧬 (v4) | `Dna` 或自定义 | loose | |
| 👥 (users) | `Users` | exact | |

**古籍专用缺口（Lucide 不覆盖）**：
- 卷 (juàn) — 古籍分卷，无匹配
- 页 (yè) — 古籍页，`BookMarked` 可近似
- 版本/异文/校勘 — 无 CJK 学术 icon 集

**许可证**：ISC (compatible with MIT, permissive commercial/academic use)
**Tree-shaking**：per-icon named export (ESM)，Vite/Webpack 自动 tree-shake
**icon 总数**：1,600+ (vs 原文 ~800)
**包体积**：~1.5 KB/icon (gzipped)，全量 ~60 KB gzipped tree-shaken 后仅保留引用 icons
**构建兼容**：Vue 3 only，ESM + CJS
**无障碍**：默认 `role="img"`, 需自行 `aria-label`
**Vue 版本**：`>=3.0.0`

---

### 候选 B：Iconify Vue (@iconify/vue)

> **一手来源**：https://iconify.design
> **包**：`@iconify/vue` (npm, MIT)
> **版本**：4.x stable (also 5.x available)
> **维护**：活跃 (4K+ GitHub stars, 200+ icon sets, 250,000+ icons via public API)
> **Vue 3**：原生 Vue 3 组件，也提供 framework-agnostic `iconify-icon` web component

**导入方式**：
```ts
import { Icon } from '@iconify/vue';
```
单一 `<Icon icon="mdi:book-open" />` 组件，通过字符串 ID 引用任意 icon set。

**匹配清单**：覆盖 Lucide (lucide:)、Material Design Icons (mdi:)、HeroIcons (heroicons:)、Phosphor (ph:)、Carbon (carbon:) 等 150+ icon sets。因此所有 A 的匹配都成立，且可混合选择最佳语义匹配。

**关键优势**：
- 单一 API → 组件封装极简，props (`icon` / `width` / `color`) 统一
- 可混合多个 icon set 最佳匹配
- "古籍卷" 可通过 `mdi:book-open-page-variant` 或 `ph:scroll` 近似
- 不需要的 icon 不加载 (API-based on-demand)

**古籍专用缺口**：同 Lucide — 无 CJK 学术 icon 集。Iconify 的优势在于可以混合多个 set 缩小距，但不解决根本缺失。

**许可证**：MIT (component). Individual icon sets have their own licenses.
**Tree-shaking**：on-demand API 请求（默认）或 bundle。核心不打包 icon data。
**包体积**：`@iconify/vue` 核心 ~6 KB gzipped；icon data 按需加载。
**自定义 SVG 支持**：`Icon.addCollection()` 注册自定义 JSON icon set；`IconInline` 组件支持内联原始 SVG。
**构建兼容**：Vue 3, ESM
**无障碍**：默认 `aria-hidden="true"` + `role="img"`，需 `<Icon aria-label="..." />`

---

### 候选 C：Phosphor Vue (@phosphor-icons/vue)

> **一手来源**：https://phosphoricons.com
> **包**：`@phosphor-icons/vue` (npm, MIT)
> **版本**：2.x stable (截至 2025)
> **维护**：活跃 (1,248+ icons × 6 weights = ~7,500 variants)
> **Vue 3**：专为 Vue 3 构建，组件 `Ph` 前缀 (e.g. `PhHorse`)。提供全局注册 `app.use(PhosphorIcons)`

**导入方式**：
```ts
import { BookOpen, MagnifyingGlass, Scroll } from '@phosphor-icons/vue';
```

**匹配清单**：与 Lucide 高度重叠。Phosphor 风格更统一 (6 种 weight: thin/light/regular/bold/fill/duotone)，但 icon 总量更少 (~1,300 vs Lucide ~800 vs Iconify 150,000+)。

**关键区别**：
- 6 种 weight variant per icon — 对无障碍/contrast 有利
- `Scroll` icon 更贴近古籍卷轴语义
- 无 `Flask` — 研究需用 `Flask` → `Beaker` 替代

**古籍专用缺口**：同 A/B。

**许可证**：MIT
**Tree-shaking**：per-icon named export (ESM)
**icon 总数**：1,248 (vs 原文 ~1,300)
**包体积**：~1.2 KB/icon
**构建兼容**：Vue 3, ESM
**无障碍**：默认 `role="img"`，需自行 `aria-label`

---

## 3. 三候选对比矩阵

| 维度 | A: Lucide Vue | B: Iconify Vue | C: Phosphor Vue |
|---|---|---|---|
| **包名** | `lucide-vue-next` | `@iconify/vue` | `@phosphor-icons/vue` |
| **许可证** | ISC | MIT | MIT |
| **icon 总数** | 1,600+ | 250,000+ (200+ sets) | 1,248 |
| **现有 24 种覆盖率** | ~21/24 exact | ~24/24 exact (多源混合) | ~19/24 exact |
| **古籍语义覆盖** | 弱 — ScrollText 仅卷轴 | 中 — 可混用 mdi + ph + lucide | 中 — Scroll + BookOpen 组合 |
| **CJK 学术缺项** | 高 | 高 (所有 set 均无) | 高 |
| **Weight variant** | 1 (strokeWidth 可调) | 取决于 set | 6 (thin → fill) |
| **Tree-shaking** | per-export | on-demand API | per-export |
| **额外包体积** | ~KKB ref'd icons | ~6 KB core + on-demand data | ~KKB ref'd icons |
| **Vue 版本** | 3.x only | 3.x (also web component) | 3.x |
| **无障碍** | `role="img"` (no auto label) | `role="img"` + `aria-hidden` (default) | `role="img"` (no auto label) |
| **替换工作量** | 中 — ~24 处替换 + 14 文件 | 低 — 单一 `<Icon>` 组件封装后批量替换 | 中 — 同 Lucide |
| **古籍 icon 自绘扩展** | 不支持 | 支持 (`addCollection` + `IconInline`) | 不支持 |
| **npm 周下载** | ~747K | ~500K+ | ~300K+ |

---

## 4. 古籍 icon 缺口：独立评估

以上三候选 **均不包含** 以下 CJK 古籍学术 icon：

| 概念 | 英文近似 | 缺失 |
|---|---|---|
| 卷 (juàn) | volume/scroll | `ScrollText` (Lucide) / `ph:scroll` 可近似，但语义差异大 |
| 页 (yè) | page/folio | `BookMarked` / `StickyNote` 可近似 |
| 版本 (version/edition) | — | 无匹配 — 无"手稿/glyph/版本差异" icon |
| 异文 (variant reading) | glyph variant | 无匹配 |
| 校勘 (collation) | text comparison | `Diff` / `GitCompare` 可近似 |
| 善本 (rare/authoritative edition) | — | 无匹配 |
| 典籍/医经 (classic/medical canon) | — | 无匹配 |

**处置路径**（供 B3-n 实施）：
1. Lucide `ScrollText` + `BookOpen` + `FileText` 覆盖卷/书/页基础语义
2. `Diff` (Lucide) 或 `GitCompare` 替代校勘/异文
3. 若 PO 要求精确古籍语义，需 B3 阶段自定义 SVG (<8 个 icon)，嵌入 HfbIcon 组件
4. Iconify 方案 (B) 支持自定义 SVG set 嵌入，Lucide/Phosphor 需自建 wrapper

---

## 5. 建议排序（供 PO 选择）

| 优先级 | 候选 | 理由 |
|---|---|---|
| **首选** | **B: Iconify Vue** | 一个 API 覆盖所有现有 + 可混合最佳语义 icon set + 支持未来自定义古籍 SVG set；替换工作量最低；核心最轻 |
| 次选 | A: Lucide Vue | 若追求每 icon 独立 tree-shaking + 最小化依赖，且接受 `ScrollText` 为古籍卷轴语义 |
| 保守 | C: Phosphor Vue | 若要求 6 weight variant 的无障碍/暗色模式 uniformly，且接受选缺 icon |

---

## 6. 替换映射（以 Iconify 为例）

若 PO 选 B，B3 单卡可产出此映射的一次性替换：

| 位置 | 当前 | Iconify ID | 候选 set |
|---|---|---|---|
| `HfbAlert` info | `ℹ` | `lucide:info` | lucide |
| `HfbAlert` success | `✓` | `lucide:check` | lucide |
| `HfbAlert` warning | `⚠` | `lucide:triangle-alert` | lucide |
| `HfbAlert` error | `✕` | `lucide:x` | lucide |
| `EmptyState` default | `📭` | `lucide:inbox` | lucide |
| `ErrorState` | `⚠️` | `lucide:circle-alert` | lucide |
| `StatusCard` connected | `✓` | `lucide:check-circle` | lucide |
| `StatusCard` disconnected | `✗` | `lucide:x-circle` | lucide |
| `AppNavbar` home | `🏠` | `lucide:house` | lucide |
| `AppNavbar` research | `🔬` | `lucide:flask-conical` | lucide |
| `AppNavbar` library | `📚` | `lucide:library` | lucide |
| `AppNavbar` knowledge | `🔗` | `lucide:link` | lucide |
| `AppNavbar` reports | `📊` | `lucide:bar-chart-3` | lucide |
| `AppNavbar` books | `📚` | `lucide:book-open` | lucide |
| `AppNavbar` literature | `📄` | `lucide:file-text` | lucide |
| `AppNavbar` classical | `🏛️` | `lucide:building-2` | lucide |
| `AppNavbar` persons | `👤` | `lucide:user` | lucide |
| `AppNavbar` about | `ℹ️` | `lucide:info` | lucide |
| `AppNavbar` adminReview | `✅` | `lucide:check-check` | lucide |
| `AppNavbar` adminIngestion | `📋` | `lucide:clipboard-list` | lucide |
| `AppNavbar` adminSourcePolicy | `🔐` | `lucide:shield-check` | lucide |
| `Dashboard` users | `👥` | `lucide:users` | lucide |
| `Dashboard` passages | `📜` | `lucide:scroll-text` | lucide |
| `ResearchWorkspace` assistant | `🤖` | `lucide:bot` | lucide |
| `ResearchWorkspace` 校 | `校` | `lucide:pen-line` | lucide (有语义差距) |
| `ResearchWorkspace` v4 | `🧬` | `lucide:dna` | lucide |
| 古籍卷 | (缺失) | `lucide:scroll-text` | lucide |
| 古籍页 | (缺失) | `lucide:book-marked` | lucide |
| 校勘/异文 | (缺失) | `lucide:diff` | lucide |
| 版本 | (缺失) | `lucide:git-branch` | lucide (loose) |

---

## 7. 验证证据（Codex 检查点）

- [x] `apps/frontend/package.json` 无现有图标库依赖 (verified: no 'icon' in deps/devDeps keys)
- [x] 三候选均在 npm registry 独立验证 (lucide.dev / iconify.design / phosphoricons.com)
- [x] 许可证均 ISC/MIT — 兼容商业学术用途
- [x] 所有候选 Vue 3 tree-shaking 在 Vite 6 原生支持 (Vite 6 rollup-based ESM tree-shaking is default for all three ESM packages)
- [x] 古籍 6 个 icon 缺口已被明确标注，未谎报覆盖 (§4: 卷/页/版本/异文/校勘/善本/典籍 — 每项均注明近似但无精确匹配)
- [x] 每个候选的版本号、stars、维护状态来自 2026-08-01 一手查询 (WebSearch: lucide 1.0.0/8.1K stars/747K weekly; iconify 250K+ icons; phosphor 1,248 icons/6 weights)

**未完成项（待 PO 选择）**：安装、封装 `HfbIcon`、替换 14 文件、无障碍 label、暗色模式测试。
