#!/usr/bin/env python3
"""Extract 针灸甲乙经 from raw scrapling fetch results, produce clean HTML then PDF."""

import json
import re
import html as html_mod

RAW_FILE = "/Users/likeming/.claude/projects/-Users-likeming-Sites-hfb/53c0911e-9899-4014-a2d4-d5caeffb742f/tool-results/call_00_Os4bnHKwxWHJQkkQel8X8609.txt"
OUT_HTML = "/Users/likeming/Sites/hfb/针灸甲乙经_四库全书本.html"

def clean_markdown(text: str) -> str:
    """Remove navbar boilerplate, repeated sidebar links, app-promo lines."""
    lines = text.split("\n")
    out = []
    skip_block = False
    for line in lines:
        # Skip app promo / login / navigation blocks
        if line.strip() in ("粗校译文", "针灸甲乙经粗校译文", "APP", "Add to Library", "Log In",
                            "Read anytime, anywhere. Scan the code to download the APP.",
                            "Word Freq"):
            continue
        if line.strip().startswith("[All Books]"):
            continue
        if line.strip().startswith("![") and "webp" in line:
            continue
        if line.strip().startswith("[Next]("):
            continue
        if re.match(r'^\d+\n?$', line.strip()) and len(line.strip()) <= 3:
            continue  # page numbers
        if re.match(r'^\d+%$', line.strip()):
            continue
        if "该图片已删除" in line:
            continue
        if re.match(r'^\[晋\]|^\[宋\]', line.strip()):
            continue  # author line at top
        if "20 Editors" in line:
            continue
        # Remove sidebar TOC (links like "[针灸甲乙经](/book/...")
        if re.match(r'^\[(.+?)\]\(/book/SK1420/chapter/', line.strip()):
            # Only keep if it's actually a chapter heading in context
            # These are sidebar links, skip them
            continue
        # Keep lines that have actual content
        out.append(line)
    # Collapse 3+ blank lines into 2
    result = "\n".join(out)
    result = re.sub(r'\n{4,}', '\n\n\n', result)
    return result.strip()

def extract_chapters(raw_text: str) -> list[dict]:
    """Parse the JSON array result and extract each chapter."""
    data = json.loads(raw_text)
    results = data["result"]
    chapters = []
    titles = [
        "钦定四库全书 · 提要",
        "针灸甲乙经序",
        "针灸甲乙经卷一",
        "针灸甲乙经卷二",
        "针灸甲乙经卷三",
        "针灸甲乙经卷四",
        "针灸甲乙经卷五",
        "针灸甲乙经卷六",
        "针灸甲乙经卷七",
        "针灸甲乙经卷八",
        "针灸甲乙经卷九",
        "针灸甲乙经卷十",
        "针灸甲乙经卷十一",
        "针灸甲乙经卷十二",
    ]
    for i, item in enumerate(results):
        content = item["content"][0]
        cleaned = clean_markdown(content)
        title = titles[i] if i < len(titles) else f"Chapter {i}"
        chapters.append({"title": title, "content": cleaned, "url": item.get("url", "")})
    return chapters

def build_html(chapters: list[dict]) -> str:
    """Build a single self-contained HTML page with all chapters."""
    toc_items = []
    body_sections = []

    for i, ch in enumerate(chapters):
        anchor = f"ch{i}"
        toc_items.append(f'<li><a href="#{anchor}">{html_mod.escape(ch["title"])}</a></li>')

        # Convert markdown headings to HTML
        text = ch["content"]
        # Escape HTML first
        text = html_mod.escape(text)
        # Convert markdown headings (###, ####, -----)
        text = re.sub(r'^#{3,4}\s+(.+)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
        text = re.sub(r'^-----$', '', text, flags=re.MULTILINE)
        # Bold markers
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        # Line breaks
        text = text.replace('\n\n', '</p><p>')
        text = '<p>' + text + '</p>'
        # Clean up empty paragraphs
        text = re.sub(r'<p>\s*</p>', '', text)

        body_sections.append(f'<section id="{anchor}">\n<h2>{html_mod.escape(ch["title"])}</h2>\n{text}\n</section>')

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
    max-width: 800px;
    margin: 0 auto;
    padding: 2rem 1.5rem;
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
    margin: 0.25rem 0;
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
    body {{ font-size: 12pt; padding: 1cm; }}
    nav {{ page-break-after: always; }}
    section {{ page-break-before: always; }}
  }}
</style>
</head>
<body>

<h1>鍼灸甲乙經</h1>
<p class="meta">欽定四庫全書 · 子部 · 醫家類<br>
〔晉〕皇甫謐 撰 · 〔宋〕高保衡 林億 等校注<br>
來源：識典古籍 (shidianguji.com) · 下載日期：2026-08-12</p>

<nav>
<h2>目錄</h2>
<ol>
{"".join(toc_items)}
</ol>
</nav>

{"".join(body_sections)}

</body>
</html>'''


def main():
    with open(RAW_FILE, "r", encoding="utf-8") as f:
        raw = f.read()

    chapters = extract_chapters(raw)
    html = build_html(chapters)

    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"HTML written: {OUT_HTML}")
    print(f"Chapters: {len(chapters)}")
    total_chars = sum(len(ch["content"]) for ch in chapters)
    print(f"Total chars: {total_chars}")

if __name__ == "__main__":
    main()
