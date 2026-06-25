# HFB Governance Toolkit

## 命令

```bash
python3 -m tools.hgt docs inventory
python3 -m tools.hgt docs scaffold
python3 -m tools.hgt docs validate
python3 -m tools.hgt docs report
python3 -m tools.hgt docs all
```

## 当前能力

- 扫描 docs 结构；
- 识别 `.md.md`；
- 识别重复 document_id；
- 识别缺失 YAML Header；
- 识别缺失 README 的目录；
- 归档已知重复旧文档；
- 修复已知 `.md.md`；
- 生成 `DOCS_STRUCTURE_AUDIT.md`；
- 生成 `UPGRADE_REPORT.md`；
- 生成 `DOCS_CHANGELOG.md`。

## 边界

v0.1 不自动重写正文内容。

正文升级由 Claude Code 执行，Codex 验收。
