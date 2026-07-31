---
title: 'Sprint 00 API Status'
version: '1.0'
status: 'Draft'
sprint: 'Sprint 00'
last_updated: '2026-06-24'
related: ['../../05-development/00_Development_Specification.md']
---

# Sprint 00 — API Status

## 当前 API 状态

**阶段：** API 设计完成，待实现。零端点。

## 规划的 API 模块

```
/api/v1/auth/          # 认证：注册、登录、刷新令牌
/api/v1/literature/    # 文献：书籍、版本、章节、段落 CRUD
/api/v1/entities/      # 实体：人物、地点、事件、概念 CRUD
/api/v1/ai/            # AI：RAG 问答、语义检索、GraphRAG 推理
/api/v1/admin/         # 管理：用户管理、数据导入、系统状态
```

## API 约定

- 统一错误格式：`{"error": {"code": "...", "message": "...", "detail": {...}}}`
- 分页：`offset` + `limit`
- 身份验证：JWT Bearer Token
- 文档：OpenAPI 3.0（FastAPI 自动生成）

## Sprint 01 API 任务

- FastAPI 项目初始化
- `/api/v1/auth/` 端点实现
- OpenAPI 文档可访问
- 健康检查端点

---

> **创建日期:** 2026-06-24
> **最后更新:** 2026-06-24
