from pathlib import Path
import re
import shutil
import datetime

def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")

def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

def extract_yaml_value(text: str, key: str) -> str | None:
    m = re.search(rf"^{re.escape(key)}:\s*(.+?)\s*$", text, re.M)
    if not m:
        return None
    return m.group(1).strip().strip('"').strip("'")

def has_yaml_header(text: str) -> bool:
    return text.startswith("---\n") or text.startswith("---\r\n")

def archive_file(path: Path, archive_dir: Path) -> Path | None:
    if not path.exists():
        return None
    archive_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    target = archive_dir / f"{path.parent.name}__{path.stem}__{ts}{path.suffix}"
    shutil.move(str(path), str(target))
    return target
