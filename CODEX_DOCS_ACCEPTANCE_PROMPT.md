# Codex 验收指令：Docs 升级审计

你负责审计《皇甫谧数字人文与中医经典智能研究平台》docs 升级结果。

## 一、审计目标

判断 Claude 是否按照 `DOCS_UPGRADE_PLAN.md` 和 `CLAUDE_DOCS_UPGRADE_PROMPT.md` 完成文档体系升级。

重点不是评价文字是否漂亮，而是检查：

- 是否减少混乱；
- 是否消除重复；
- 是否统一结构；
- 是否服务产品实现；
- 是否可指导开发与验收；
- 是否与 16/17 系列一致。

---

## 二、必须执行的检查命令

在项目根目录执行：

```bash
find docs -maxdepth 3 -type f | sort
find docs -name "*.md.md"
find docs -type f -name "*.md" | wc -l
grep -R "^document_id:" docs --include="*.md" | sort
grep -R "^title:" docs --include="*.md" | sort
grep -R "HFB-PS-17" docs --include="*.md"
grep -R "17-Platform-Specifications" docs --include="*.md"
```

检查是否存在：

- `.md.md`;
- 重复 Project Charter;
- 重复 Constitution;
- 重复 Acceptance;
- document_id 重复；
- documentation-index 与实际文件不一致。

---

## 三、重点审计目录

### P0 目录

```text
docs/README.md
docs/documentation-index.md
docs/00-governance/
docs/01-product/
docs/02-architecture/
docs/03-data/
docs/04-ai/
docs/05-development/
docs/06-ui/
docs/07-security/
docs/08-domain/
```

### 基线目录

必须确认未被破坏：

```text
docs/16-research-framework/
docs/17-Platform-Specifications/
```

---

## 四、判定标准

### 通过条件

必须满足：

- 有 `docs/DOCS_STRUCTURE_AUDIT.md`;
- 有 `docs/UPGRADE_REPORT.md`;
- 有 `docs/DOCS_CHANGELOG.md`;
- 重复文件已归档；
- `.md.md` 已修复；
- P0 文档都有 YAML Header；
- document_id 唯一；
- documentation-index.md 可用；
- 16/17 系列内容未被降级；
- 01~15 与 17 系列产品规格一致；
- 文档明确服务产品实现。

### 阻塞条件

任一存在即判定阻塞：

- 删除 16/17 核心文档；
- 大量新增无关目录；
- 重复文件未处理；
- document_id 冲突；
- 无升级报告；
- P0 文档无 Header；
- documentation-index 失真；
- 文档继续空泛，不可指导开发。

---

## 五、审计输出格式

请严格输出：

```markdown
# Docs Upgrade Acceptance Report

## 1. 总体结论

- 是否通过：
- 是否阻塞：
- 总分：

## 2. 已验证命令

列出命令与结果摘要。

## 3. 通过项

逐条列出。

## 4. 阻塞项

逐条列出，必须包含文件路径。

## 5. 主要问题

按 P0/P1/P2 分类。

## 6. 与 16/17 一致性检查

说明是否对齐。

## 7. 对 Claude 的修复指令

给出可直接复制给 Claude 的修复 Prompt。

## 8. 最终建议

通过 / 不通过 / 有条件通过。
```

---

## 六、特别注意

不要只看文档数量。

不要被“完成了很多文件”迷惑。

核心判断：

> 这些文档是否能减少开发歧义、减少审计争议、减少产品偏航。

如果不能，即使文件很多，也不得通过。
