## Wikisource 古籍原典验证

- 四库全书本《针灸甲乙经》通过 Wikisource API 获取：`https://zh.wikisource.org/w/api.php?action=parse&page=鍼灸甲乙經_(四庫全書本)/卷XX&prop=text&format=json`
- **同一个 Wikisource URL 多次 WebFetch 可能返回不同文字**（编码/解析不一致），关键文字必须以最近一次 fetch 为准，并在报告中标注版本来源
- 四库全书本存在清乾隆馆臣校勘干预（避讳改字、异体字规范），与通行本（如黄龙祥校注本）可能存在文字差异，涉及穴位归属时不宜作确定性同一化判定

## 古籍证据分级（A/B/C）

- A：原典明确"小兒/嬰兒/乳子" + 包含呼吸症状 + 有取穴
- B：原典有呼吸症状与取穴，但未限定儿童
- C：现代临床指南或国家标准
- 严禁 B→A 或 C→A 反推
- 惊痫/痫瘈语境下的"不得息""喘"不可脱离原病证外推为现代哮喘

## Docs 提交规范

- docs 类 commit：`docs: Context XX — <description>`

## 前端开发规范

- 无直接 Hex 颜色硬编码，必须使用 Design Token（`--color-*`、`--text-*`、`--space-*`）
- 禁止 `any` 类型
- 数组类型用 `Array<T>` 而非 `T[]`
- 提交前必须运行 `npx eslint`、`npx vue-tsc --noEmit`、`npx vitest run`

## 常用命令

- 前端目录：`apps/frontend`
- 启动前端：`cd apps/frontend && npx vite --host 0.0.0.0`
- 启动后端：`cd apps/backend && python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload`
- 运行 Reports 单测：`pnpm --filter @hfb/frontend test src/__tests__/research-reports-page.test.ts`
- Playwright 可用（`npx playwright`），测试用户 `researcher / researcher123`
- 200% 缩放检测用 `document.body.style.zoom = '200%'`，注意固定定位导航栏不在页面作用域内
