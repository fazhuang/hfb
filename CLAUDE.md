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

## 冻结基线

### Task 008 Library 基线 `06a6b74`
- Research Library 页面/API/E2E 冻结，禁止修改

### Task 009 R3 Reader 基线 `b3fd9ac`
- **Reader Page** (`apps/frontend/src/pages/reader/ReaderPage.vue`)：原文/OCR 分离、锚点解析、chunk 渲染 — 冻结
- **Reader API** (`apps/backend/app/api/v1/entities.py::get_document_reader`)：original_chunks/ocr_chunks 分离逻辑 — 冻结
- **Reader Tests** (`apps/frontend/src/__tests__/reader-page.test.ts`)：R3a-R3d 边界验证 — 冻结
- **Reader E2E** (`tests/e2e/test_reader_e2e.py`)：R3 API + UI 验证 — 冻结
- **关键约束**：禁止关键词匹配定位 chunk、禁止前端伪造文本、OCR 锚点必须指向 `ocr-chunk-{id}` DOM 节点、原文/OCR 严格分离
- **门禁**：371 前端测试 + 25 E2E + type-check + build ALL GREEN

### 通用冻结规则
- 禁止修改上述冻结文件，除非有新的明确任务指令
- 禁止开始 Task 010
- 禁止修改 Research Workflow 冻结基线 `cea0802`

## Docs 提交规范
- docs 类 commit：`docs: Context XX — <description>`
