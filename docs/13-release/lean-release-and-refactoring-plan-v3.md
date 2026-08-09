# 精益推进计划 v3（最终版）

**文档状态:** 已批准 (Approved)
**版本:** v3.0 (Final)
**适用基线:** `c7ddecc9b11f19fffb86c9afbcbf0ca8d7f1ea30` 及后续 Candidate

---

## 路线图概览

```
【Step 1: 入口规格与按钮定位】 ──► 【Step 2: 文本精度与 E2E 对齐】 ──► 【Step 3: GUIDE-011 范围限定】 ──► 【Step 4: 不可变证据机制绑定】 ──► 【Step 5: 4 项硬性 GO/NO-GO 门禁】 ──► 【Step 6: 历史决策包归档】
 (指定 ProjectListPage/DetailPage) (改“第二步：检索范围确认”)  (区分并保留合法 localStorage) (Tag/Release/Run-URL 关联) (含 CI 5/5 全绿在候选 SHA)   (e0-release-decision-package.md 归档)
```

---

## 详细实施规格

### Step 1: 产品入口与按钮定位（组件规格明确）

- **目标组件 1：课题详情页 `apps/frontend/src/pages/research/ProjectDetailPage.vue`**
  - 保持现有“**继续研究**”按钮指向 `/research/${project.id}/workspace` 不变。
  - 在动作栏内新增主按钮“**发起新研究**”，显式跳转至规范路由 `/research/${project.id}/workflow`（触发 `reset()` 并初始化全新 `run_id`）。
- **目标组件 2：课题列表页 `apps/frontend/src/pages/research/ProjectListPage.vue`**
  - **非空状态**：Header 动作区在 `+ 新建课题` 旁增设 `⚡ 直接研究` 快捷按钮，引导研究者进入默认选中的课题工作流。
  - **空态引导**：在 Empty State 区域新增示例提示“_支持《针灸甲乙经》版本检索与证据导出的可复现研究_”，提升价值吸引力。

### Step 2: 文本精度修改与测试断言对齐

- **精密文案修改**：
  - 将 `apps/frontend/src/components/research/workflow/DocumentSelectionStep.vue` L3 的标题文本由 `第二步：文献选择` 精确修改为 `第二步：检索范围确认`。
- **E2E 断言同步**：
  - 更新 Playwright 测试中对 `/文献选择/` 的正则表达式断言，同步替换为 `/检索范围确认/`。
  - 维持现有容器元素与提交按钮的 `role` / `aria-label` 语义属性，确保 `pnpm test:e2e` 定向回归通过。

### Step 3: GUIDE-011 指南范围限定

重写 `docs/06-guides/GUIDE-011-first-research-workflow.md`，**严格区分两类 `localStorage` 描述**：

- **应保留的真实描述**：保留关于“课题列表与 ID 通过 Pinia Store（`apps/frontend/src/stores/research.ts:14` `STORAGE_KEY`）在浏览器本地持久化”的准确技术事实。
- **应清理的废弃描述**：彻底删除暗示 `/research/new`、`/research/home`、6 工具栏以及旧版 V4 嵌入式工作区依赖 `localStorage` 保存分析结果的过时说明。
- **规范路由纠偏**：指南全程以 `/research/${projectId}/workflow` 和 `/research/${projectId}/workspace` 为唯一标准路由。

### Step 4: 不可变证据绑定机制定义

完成 Step 1~3 并进行 Code Freeze 提交后，获取该 Candidate SHA：

- **Git Tag 命名规范**：创建不可变标签，格式为 `v0.2.0-e0-candidate-YYYYMMDD`。
- **GitHub Release / CI Artifact 绑定**：
  - 通过 `gh release create v0.2.0-e0-candidate-YYYYMMDD --notes "Candidate SHA: <SHA> | CI Run URL: <URL>"` 创建发布候选存证。
  - CI 构建产物（Coverage JSON、E2E 报告、Test Log）自动关联至对应的 Actions Run ID，保存策略按 GitHub 默认 90 天留存。

### Step 5: 最终发布决策判定（4 项硬性门禁）

由审计方对冻结的 Candidate SHA 执行 **4 项一票否决制检查**：

1. **CI 5/5 全绿**：Build, Test, Documentation, Lint, Security 在**该 Candidate SHA 上**全部成功跑通（`success`）。
2. **SHA 证据唯一绑定**：Git Tag、Release Artifacts 及测试报告关联的 Commit 保持 100% 一致。
3. **工作区绝对干净**：`git status --short` 输出为空，`git diff --check` 无格式异常。
4. **网络与凭据安全**：生产 Compose `docker-compose.prod.yml` 无暴露端口（已绑定 `127.0.0.1`），`.env.example` 无明文默认凭据。

### Step 6: 历史 E0 决策包归档与追溯

- 将原 `docs/13-release/e0-release-decision-package.md` 文件顶部增加 `[ARCHIVED AUDIT TRAIL - NO-GO DECISION]` 标记旗帜。
- 将其保留在 `docs/13-release/` 目录中，作为该阶段发布审批从 `BLOCK_RELEASE` 到优化收敛全过程的只读追溯链条。
