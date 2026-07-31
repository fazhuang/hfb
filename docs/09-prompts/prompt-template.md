---
title: Prompt Template
document_id: HFB-PRM-TPL-0001
version: 0.1.0
status: Draft
owner: —
reviewer: —
effective_date: 2026-06-24
scope: Prompt Engineering
priority: P2
tags:
  - template
  - prompt
---

# Prompt 模板

---

> **状态:** Draft → Review → Accepted → Implemented → Retired
> **版本:** v0.1.0
> **日期:** YYYY-MM-DD
> **作者:** [name]
> **负责人:** [name]
> **模型:** [Claude / Codex / Gemini / GPT / DeepResearch]
> **标签:** [tag1] [tag2]

## 目标

一句话说明这个 Prompt 解决什么问题。

## 适用模型

- **主要:** [model]
- **兼容:** [model] / 不适用

## System Prompt

```markdown
{{PLACEHOLDER_VALUE}}
```

## User Prompt

```markdown
{{USER_INPUT}}
```

## 输入示例

```text
{{EXAMPLE_INPUT}}
```

## 期望输出

```text
{{EXPECTED_OUTPUT}}
```

## 使用说明

1. 将 `{{PLACEHOLDER}}` 替换为实际值
2. 复制 System Prompt 到系统消息
3. 复制 User Prompt 到用户消息，用实际输入替换 `{{USER_INPUT}}`

## 已知限制

- _待定_
- _待定_

## 版本效果对比

| 版本   | 评估日期 | 准确率 | 备注 |
| ------ | -------- | ------ | ---- |
| v0.1.0 | —        | —      | —    |

## Changelog

| 版本   | 日期       | 变更 |
| ------ | ---------- | ---- |
| v0.1.0 | YYYY-MM-DD | 初稿 |
