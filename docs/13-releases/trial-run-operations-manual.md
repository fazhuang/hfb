---
document_id: HFB-REL-1303
document_title: 文献采集试运行操作手册
document_type: operations_manual
document_status: draft
version: v0.1.0
created_date: 2026-07-11
last_modified: 2026-07-11
author: Engineering
related_documents:
  - HFB-REL-1301
  - HFB-REL-1302
  - HFB-DEV-0509
tags:
  - operations
  - trial-run
  - literature
  - ingestion
---

# 文献采集试运行操作手册

## 概述

本文档指导如何对皇甫谧专题文献采集模块进行小规模试运行。试运行的目标是：

1. 验证外部 API 调用的可用性（5 个数据源，15 个种子关键词）
2. 观察去重准确性、错误率、速率限制行为
3. 确认 dry-run 模式不写入生产库
4. 收集试运行数据供后续分析

## 前置条件

### 环境
- Python 3.13+
- 网络可访问 OpenAlex、Crossref、CORE、PubMed、Internet Archive
- `.env` 中配置了 `CONTACT_EMAIL`

### 可选但推荐
- `.env` 中配置 `CORE_API_KEY`（否则 CORE 可能返回 429）
- 独立的 trial 数据库（默认为 `trial_ingestion.db` SQLite，与生产隔离）

## 快速开始

### 步骤 1：确认环境

```bash
cd /path/to/hfb
python3 --version                          # ≥ 3.13
python3 -m pytest tests/unit/test_literature_ingestion_compliance.py -q
```

### 步骤 2：Dry-Run（默认，不写数据库）

```bash
# 完整试运行 — 15 个种子关键词 × 5 个数据源 × 1 页
python3 scripts/trial_run_ingestion.py

# 单源测试
python3 scripts/trial_run_ingestion.py --source pubmed

# 单关键词测试
python3 scripts/trial_run_ingestion.py --query "皇甫谧"

# JSON 输出（机器可读）
python3 scripts/trial_run_ingestion.py --json > trial_result.json
```

Dry-run 模式会：
- 从每个来源拉取元数据
- 在内存中执行去重
- 打印汇总报告和样本条目
- **不创建任何数据库表，不写入任何记录**

### 步骤 3：分析 Dry-Run 结果

关注以下指标：

| 指标 | 健康值 | 需关注 |
|------|--------|--------|
| Jobs OK 率 | ≥ 80% | < 70% |
| 去重率 | 20-60% | < 5%（可能重复采集） |
| 单源错误率 | < 20% | > 30% |
| 唯一记录数 | > 50 | < 20（关键词需调整） |

### 步骤 4：Live 写入（可选，需确认）

```bash
# 写入独立的 trial SQLite 数据库（默认）
python3 scripts/trial_run_ingestion.py --live

# 指定目标数据库
python3 scripts/trial_run_ingestion.py --live --db-url sqlite+aiosqlite:///staging_ingest.db

# 单源 + 单页（最小化试运行）
python3 scripts/trial_run_ingestion.py --live --source crossref --page 1
```

**重要：** `--live` 会实际写入数据库。确认数据库连接字符串指向预期目标。
生产数据库应使用与生产环境相同的 PostgreSQL URL。

### 步骤 5：验证 Live 结果

```bash
# 查看写入的记录数
sqlite3 trial_ingestion.db "SELECT COUNT(*) FROM papers;"
sqlite3 trial_ingestion.db "SELECT source, COUNT(*) FROM papers GROUP BY source;"
sqlite3 trial_ingestion.db "SELECT COUNT(DISTINCT doi) FROM papers WHERE doi IS NOT NULL;"
sqlite3 trial_ingestion.db "SELECT title, source, year FROM papers LIMIT 10;"
```

## 种子关键词说明

试运行使用 15 个种子关键词，分 3 组：

| 组 | 术语 | 目的 |
|----|------|---------|
| **核心精确** | 皇甫谧、针灸甲乙经、Huangfu Mi、Zhenjiu Jiayi Jing | 高精度，验证主要目标 |
| **英文扩展** | A-B Classic of Acupuncture、Jiayi Jing、Huangfu Mi acupuncture | 西方学术文献召回 |
| **中文扩展** | 甲乙经 针灸、皇甫谧 医学、皇甫谧 文献 | 中文学术文献召回 |
| **相关交叉** | 黄帝内经 针灸、王焘 外台秘要 针灸、孙思邈 千金要方 针灸、张仲景 伤寒论 针灸 | 相关文献广度 |
| **学科框架** | early Chinese medical literature acupuncture | 中医文献学框架 |

## 速率限制与错误处理

### 已知行为

| 来源 | 限制 | 表现 |
|------|------|------|
| OpenAlex | 10 req/s 匿名 | 偶发 403 Cloudflare 拦截（已内置重试） |
| Crossref | 50 req/s | Polite pool，一般稳定 |
| CORE | 无 API key 时受限 | 中文查询 429，需配置 `CORE_API_KEY` |
| PubMed | 3 req/s（无 key） | 稳定，Europe PMC 优先 |
| Internet Archive | 无明确限制 | 皇甫谧主题通常返回 0 结果 |

### 故障排查

1. **OpenAlex 403** — 等待 30 秒后重试，或减少 page 参数
2. **CORE 429** — 在 `.env` 中设置 `CORE_API_KEY`
3. **全部超时** — 检查网络连接，确认可访问 api.openalex.org
4. **全部 0 结果** — 可能是 API 变更，检查各来源的 API 文档

## 试运行后任务

1. 记录 dry-run 结果并对比历史运行数据（参考 `literature-ingestion-v1-status.md`）
2. 检查是否有新的高价值来源出现
3. 如结果满意，将 `trial_ingestion.db` 中的数据导入 staging
4. 更新 memory 中的采集状态
5. 如有异常，查阅 `docs/13-releases/v0.1.0-literature-compliance-release.md` 中的 Known Limitations

## 回滚

试运行不涉及生产库，无需回滚。如执行了 `--live` 并需要清除：

```bash
# SQLite：直接删除数据库文件
rm trial_ingestion.db

# PostgreSQL：删除试运行期间创建的 Paper 记录
# (Paper 无外键级联 — 安全删除)
DELETE FROM papers WHERE created_at > '2026-07-11';
```

## 联系人

- 工程问题：参见 release notes 中的 Known Limitations
- 合规问题：参见 `docs/07-compliance/literature-source-policy.md`
- 学术问题：参见 Context 24 Gemini Review
