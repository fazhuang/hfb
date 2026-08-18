#!/usr/bin/env python3
"""Build complete 针灸甲乙经 PDF from all scraped chapter data.

Merges all raw scrapling output files, deduplicates, orders by the book's
table of contents, produces a single clean HTML, then converts to PDF.
"""

from __future__ import annotations

import json
import re
import html as html_mod
import glob
import os
from collections import OrderedDict

RAW_DIR = "/Users/likeming/.claude/projects/-Users-likeming-Sites-hfb/53c0911e-9899-4014-a2d4-d5caeffb742f/tool-results/"
OUT_HTML = "/Users/likeming/Sites/hfb/针灸甲乙经_四库全书本.html"
OUT_PDF = "/Users/likeming/Sites/hfb/针灸甲乙经_四库全书本.pdf"

# Canonical chapter order derived from the book's sidebar TOC.
# (chapter_id, label, parent_volume)
CANONICAL: list[tuple[str, str, str | None]] = [
    # Title page / 提要 / 序
    ("1m17dqxaqpjbu", "鍼灸甲乙經 · 欽定四庫全書", None),
    ("1m17dqxaqpvyy", "提要", None),
    ("1m17dqxaqusyi", "鍼灸甲乙經序", None),
    # 卷一
    ("1jurkyxgjjnea", "鍼灸甲乙經卷一", None),
    ("1m1jdidk1fsp6", "精神五藏論第一", "卷一"),
    ("1m1jdidk1g5ca", "五藏變腧第二", "卷一"),
    ("1m1jdidk1ghze", "五藏六府陰陽表裏第三", "卷一"),
    ("1m1jdidk1gumi", "五藏五官第四", "卷一"),
    ("1m1jdidk1h79m", "五藏大小六府應候第五", "卷一"),
    ("1jurkyxhzsufu", "十二原第六", "卷一"),
    ("1jurkyxhzt72y", "十二經水第七", "卷一"),
    ("1m1jdidk1hjwq", "四海第八", "卷一"),
    ("1m1jdidk1hwju", "氣息周身五十營四時日分漏刻第九", "卷一"),
    ("1m1jdidk1i96y", "營氣第十", "卷一"),
    ("1m1jdidu7mkh2", "營衛三焦第十一", "卷一"),
    ("1jurkyxhztjq2", "陰陽清濁精氣津液血脈第十二", "卷一"),
    ("1m1jdidu7mx46", "津液五別第十二", "卷一"),
    ("1m1jdidu7n9ra", "奇邪血絡第十四", "卷一"),
    ("1jurkyxhzulne", "五色第十五", "卷一"),
    ("1m1jdidu7nmee", "陰陽二十五人形性血氣不同第十六", "卷一"),
    # 卷二
    ("1jurkyz91vub7", "鍼灸甲乙經卷二", None),
    ("1jurkyza0r9c9", "十二經脈絡脈支別第一 (上)", "卷二"),
    ("1jurkyzax7xuj", "十二經脈絡脈支別第一 (下)", "卷二"),
    ("1m1jdig4kodv6", "奇經八脈第二", "卷二"),
    ("1jurkyzb26omq", "脈度第三", "卷二"),
    ("1jurkyzb4nj1v", "十二經標本第四", "卷二"),
    ("1m1jdig4koqia", "經脈根結第五", "卷二"),
    ("1m1jdig4kp35e", "經筋第六", "卷二"),
    ("1m1jdig4kpfsi", "骨度腸度腸胃所受第七", "卷二"),
    # 卷三 (穴位)
    ("1jurkz0ey3pxm", "鍼灸甲乙經卷三", None),
    ("1m1jdilmnrkm3", "俠脊凡二十六穴第九 / 面凡二十九穴第十", "卷三"),
    ("1m1jdilmns9wb", "耳前後凡二十穴第十一", "卷三"),
    # 卷四 (脉诊)
    ("1m17du0i2gg7d", "鍼灸甲乙經卷四", None),
    ("1m17du0i2gsuh", "經脈第一 (上)", "卷四"),
    ("1m17du0i2h5hl", "經脈第一 (下)", "卷四"),
    ("1m17du0i2hi4p", "脈經第一", "卷四"),
    ("1m17du0i2hurt", "病形脈胗第二 (上)", "卷四"),
    ("1m17du0i2i7ex", "病形脈診第二 (下)", "卷四"),
    ("1m17du0i2ik21", "三部九候第三", "卷四"),
    # 卷五 (针灸禁忌与针道)
    ("1jurkz23d8gtu", "鍼灸甲乙經卷五", None),
    ("1m1jdip68f6su", "針灸禁忌第一 (上)", "卷五"),
    ("1m1jdip68fw32", "右刺禁 / 右禁灸", "卷五"),
    # 卷六
    ("1jurkz32bnos3", "鍼灸甲乙經卷六", None),
    ("1m1jdir0ytee2", "八正八虛八風大論第一 / 逆順病本末方宜形志大論第二", "卷六"),
    ("1m1jdir0yu3oa", "五藏六府虛實大論第三", "卷六"),
    # 卷七
    ("1jurkz3pu79y3", "鍼灸甲乙經卷七", None),
    ("1jurkz3pu7ml7", "六經受病發傷寒熱病第一 (上)", "卷七"),
    ("1jurkz3pu7z8b", "六經受病發傷寒熱病第一 (中)", "卷七"),
    ("1m1jdit3qhfrd", "六經受病發傷寒熱病第一 (下)", "卷七"),
    ("1m1jdit3qhseh", "足陽明脈病發熱狂走第二", "卷七"),
    ("1jurkz3pu9dsr", "陰陽相移發三瘧第五", "卷七"),
    # 卷八
    ("1m17du4xetkpn", "鍼灸甲乙經卷八", None),
    ("1m17du4xetxcr", "五藏傳病發寒熱第一 (上)", "卷八"),
    ("1m17du4xeu9zv", "五藏傳病發寒熱第一 (下)", "卷八"),
    ("1m17du4xeummz", "五藏六府脹第三", "卷八"),
    ("1m17du4xeuza3", "水膚脹鼓脹腸覃石瘕第四", "卷八"),
    ("1m17du4xevbx7", "腎風發風水面胕腫第五", "卷八"),
    # 卷九
    ("1jurkz4zowaat", "鍼灸甲乙經卷九", None),
    ("1m1jdivamhnou", "大寒內薄骨髓陽逆發頭痛第一 / 寒氣客於五藏六府發卒心痛胸痺心疝三蟲第二 / 邪在肺五藏六府受病發欬逆上氣第三", "卷九"),
    ("1jurkz4zowmxx", "邪在肺五藏六府受病發欬逆上氣第三 (續)", "卷九"),
    ("1jurkz4zowzl1", "肝受病及衛氣留積發胸脇滿痛第四", "卷九"),
    ("1jurkz4zoxc85", "脾受病發四肢不用第六", "卷九"),
    ("1jurkz4zoxov9", "脾胃大腸受病發腹脹滿腸中鳴短氣第七", "卷九"),
    ("1jurkz4zoy1id", "三焦膀胱受病發少腹腫不得小便第九", "卷九"),
    ("1jurkz4zoyqsl", "足太陽脈動發下部痔脫肛第十二", "卷九"),
    # 卷十
    ("1m17du759925v", "鍼灸甲乙經卷十", None),
    ("1m17du7599esz", "陰受病發痺第一 (上)", "卷十"),
    ("1m17du7599rg3", "陰受病發痺第一 (下)", "卷十"),
    ("1m17du759a437", "陽受病發風第二 (上)", "卷十"),
    ("1m17du759agqb", "陽受病發風第二 (下)", "卷十"),
    ("1m17du759atdf", "八虛受病發拘攣第三", "卷十"),
    ("1m17du759b60j", "熱在五藏發痿第四", "卷十"),
    ("1m17du759binn", "痛肩似拔第五", "卷十"),
    ("1m17du759bvar", "水漿不消發飲第六", "卷十"),
    # 卷十一
    ("1jurkz69r1l3e", "鍼灸甲乙經卷十一", None),
    ("1lzguzkr17twa", "胸中寒發脈代第一", "卷十一"),
    ("1lzguzkr186je", "陽厥大驚發狂癇第二", "卷十一"),
    ("1lzguzkr18j6i", "陽脈下墜陰脈上爭發尸厥第三", "卷十一"),
    ("1jurkz69r2adm", "氣亂於腸胃發霍亂吐下第四", "卷十一"),
    ("1jurkz69r3cay", "足太陰厥脈病發溏泄下痢第五", "卷十一"),
    ("1jurkz69r4e8a", "五氣溢發消渴黃癉第六", "卷十一"),
    ("1lzguzkr18vtm", "動作失度內外傷發崩中瘀血嘔血唾血第七", "卷十一"),
    ("1lzguzkr198gq", "邪氣聚於下脘發內癰第八 / 寒氣客於經絡之中發癰疽風成發厲浸淫第九", "卷十一"),
    # 卷十二
    ("1m1jdiyhtokrq", "鍼灸甲乙經卷十二", None),
    ("1m1jdiyhtoxeu", "客氣客於厭發喑不能言第二 / 目不得眠不得視及多臥臥不安不得偃臥肉苛諸息有音及喘第三 / 足太陽陽明手少陽脈動發目病第四", "卷十二"),
    ("1m1jdiyhtpmp2", "手太陽少陽脈動發耳病第五", "卷十二"),
]


def clean_markdown(text: str) -> str:
    """Strip boilerplate, navigation, app promo, sidebar links."""
    lines = text.split("\n")
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped in (
            "粗校译文", "针灸甲乙经粗校译文", "APP",
            "Add to Library", "Log In", "Word Freq",
            "Read anytime, anywhere. Scan the code to download the APP.",
        ):
            continue
        if stripped.startswith("[All Books]"):
            continue
        if stripped.startswith("![") and "webp" in stripped:
            continue
        if stripped.startswith("[Next]("):
            continue
        if re.match(r"^\d+\n?$", stripped) and len(stripped) <= 3:
            continue
        if re.match(r"^\d+%$", stripped):
            continue
        if "该图片已删除" in stripped:
            continue
        if re.match(r"^\[晉\]|^\[宋\]", stripped):
            continue
        if "20 Editors" in stripped:
            continue
        if re.match(r"^\[.+?\]\(/book/SK1420/chapter/", stripped):
            continue
        out.append(line)
    result = "\n".join(out)
    result = re.sub(r"\n{4,}", "\n\n\n", result)
    return result.strip()


def load_all_chapters() -> OrderedDict[str, dict]:
    """Read all raw scrapling output and return {chapter_id: {title, content, url}}."""
    chapters: OrderedDict[str, dict] = OrderedDict()
    pattern = os.path.join(RAW_DIR, "call_00_*.txt")
    for fpath in sorted(glob.glob(pattern)):
        with open(fpath, "r", encoding="utf-8") as f:
            raw = f.read()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        results = data.get("result", [])
        for item in results:
            content = item.get("content", [""])[0]
            url = item.get("url", "")
            ch_id = url.split("/chapter/")[-1] if "/chapter/" in url else ""
            cleaned = clean_markdown(content)
            if ch_id and ch_id not in chapters:
                chapters[ch_id] = {"content": cleaned, "url": url}
    return chapters


def markdown_to_html(text: str) -> str:
    """Convert content text to safe HTML paragraphs with heading support."""
    escaped = html_mod.escape(text)
    # Headings
    escaped = re.sub(r"^#{3,4}\s+(.+)$", r"<h3>\1</h3>", escaped, flags=re.MULTILINE)
    escaped = re.sub(r"^-----$", "", escaped, flags=re.MULTILINE)
    # Paragraphs
    escaped = escaped.replace("\n\n", "</p><p>")
    escaped = "<p>" + escaped + "</p>"
    escaped = re.sub(r"<p>\s*</p>", "", escaped)
    return escaped


def build_html(chapters: OrderedDict[str, dict]) -> str:
    """Assemble the full HTML document."""
    toc_items: list[str] = []
    body_sections: list[str] = []

    for seq, (ch_id, label, _vol) in enumerate(CANONICAL):
        text = chapters.get(ch_id, {}).get("content", "")
        if not text:
            continue

        anchor = f"ch{seq}"
        display_label = html_mod.escape(label)
        toc_items.append(
            f'<li><a href="#{anchor}">{display_label}</a></li>'
        )
        body_html = markdown_to_html(text)
        body_sections.append(
            f'<section id="{anchor}">\n'
            f'<h2>{display_label}</h2>\n'
            f'{body_html}\n'
            f'</section>'
        )

    return f'''<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="UTF-8">
<title>鍼灸甲乙經 · 四庫全書本</title>
<style>
  :root {{
    --bg: #f5f0e8;
    --text: #2c2416;
    --accent: #8b4513;
    --border: #d4c5a9;
    --toc-bg: #ede4d3;
  }}
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: "Songti SC", "Noto Serif CJK SC", "STSong", "SimSun", serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.9;
    max-width: 850px;
    margin: 0 auto;
    padding: 2rem 1.5rem;
    font-size: 15px;
  }}
  h1 {{
    text-align: center;
    font-size: 1.8rem;
    margin-bottom: 0.5rem;
    color: var(--accent);
  }}
  .meta {{
    text-align: center;
    color: #6b5e4a;
    font-size: 0.9rem;
    margin-bottom: 2rem;
  }}
  nav {{
    background: var(--toc-bg);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 1.2rem 1.5rem;
    margin-bottom: 2.5rem;
  }}
  nav h2 {{
    font-size: 1.1rem;
    margin-bottom: 0.6rem;
    color: var(--accent);
  }}
  nav ol {{
    padding-left: 1.5rem;
  }}
  nav li {{
    margin: 0.2rem 0;
    font-size: 0.92rem;
  }}
  nav a {{
    color: var(--accent);
    text-decoration: none;
  }}
  nav a:hover {{ text-decoration: underline; }}
  section {{
    margin-bottom: 2rem;
    padding-bottom: 1.5rem;
    border-bottom: 1px solid var(--border);
  }}
  section h2 {{
    font-size: 1.3rem;
    color: var(--accent);
    margin-bottom: 1rem;
    text-align: center;
  }}
  section h3 {{
    font-size: 1.1rem;
    color: #5a3e28;
    margin: 1.2rem 0 0.5rem;
  }}
  p {{
    text-indent: 2em;
    margin: 0.5rem 0;
  }}
  @media print {{
    body {{ font-size: 11pt; padding: 1cm; }}
    nav {{ page-break-after: always; }}
    section {{ page-break-before: always; }}
  }}
</style>
</head>
<body>

<h1>鍼灸甲乙經</h1>
<p class="meta">欽定四庫全書 · 子部 · 醫家類<br>
〔晉〕皇甫謐 撰 · 〔宋〕高保衡 林億 等校注<br>
來源：識典古籍 (shidianguji.com) · 下載日期：2026-08-12<br>
全書十二卷，計 91 頁</p>

<nav>
<h2>目錄</h2>
<ol>
{"".join(toc_items)}
</ol>
</nav>

{"".join(body_sections)}

</body>
</html>'''


def main() -> None:
    chapters = load_all_chapters()
    print(f"Loaded {len(chapters)} unique chapters from raw files")

    # Report which canonical chapters are missing
    missing = [cid for cid, _, _ in CANONICAL if cid not in chapters]
    if missing:
        print(f"WARNING: {len(missing)} canonical chapters missing: {missing}")

    html = build_html(chapters)
    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"HTML written: {OUT_HTML} ({len(html):,} bytes)")

    try:
        from weasyprint import HTML
        HTML(OUT_HTML).write_pdf(OUT_PDF)
        pdf_size = os.path.getsize(OUT_PDF)
        print(f"PDF written: {OUT_PDF} ({pdf_size:,} bytes)")
    except ImportError:
        print("WeasyPrint not available. Skipping PDF.")


if __name__ == "__main__":
    main()
