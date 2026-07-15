# Context 20: 古籍版本模块 Codex 验收

**验收日期:** 2026-07-10  
**验收对象:** 古籍版本目录模块 `ClassicalVersion`、API、迁移、RBAC、测试覆盖  
**结论:** **BLOCK_RELEASE**

## 结论摘要

当前 worktree 已实现古籍版本模块的基础模型、schema、API 路由和专项测试，但不能按本轮验收口径放行。

阻塞项只有 1 个：`DELETE /api/admin/classical-versions/{version_id}` 实际调用 `hard_delete()`，会物理删除数据库行，不是软删除。

另外有 2 个非阻塞但必须记录的质量问题：

1. `public_domain_status` 在 create schema 中有默认值 `unknown`，因此“业务上必填/必须显式填写”未严格成立；当前只能证明数据库非空。
2. 写接口权限粒度不严：`PATCH` 复用 `require_admin()`，而该依赖只检查 `classical_version.create`，没有检查 `classical_version.update`。

## 验收矩阵

| 验收项 | 结论 | 证据 |
|---|---:|---|
| 普通用户是否不能新增、编辑、删除 | PASS | 路由探针：普通用户 `POST /api/admin/classical-versions` = 403，`PATCH /api/admin/classical-versions/{id}` = 403；源码中写接口均挂载 `require_admin` / `require_superuser`。 |
| 管理员是否可以新增、编辑 | PASS | 路由探针：管理员 `POST` = 201，`PATCH` = 200；源码中新增和编辑路由均依赖 `require_admin`。 |
| 删除是否为软删除 | **FAIL** | 删除路由调用 `svc.hard_delete(version_id)`；路由探针中超级用户删除返回 200 后，直接查表结果为 `row_after_super_delete='absent'`。 |
| 版本是否必须有来源 | PASS | `ClassicalVersionCreate.source_url` 为必填字段；路由探针中缺少 `source_url` 的创建请求返回 422；服务层 `_validate_create()` 也拒绝空 `source_url`。 |
| 公共领域状态是否必填 | PARTIAL | 数据库和模型为 `nullable=False`，但 schema 给 `public_domain_status` 默认值 `unknown`，路由探针中未显式传入也可创建成功。因此“字段非空”成立，“必须人工显式填写”不成立。 |
| 是否支持人工审核状态 | PASS | schema 定义 `pending_review / under_review / approved / rejected`；迁移有 `ck_classical_versions_review_status`；服务层 create/update 均校验 `review_status`。 |
| 是否有测试覆盖 | PASS | `tests/unit/test_classical_versions.py` 与 `tests/unit/test_classical_versions_rbac.py` 存在，专项测试命令通过：`28 passed in 4.21s`。 |

## 关键源码证据

### API 与权限

- `apps/backend/app/api/v1/classical_versions.py:172-190`：`POST /api/admin/classical-versions` 使用 `_admin: Depends(require_admin)`。
- `apps/backend/app/api/v1/classical_versions.py:193-213`：`PATCH /api/admin/classical-versions/{version_id}` 使用 `_admin: Depends(require_admin)`。
- `apps/backend/app/api/v1/classical_versions.py:216-227`：`DELETE /api/admin/classical-versions/{version_id}` 使用 `_superuser: Depends(require_superuser)`，但执行 `await svc.hard_delete(version_id)`。
- `apps/backend/app/api/v1/classical_versions.py:110-120`：`require_admin()` 只检查 `classical_version.create`，未检查 `classical_version.update`。

### 软删除与硬删除

- `apps/backend/app/repositories/base.py:149-159`：基础仓库已有 `soft_delete()`，会设置 `is_deleted=True` 和 `deleted_at`。
- `apps/backend/app/repositories/base.py:161-166`：`hard_delete()` 使用 SQLAlchemy `delete()` 物理删除。
- `apps/backend/app/services/base.py:63-67`：服务层同时暴露 `soft_delete()` 与 `hard_delete()`。
- `apps/backend/app/api/v1/classical_versions.py:226`：古籍版本 DELETE 路由选择的是 `hard_delete()`，不是 `soft_delete()`。

### 来源、公共领域、审核状态

- `apps/backend/app/schemas/classical_version.py:35-48`：创建 schema 中 `source_url` 必填；`public_domain_status` 默认 `unknown`；`review_status` 默认 `pending_review`。
- `apps/backend/app/api/v1/classical_versions.py:57-72`：创建校验要求 `work_title`、`version_name`、`source_url` 非空，并校验 `public_domain_status`、`review_status`、`edition_type` 枚举。
- `apps/backend/app/api/v1/classical_versions.py:74-83`：更新校验覆盖 `public_domain_status`、`review_status`、`edition_type`。
- `apps/backend/app/db/migrations/versions/a4b5c6d7e8f9_add_classical_versions.py:36-40`：迁移层 `public_domain_status` 与 `review_status` 均为 `nullable=False` 并有默认值。
- `apps/backend/app/db/migrations/versions/a4b5c6d7e8f9_add_classical_versions.py:43-50`：迁移层有公共领域状态和审核状态的 check constraint。

## 动态验证

已执行：

```bash
uv run pytest tests/unit/test_classical_versions.py tests/unit/test_classical_versions_rbac.py -q
```

结果：

```text
28 passed in 4.21s
```

真实 ASGI 路由探针结果：

```text
normal_post=403
admin_post=201
normal_patch=403
admin_patch=200
missing_source_post=422
missing_pd_post=201
admin_delete=403
super_delete=200
row_after_super_delete=absent
```

解释：

- 普通用户不能新增和编辑。
- 管理员可以新增和编辑。
- 缺少来源会被拒绝。
- 未显式传 `public_domain_status` 仍可创建，说明它不是强制人工填写。
- 管理员不能删除，超级用户可以删除。
- 超级用户删除后数据库行不存在，证明当前删除是硬删除。

## 最小修复要求

1. 将 `delete_classical_version()` 从 `await svc.hard_delete(version_id)` 改为 `await svc.soft_delete(version_id)`。
2. 增加路由级测试：调用 DELETE 后直接查表，必须看到行仍存在，且 `is_deleted=True`、`deleted_at is not None`。
3. 如验收口径要求“公共领域状态必须由提交者显式填写”，则移除 `ClassicalVersionCreate.public_domain_status` 默认值，保持字段必填，并补缺失字段 422 测试。
4. 如验收口径要求编辑权限独立于新增权限，则 `PATCH` 应检查 `classical_version.update`，并补仅有 create 无 update 的 403 测试。

## 最终门禁

**BLOCK_RELEASE**

阻塞发布原因：删除不是软删除。
