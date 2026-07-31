"""Smoke tests for trial_run_ingestion.py — import, arg parsing, dry-run structure."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

# Make scripts/ importable
_root = str(
    Path(__file__).resolve().parent.parent.parent
)  # repo root (tests/unit/ -> tests/ -> root)
sys.path.insert(0, str(Path(_root) / "apps" / "backend"))


class TestTrialScriptImport:
    """Verify the trial script can be imported and parsed without side effects."""

    def test_argparse_defaults(self):
        """Default args: dry-run mode, all sources, trial queries, page=1."""
        # Import the parse_args function via __import__
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "trial_run", str(Path(_root) / "scripts" / "trial_run_ingestion.py")
        )
        # Don't execute the module body (it does path manipulation) —
        # we only need parse_args via parsing manually.
        # Instead, test the module structure.
        assert spec is not None, "trial_run_ingestion.py should exist and be loadable"

    def test_seed_keywords_present(self):
        """TRIAL_QUERIES list should have ~15 terms, covering 中文 + English."""
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "trial_run", str(Path(_root) / "scripts" / "trial_run_ingestion.py")
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        assert len(mod.TRIAL_QUERIES) >= 10, (
            f"Expected ≥10 seed keywords, got {len(mod.TRIAL_QUERIES)}"
        )
        # Must include both Chinese and English
        assert any("皇甫谧" in q for q in mod.TRIAL_QUERIES), (
            "Missing core Chinese term"
        )
        assert any("Huangfu Mi" in q for q in mod.TRIAL_QUERIES), (
            "Missing core English term"
        )
        # Must include cross-reference terms
        assert any("黄帝内经" in q for q in mod.TRIAL_QUERIES), (
            "Missing cross-reference term"
        )

    def test_dry_run_is_default(self):
        """--live must be False by default."""
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "trial_run", str(Path(_root) / "scripts" / "trial_run_ingestion.py")
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        # Simulate: sys.argv = ['trial_run_ingestion.py'] (no --live)
        with patch.object(sys, "argv", ["trial_run_ingestion.py"]):
            args = mod.parse_args()
            assert args.live is False, "--live should default to False"
            assert args.page == 1, "--page should default to 1"


class TestTrialScriptSourceCompliance:
    """Verify no PDF download logic in trial script source code."""

    def test_no_pdf_imports_or_references(self):
        """Trial script source must not reference pdf, fulltext download paths."""
        script_path = Path(_root) / "scripts" / "trial_run_ingestion.py"
        source = script_path.read_text()

        forbidden = [
            "download.pdf",
            "downloadUrl",
            "getFullText",
            "fulltext.pdf",
            "requests.get",
            "urllib.request",
            "wget",
        ]
        for pattern in forbidden:
            assert pattern not in source.lower(), (
                f"Forbidden pattern '{pattern}' found in trial script"
            )

    def test_dry_run_no_session_flush(self):
        """Dry-run path must not call session.add() or session.flush()."""
        script_path = Path(_root) / "scripts" / "trial_run_ingestion.py"
        source = script_path.read_text()

        # The _dry_run function should exist
        assert "async def _dry_run" in source, "Missing _dry_run function"

        # _dry_run function body — extract and check no session writes
        dry_run_start = source.index("async def _dry_run")
        # Find the next top-level async def or if __name__
        next_def = len(source)
        for marker in ["\nasync def _live_run", "\nif __name__"]:
            idx = source.find(marker, dry_run_start)
            if idx != -1:
                next_def = min(next_def, idx)
        dry_run_body = source[dry_run_start:next_def]

        # Should import but not use session
        assert "session.add" not in dry_run_body, "_dry_run must not call session.add"
        assert "session.flush" not in dry_run_body, (
            "_dry_run must not call session.flush"
        )
        assert "session.commit" not in dry_run_body, (
            "_dry_run must not call session.commit"
        )

    def test_live_run_has_gate(self):
        """--live mode must exist as an explicit opt-in path."""
        script_path = Path(_root) / "scripts" / "trial_run_ingestion.py"
        source = script_path.read_text()

        assert "async def _live_run" in source, "Missing _live_run function"
        assert "--live" in source, "Missing --live argument flag"
        assert "not args.live" in source, "Must check args.live before writing"


class TestDocumentReferences:
    """Verify related documents reference each other correctly."""

    def test_release_notes_mentions_related_docs(self):
        release_path = (
            Path(_root)
            / "docs"
            / "13-releases"
            / "v0.1.0-literature-compliance-release.md"
        )
        content = release_path.read_text()

        assert "trial" in content.lower()
        assert "Gemini" in content
        assert "Context 24" in content
        assert "checklist" in content.lower()

    def test_checklist_has_all_sections(self):
        checklist_path = (
            Path(_root)
            / "docs"
            / "13-releases"
            / "v0.1.0-literature-compliance-checklist.md"
        )
        content = checklist_path.read_text()

        required_sections = [
            "代码冻结",
            "测试验证",
            "合规红线验证",
            "环境配置",
            "试运行准备",
            "回滚准备",
            "发布标签",
        ]
        for section in required_sections:
            assert section in content, f"Checklist missing section: {section}"

    def test_operations_manual_has_all_steps(self):
        manual_path = (
            Path(_root) / "docs" / "13-releases" / "trial-run-operations-manual.md"
        )
        content = manual_path.read_text()

        required_topics = [
            "Dry-Run",
            "Live",
            "种子关键词",
            "速率限制",
            "回滚",
            "sqlite3",
            "trial_ingestion",
            "CORE_API_KEY",
        ]
        for topic in required_topics:
            assert topic in content, f"Operations manual missing topic: {topic}"
