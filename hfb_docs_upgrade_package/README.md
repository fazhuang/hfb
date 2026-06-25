# HFB Docs Upgrade Automation Package

用于升级《皇甫谧数字人文与中医经典智能研究平台》docs 文档体系。

## 使用方式

将本包内容复制到项目根目录，然后执行：

```bash
python3 scripts/docs_inventory.py
python3 scripts/docs_upgrade_scaffold.py
```

然后将：

```text
CLAUDE_DOCS_UPGRADE_PROMPT.md
```

投喂给 Claude Code。

Claude 完成后，将：

```text
CODEX_DOCS_ACCEPTANCE_PROMPT.md
```

投喂给 Codex 进行审计。

需要产品体验评审时，将：

```text
GEMINI_PRODUCT_REVIEW_PROMPT.md
```

投喂给 Gemini。
