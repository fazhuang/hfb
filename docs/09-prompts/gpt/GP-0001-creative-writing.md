---
title: Creative Writing Prompt
document_id: HFB-PRM-GP-0001
version: 0.1.0
status: Draft
owner: —
reviewer: —
effective_date: 2026-06-24
scope: Prompt Engineering
priority: P2
model: GPT
tags:
  - writing
  - creative
---

# GP-0001 Creative Writing

---

> **状态:** Draft
> **版本:** v0.1.0
> **日期:** 2026-06-24
> **作者:** —
> **负责人:** —
> **模型:** GPT
> **标签:** [writing] [creative]

## 目标

生成高质量的创意写作文本，支持指定风格、语气和长度。

## 适用模型

- **主要:** GPT
- **兼容:** Claude、Gemini
- **不适用:** Codex

## System Prompt

```markdown
You are an experienced writer. Write text that matches the requested style, tone, and length.

Rules:

- Match the specified voice exactly
- Avoid clichés unless the style specifically calls for them
- End with impact — the last sentence should land
- Do not explain your choices or add meta-commentary
```

## User Prompt

```markdown
Style: {{STYLE_DESCRIPTION}}
Tone: {{TONE}}
Length: {{LENGTH}}
Topic: {{TOPIC}}

Write:
```

## 输入示例

```text
{{STYLE_DESCRIPTION}} = 简洁、有力，像海明威
{{TONE}} = 冷静、旁观
{{LENGTH}} = 200 字以内
{{TOPIC}} = 一个程序员在凌晨三点发现了一个 bug
```

## 期望输出

```text
凌晨三点，显示屏是唯一的灯。

他盯着那行代码已经二十分钟了。第九百四十二行，一个等号写成了不等号。六个月前，他的手打出了这个字符。

现在六万用户的数据是错的。

他改了那行代码。测试通过。部署。然后关上电脑。

窗外开始亮了。他什么也没想。
```

## 使用说明

1. 填写 Style / Tone / Length / Topic 四个参数
2. 组合 System + User Prompt 发送
3. 如结果不符合预期，调整 Style 描述更具体

## 已知限制

- Style 描述模糊时输出不稳定
- 超过 500 字后一致性下降
- 中文短篇效果优于长篇

## 版本效果对比

| 版本   | 评估日期 | 准确率 | 备注 |
| ------ | -------- | ------ | ---- |
| v0.1.0 | —        | —      | —    |

## Changelog

| 版本   | 日期       | 变更                        |
| ------ | ---------- | --------------------------- |
| v0.1.0 | 2026-06-24 | 初稿 — 风格写作、四参数驱动 |
