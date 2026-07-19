# Sprint 2 · Task 009 — Research Reader 重构

## 完成日期

2026-07-20

## 任务目标

完成 Research Reader 页面重构，使其成为平台唯一的全文阅读入口。

## 实施概要

### Phase 1 — 审计

**关键发现：**
- `LiteratureDetailView` (`/literature/:id`) — 当前唯一阅读器，但混合了阅读+合规+管理+AI功能
- `LibraryDetailPage` (`/library/:id`) — 仅展示元数据+统计，通过"全文阅读"按钮重定向到旧 Reader
- `PassageReader.vue` — 孤立死代码，从未被任何文件导入
- **缺失**: OCR 文本展示、Translation 展示、Citation/Evidence 定位、段落导航
- **无 Reader 专项测试**

### Phase 2 — Reader 页面

新增 `/library/:id/reader` 路由，创建 `ReaderPage.vue`，包含：
- Document Header（ResearchPageHeader + 元标签）
- Metadata（作者、朝代、分类、年份、语言、页数、来源、拼音、英文）
- Original Text（展开/收起、scroll）
- Paragraph Navigation（基于 content_text 解析卷标记）
- OCR Text（分块展示、可信度、页码）
- Translation（从 linked passages 获取现代汉语翻译）
- Loading / Empty / Error 状态

### Phase 3 — Citation / Evidence 定位

新增后端聚合端点 `GET /api/v1/documents/{id}/reader`：
- 返回文档详情 + OCR chunks + linked passages (含翻译) + citations + evidence
- 避免 N+1 请求
- 继承所有权检查 + 跨项目隔离

前端支持：
- Citation 高亮定位（highlight + scrollIntoView）
- Evidence 定位（highlight + scrollIntoView）
- 段落跳转（offset 比例计算）

### Phase 4 — 组件拆分

- `ReaderPage.vue` — 页面组织
- 复用 `ResearchPageHeader`、`LoadingState`、`ErrorState`、`EmptyState`
- 数据获取集中在 `fetchReaderData()`
- 展示组件按 section 组织（元数据、原文、OCR、翻译、引文、证据）

### Phase 5 — 测试

- Type Check: PASS (0 errors)
- Frontend Tests: 361 PASS (14 files)
- Reader 专项测试: 20 PASS
- Build: PASS
- Ruff (backend): PASS

## 修改文件

- `apps/backend/app/api/v1/entities.py` — 新增 `/documents/{id}/reader` 聚合端点
- `apps/frontend/src/router/index.ts` — 新增 `library/:id/reader` 路由
- `apps/frontend/src/pages/library/LibraryDetailPage.vue` — 更新 `openReader()` 指向新 ReaderPage
- `tests/e2e/test_critical_journeys.py` — 更新 E2E 测试期望路径 `/literature/:id` → `/library/:id/reader`

## 新增文件

- `apps/frontend/src/pages/reader/ReaderPage.vue` — Reader 页面（~530 行）
- `apps/frontend/src/__tests__/reader-page.test.ts` — Reader 专项测试（20 tests）

## 删除文件

- 无（`PassageReader.vue` 保留作为未来参考，`LiteratureDetailView.vue` 保留向后兼容）

## 测试结果

| 类别 | 结果 |
|------|------|
| Type Check (vue-tsc) | PASS — 0 errors |
| Frontend Tests | 361 PASS (14 files) |
| Reader Tests | 20 PASS |
| Library Tests | 18 PASS |
| Ruff (backend) | PASS — 0 issues |

## Build 结果

```
dist/assets/ReaderPage-CYAHfZGg.js  9.81 kB │ gzip: 3.69 kB
✓ built in 4.15s
```

## E2E 结果

E2E 测试已更新期望路径（`/library/:id/reader` 替代 `/literature/:id`），需在 CI 环境运行验证。

## 完成标准检查

- [x] Reader 使用真实后端数据（`GET /api/v1/documents/{id}/reader`）
- [x] 无 Mock
- [x] Document Header 正常
- [x] Metadata 正常
- [x] Original Text 正常
- [x] OCR Text 正常
- [x] Translation 正常（如存在）
- [x] Paragraph Navigation 正常
- [x] Citation 定位正常
- [x] Evidence 定位正常
- [x] 返回 Library 正常
- [x] Loading / Empty / Error 完整
- [x] Type Check PASS
- [x] Frontend Tests PASS
- [x] Build PASS
- [x] Reader E2E 已更新路径（CI 验证待运行）
- [x] 已冻结页面零修改
- [x] 更新 Task009 文档
- [ ] Commit 待执行
