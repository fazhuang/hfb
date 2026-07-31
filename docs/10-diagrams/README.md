# 10 — Diagrams

Mermaid 唯一来源。所有图表统一用 Mermaid 编写，禁止其他格式。

---

> **状态:** Draft
> **版本:** v0.1.0
> **日期:** 2026-06-24
> **作者:** —
> **负责人:** —

## 目录

- [1. 原则](#1-原则)
- [2. 图表类型](#2-图表类型)
- [3. 命名规范](#3-命名规范)
- [4. 样式约束](#4-样式约束)
- [5. 引用方式](#5-引用方式)
- [6. 工具](#6-工具)

## 1. 原则

1. **唯一格式** — 所有图表使用 Mermaid（`.mmd`），禁止 `.drawio`、`.puml`、`.vsdx`、图片截图等任何其他格式
2. **文本优先** — Mermaid 是纯文本，可 diff、可 grep、可 code review
3. **与文档同仓** — 图表源文件存放在 `src/`，与引用它的文档同仓库，不做外链
4. **命名统一** — 按照 §3 命名规范，一眼看出图表所属领域和类型

## 2. 图表类型

| 类型             | Mermaid 语法                | 用途                         |
| ---------------- | --------------------------- | ---------------------------- |
| **Architecture** | `graph TD` / `flowchart LR` | 系统架构、组件拓扑、部署视图 |
| **RoadMap**      | `gantt`                     | 路线图、里程碑、发布计划     |
| **ER**           | `erDiagram`                 | 实体关系图、数据模型         |
| **Sequence**     | `sequenceDiagram`           | 时序图、API 调用链、数据流   |
| **State**        | `stateDiagram-v2`           | 状态机、生命周期、工作流     |
| **Class**        | `classDiagram`              | 类图、接口关系、类型层级     |
| **Graph**        | `graph` / `flowchart`       | 决策树、流程图、依赖图       |
| **Pie**          | `pie`                       | 占比分布、资源分配           |
| **Timeline**     | `timeline`                  | 事件时间线                   |
| **Mindmap**      | `mindmap`                   | 脑图、知识结构               |

## 3. 命名规范

```
{domain}-{type}-{description}.mmd
```

| 组成部分      | 说明                                                        | 示例              |
| ------------- | ----------------------------------------------------------- | ----------------- |
| `domain`      | 所属领域：`architecture`、`data`、`product`、`ai`、`sprint` | `architecture`    |
| `type`        | 图表类型（见 §2 表）                                        | `c4-context`      |
| `description` | 简短描述，小写英文，连字符分隔                              | `system-topology` |

### 示例

```
src/architecture-c4-context-system-topology.mmd
src/architecture-sequence-login-flow.mmd
src/product-gantt-roadmap.mmd
src/data-er-core-entities.mmd
src/data-state-order-lifecycle.mmd
src/ai-flow-prompt-pipeline.mmd
src/sprint-gantt-release-plan.mmd
src/ui-graph-navigation-map.mmd
```

## 4. 样式约束

所有 Mermaid 图表在文件头部包含统一配置：

```mermaid
%%{init: {'theme': 'neutral', 'themeVariables': { 'fontFamily': 'system-ui' }}}%%
```

- **主题** — `neutral`，禁止 `dark` 主题（Markdown 渲染不可控）
- **字体** — `system-ui`，不做自定义字体
- **方向** — Architecture / ER / Graph 默认 `LR`（左到右）；Sequence / State 默认 `TD`（上到下）
- **文字** — 节点文字用双引号包裹：`A["用户服务"]`
- **颜色** — 非必要不使用自定义颜色；如需使用，只用 `neutral` 主题内置色板不自行定义 hex
- **节点 ID** — 用语义化 ID：`A` → `userService`，`B` → `orderDB`

## 5. 引用方式

### 在文档中内嵌

````markdown
\```mermaid
%%{init: {'theme': 'neutral'}}%%
graph LR
A["用户"] --> B["API Gateway"]
\```
````

### 引用外部文件

```markdown
![系统拓扑](../10-diagrams/src/architecture-c4-context-system-topology.mmd)
```

优先使用内嵌方式（阅读时直接渲染）。仅当图表被多份文档引用时，才存为 `.mmd` 文件，各文档引用它。

## 6. 工具

| 场景     | 工具                                                             |
| -------- | ---------------------------------------------------------------- |
| 本地预览 | VS Code + Mermaid Preview 插件                                   |
| 在线调试 | [Mermaid Live Editor](https://mermaid.live)（访问于 2026-06-24） |
| CI 检测  | `mermaid-cli` 或 `mermaid-lint`                                  |

## Changelog

| 版本   | 日期       | 变更                                                                  |
| ------ | ---------- | --------------------------------------------------------------------- |
| v0.2.0 | 2026-06-25 | 新增关联目录与MVP约束章节                                             |
| v0.1.0 | 2026-06-24 | 初稿 — 统一 Mermaid，定义 10 种图表类型、命名规范、样式约束、引用方式 |

---

## 关联目录

| 目录                                                               | 关系         | 说明                                  |
| ------------------------------------------------------------------ | ------------ | ------------------------------------- |
| [docs/02-architecture/](../02-architecture/)                       | 架构图消费方 | 系统架构图、部署拓扑图用于技术白皮书  |
| [docs/03-data/](../03-data/)                                       | 数据图消费方 | ER 图用于 Entity、Relation 规范       |
| [docs/17-Platform-Specifications/](../17-Platform-Specifications/) | 产品图依据   | 产品甘特路线图以 HFB-PS-1709 MVP 为准 |
| [docs/01-product/](../01-product/)                                 | 产品图消费方 | 路线图用于产品规划                    |

## MVP 图表边界

依据 [HFB-PS-1709](../17-Platform-Specifications/1709_MVP_Implementation_Specification.md)：

- MVP 阶段图表聚焦于：系统架构、核心 ER、决策流程、产品路线图
- Post-MVP 图表（如 GraphRAG 推理路径、Multi-Agent 协作图）延后制作
