---
title: 'Person Knowledge'
version: '1.0'
status: 'Active'
domain: 'person'
last_updated: '2026-06-24'
---

# Person — 人物知识

历史人物与现代学者的结构化知识。

## 人物分类

- 古代医家（如皇甫谧、张仲景、孙思邈）
- 古代哲学家（如老子、庄子）
- 历史人物（帝王、官员等）
- 现代学者（古籍研究者）
- 虚构人物（文学作品人物，标注虚构标记）

## 标准属性

见 `docs/03-data/01_Ontology_Specification.md` §2.2

## 示例

```json
{
  "name": "Huangfu Mi",
  "name_zh": "皇甫谧",
  "birth_year": 215,
  "death_year": 282,
  "courtesy_name": "士安",
  "dynasty": "魏晋",
  "biography": "魏晋医学家，著《针灸甲乙经》，整理《黄帝内经》",
  "works": ["《针灸甲乙经》", "《帝王世纪》"],
  "entity_type": "Person"
}
```

---

> **创建日期:** 2026-06-24
> **最后更新:** 2026-06-24
