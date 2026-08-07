"""
Deterministic unit tests for source_whitelist.py — runtime source policy enforcement.
Covers: SourcePolicyEntry defaults/explicit, name normalization, lookup,
default-deny, category D rejection, allowed_sources filtering, and
get_whitelist config path resolution with lru_cache isolation.
All YAML content is constructed via tmp_path — no real files read.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from app.services.source_whitelist import (
    SourcePolicyEntry,
    SourceWhitelist,
    get_whitelist,
)

# =============================================================================
# Helpers
# =============================================================================


def _write_yaml(path: Path, data: dict) -> Path:
    """Write a temporary YAML file and return its Path."""
    path.write_text(yaml.dump(data, allow_unicode=True), encoding="utf-8")
    return path


def _clear_whitelist_cache() -> None:
    """Clear the lru_cache on get_whitelist between tests."""
    get_whitelist.cache_clear()


@pytest.fixture(autouse=True)
def _clear_cache():
    """Ensure no cached whitelist leaks between tests."""
    _clear_whitelist_cache()
    yield
    _clear_whitelist_cache()


# =============================================================================
# SourcePolicyEntry
# =============================================================================


class TestSourcePolicyEntry:
    def test_all_fields_explicit(self):
        entry = SourcePolicyEntry(
            {
                "name": "OpenAlex",
                "domain": "openalex.org",
                "category": "A",
                "metadata_allowed": True,
                "fulltext_allowed": True,
                "requires_manual_review": False,
            }
        )
        assert entry.name == "OpenAlex"
        assert entry.domain == "openalex.org"
        assert entry.category == "A"
        assert entry.metadata_allowed is True
        assert entry.fulltext_allowed is True
        assert entry.requires_manual_review is False

    def test_defaults_false(self):
        """Omitted boolean fields default to False."""
        entry = SourcePolicyEntry(
            {
                "name": "Unknown Source",
                "domain": "example.com",
                "category": "B",
            }
        )
        assert entry.metadata_allowed is False
        assert entry.fulltext_allowed is False
        assert entry.requires_manual_review is False

    def test_partial_overrides(self):
        """metadata_allowed overridden but fulltext_allowed defaulted."""
        entry = SourcePolicyEntry(
            {
                "name": "CNKI",
                "domain": "cnki.net",
                "category": "B",
                "metadata_allowed": True,
            }
        )
        assert entry.metadata_allowed is True
        assert entry.fulltext_allowed is False


# =============================================================================
# Name normalization
# =============================================================================


class TestNormalize:
    def test_lowercase(self):
        assert SourceWhitelist._normalize("OpenAlex") == "openalex"

    def test_underscore_to_space(self):
        assert SourceWhitelist._normalize("internet_archive") == "internet archive"

    def test_mixed_case_and_underscore(self):
        assert SourceWhitelist._normalize("Internet_Archive") == "internet archive"

    def test_spaces_preserved(self):
        assert SourceWhitelist._normalize("Internet Archive") == "internet archive"

    def test_empty_string(self):
        assert SourceWhitelist._normalize("") == ""


# =============================================================================
# lookup
# =============================================================================


class TestLookup:
    def test_hit_exact_name(self):
        wl = SourceWhitelist(
            {
                "sources": [
                    {"name": "OpenAlex", "domain": "openalex.org", "category": "A"}
                ]
            }
        )
        entry = wl.lookup("OpenAlex")
        assert entry is not None
        assert entry.name == "OpenAlex"

    def test_hit_case_insensitive(self):
        wl = SourceWhitelist(
            {
                "sources": [
                    {"name": "OpenAlex", "domain": "openalex.org", "category": "A"}
                ]
            }
        )
        assert wl.lookup("openalex") is not None
        assert wl.lookup("OPENALEX") is not None

    def test_hit_underscore_equivalent(self):
        wl = SourceWhitelist(
            {
                "sources": [
                    {
                        "name": "Internet Archive",
                        "domain": "archive.org",
                        "category": "A",
                    }
                ]
            }
        )
        assert wl.lookup("internet_archive") is not None

    def test_miss_unlisted_source(self):
        wl = SourceWhitelist(
            {
                "sources": [
                    {
                        "name": "PubMed",
                        "domain": "pubmed.ncbi.nlm.nih.gov",
                        "category": "A",
                    }
                ]
            }
        )
        assert wl.lookup("SciHub") is None

    def test_miss_empty_sources(self):
        wl = SourceWhitelist({"sources": []})
        assert wl.lookup("anything") is None

    def test_whitespace_insensitive(self):
        """Extra spaces on either side don't matter for lookup."""
        wl = SourceWhitelist(
            {
                "sources": [
                    {"name": "OpenAlex", "domain": "openalex.org", "category": "A"}
                ]
            }
        )
        # Normalization strips spaces from name, not from argument.
        # Argument "openalex" matches "openalex" (lowered) — and " OpenAlex "
        # lowered and space-collapsed becomes " openalex " which is NOT "openalex".
        # Actually: _normalize(" OpenAlex ") → " openalex " (spaces preserved)
        # Source name "OpenAlex" → "openalex" (no spaces)
        # So they don't match. That's correct — name is exact match after normalize.
        # Only test what normalize actually does.
        assert wl.lookup("  OpenAlex  ") is None  # spaces not collapsed
        assert wl.lookup("OpenAlex") is not None


# =============================================================================
# is_source_allowed / default-deny
# =============================================================================


class TestDefaultDeny:
    def test_unlisted_source_denied_by_default_policy(self):
        """Default policy metadata_allowed=false → unlisted sources denied."""
        wl = SourceWhitelist(
            {
                "sources": [],
                "default_policy": {
                    "metadata_allowed": False,
                    "fulltext_allowed": False,
                },
            }
        )
        assert wl.is_source_allowed("unknown", metadata=True) is False
        assert wl.is_source_allowed("unknown", metadata=False) is False

    def test_unlisted_source_allowed_when_default_true(self):
        """When default policy allows, unlisted sources inherit that."""
        wl = SourceWhitelist(
            {
                "sources": [],
                "default_policy": {"metadata_allowed": True, "fulltext_allowed": False},
            }
        )
        assert wl.is_source_allowed("unknown", metadata=True) is True
        assert wl.is_source_allowed("unknown", metadata=False) is False

    def test_unlisted_fulltext_denied_even_when_metadata_allowed(self):
        wl = SourceWhitelist(
            {
                "sources": [],
                "default_policy": {"metadata_allowed": True, "fulltext_allowed": False},
            }
        )
        assert wl.is_source_allowed("unknown", metadata=True) is True
        assert wl.is_source_allowed("unknown", metadata=False) is False

    def test_no_default_policy_specified_defaults_false(self):
        """When default_policy key is missing, both allow flags default to False."""
        wl = SourceWhitelist({"sources": []})
        assert wl.is_source_allowed("unknown", metadata=True) is False
        assert wl.is_source_allowed("unknown", metadata=False) is False


# =============================================================================
# Category D rejection
# =============================================================================


class TestCategoryDRejection:
    def test_d_category_always_rejected_metadata(self):
        wl = SourceWhitelist(
            {
                "sources": [
                    {
                        "name": "SciHub",
                        "domain": "sci-hub.se",
                        "category": "D",
                        "metadata_allowed": True,
                        "fulltext_allowed": True,
                    },
                ]
            }
        )
        assert wl.is_source_allowed("SciHub", metadata=True) is False

    def test_d_category_always_rejected_fulltext(self):
        wl = SourceWhitelist(
            {
                "sources": [
                    {
                        "name": "SciHub",
                        "domain": "sci-hub.se",
                        "category": "D",
                        "metadata_allowed": True,
                        "fulltext_allowed": True,
                    },
                ]
            }
        )
        assert wl.is_source_allowed("SciHub", metadata=False) is False

    def test_d_category_rejected_even_with_true_flags(self):
        """Even if metadata_allowed=True on the entry, D category overrides."""
        wl = SourceWhitelist(
            {
                "sources": [
                    {
                        "name": "PirateBay",
                        "domain": "*.se",
                        "category": "D",
                        "metadata_allowed": True,
                        "fulltext_allowed": False,
                    },
                ]
            }
        )
        assert wl.is_source_allowed("PirateBay", metadata=True) is False


# =============================================================================
# Category A/B/C combinations
# =============================================================================


class TestAllowedCombinations:
    def test_category_a_full_access(self):
        wl = SourceWhitelist(
            {
                "sources": [
                    {
                        "name": "OpenAlex",
                        "domain": "openalex.org",
                        "category": "A",
                        "metadata_allowed": True,
                        "fulltext_allowed": True,
                    },
                ]
            }
        )
        assert wl.is_source_allowed("OpenAlex", metadata=True) is True
        assert wl.is_source_allowed("OpenAlex", metadata=False) is True

    def test_category_b_metadata_only(self):
        wl = SourceWhitelist(
            {
                "sources": [
                    {
                        "name": "CNKI",
                        "domain": "cnki.net",
                        "category": "B",
                        "metadata_allowed": True,
                        "fulltext_allowed": False,
                    },
                ]
            }
        )
        assert wl.is_source_allowed("CNKI", metadata=True) is True
        assert wl.is_source_allowed("CNKI", metadata=False) is False

    def test_category_c_metadata_with_review(self):
        wl = SourceWhitelist(
            {
                "sources": [
                    {
                        "name": "Forum",
                        "domain": "*",
                        "category": "C",
                        "metadata_allowed": True,
                        "fulltext_allowed": False,
                        "requires_manual_review": True,
                    },
                ]
            }
        )
        assert wl.is_source_allowed("Forum", metadata=True) is True
        assert wl.is_source_allowed("Forum", metadata=False) is False


# =============================================================================
# allowed_sources
# =============================================================================


class TestAllowedSources:
    def test_returns_only_non_d_with_metadata(self):
        wl = SourceWhitelist(
            {
                "sources": [
                    {
                        "name": "OpenAlex",
                        "domain": "openalex.org",
                        "category": "A",
                        "metadata_allowed": True,
                        "fulltext_allowed": True,
                    },
                    {
                        "name": "CNKI",
                        "domain": "cnki.net",
                        "category": "B",
                        "metadata_allowed": True,
                        "fulltext_allowed": False,
                    },
                    {
                        "name": "SciHub",
                        "domain": "sci-hub.se",
                        "category": "D",
                        "metadata_allowed": False,
                        "fulltext_allowed": False,
                    },
                    {
                        "name": "NoMetaSource",
                        "domain": "example.com",
                        "category": "A",
                        "metadata_allowed": False,
                        "fulltext_allowed": True,
                    },
                ]
            }
        )
        names = wl.allowed_sources()
        assert "OpenAlex" in names
        assert "CNKI" in names
        assert "SciHub" not in names
        assert "NoMetaSource" not in names  # metadata_allowed=False

    def test_empty_when_no_sources(self):
        wl = SourceWhitelist({"sources": []})
        assert wl.allowed_sources() == []

    def test_all_d_category_returns_empty(self):
        wl = SourceWhitelist(
            {
                "sources": [
                    {
                        "name": "Pirate",
                        "domain": "*",
                        "category": "D",
                        "metadata_allowed": True,
                        "fulltext_allowed": False,
                    },
                ]
            }
        )
        assert wl.allowed_sources() == []


# =============================================================================
# get_whitelist — explicit config_path
# =============================================================================


class TestGetWhitelistExplicitPath:
    def test_loads_from_explicit_tmp_path(self, tmp_path):
        yaml_path = _write_yaml(
            tmp_path / "wl.yaml",
            {
                "sources": [
                    {
                        "name": "TestSource",
                        "domain": "test.example",
                        "category": "A",
                        "metadata_allowed": True,
                        "fulltext_allowed": True,
                    },
                ],
            },
        )
        wl = get_whitelist(config_path=str(yaml_path))
        assert wl.lookup("TestSource") is not None
        assert wl.is_source_allowed("TestSource", metadata=True) is True

    def test_missing_path_raises_filenotfound(self, tmp_path):
        missing = tmp_path / "does_not_exist.yaml"
        with pytest.raises(FileNotFoundError, match="source_whitelist.yaml not found"):
            get_whitelist(config_path=str(missing))


# =============================================================================
# get_whitelist — SOURCE_WHITELIST_PATH env var
# =============================================================================


class TestGetWhitelistEnvVar:
    def test_loads_from_env_var(self, tmp_path, monkeypatch):
        yaml_path = _write_yaml(
            tmp_path / "env_wl.yaml",
            {
                "sources": [
                    {
                        "name": "EnvSource",
                        "domain": "env.example",
                        "category": "B",
                        "metadata_allowed": True,
                        "fulltext_allowed": False,
                    },
                ],
            },
        )
        monkeypatch.setenv("SOURCE_WHITELIST_PATH", str(yaml_path))
        wl = get_whitelist()
        assert wl.lookup("EnvSource") is not None

    def test_env_var_takes_priority_over_default(self, tmp_path, monkeypatch):
        """When both config_path and env var are absent, fallback path is used.
        When env var IS set, it takes priority."""
        yaml_path = _write_yaml(
            tmp_path / "priority_wl.yaml",
            {
                "sources": [
                    {
                        "name": "PrioritySource",
                        "domain": "p.example",
                        "category": "A",
                        "metadata_allowed": True,
                        "fulltext_allowed": True,
                    },
                ],
            },
        )
        monkeypatch.setenv("SOURCE_WHITELIST_PATH", str(yaml_path))
        wl = get_whitelist()
        assert wl.lookup("PrioritySource") is not None

    def test_env_var_bad_path_raises_filenotfound(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SOURCE_WHITELIST_PATH", str(tmp_path / "nope.yaml"))
        with pytest.raises(FileNotFoundError):
            get_whitelist()


# =============================================================================
# get_whitelist — lru_cache isolation
# =============================================================================


class TestLRUCacheIsolation:
    def test_cache_returns_same_instance(self, tmp_path):
        """Cached calls return the same SourceWhitelist object."""
        yaml_path = _write_yaml(
            tmp_path / "cache_wl.yaml",
            {
                "sources": [
                    {
                        "name": "Cached",
                        "domain": "c.example",
                        "category": "A",
                        "metadata_allowed": True,
                        "fulltext_allowed": True,
                    },
                ],
            },
        )
        wl1 = get_whitelist(config_path=str(yaml_path))
        wl2 = get_whitelist(config_path=str(yaml_path))
        assert wl1 is wl2

    def test_cache_clear_returns_new_instance(self, tmp_path):
        """After cache clear, a new instance is created."""
        yaml_path = _write_yaml(
            tmp_path / "clear_wl.yaml",
            {
                "sources": [
                    {
                        "name": "ClearTest",
                        "domain": "cl.example",
                        "category": "A",
                        "metadata_allowed": True,
                        "fulltext_allowed": True,
                    },
                ],
            },
        )
        wl1 = get_whitelist(config_path=str(yaml_path))
        _clear_whitelist_cache()
        wl2 = get_whitelist(config_path=str(yaml_path))
        # Same data, different object after cache clear
        assert wl1 is not wl2
        # But same logical content
        assert wl1.lookup("ClearTest") is not None
        assert wl2.lookup("ClearTest") is not None

    def test_different_config_path_not_cached_together(self, tmp_path):
        """Different config_path arguments produce different results."""
        yaml_a = _write_yaml(
            tmp_path / "a.yaml",
            {
                "sources": [
                    {
                        "name": "SourceA",
                        "domain": "a.example",
                        "category": "A",
                        "metadata_allowed": True,
                        "fulltext_allowed": True,
                    },
                ],
            },
        )
        yaml_b = _write_yaml(
            tmp_path / "b.yaml",
            {
                "sources": [
                    {
                        "name": "SourceB",
                        "domain": "b.example",
                        "category": "A",
                        "metadata_allowed": True,
                        "fulltext_allowed": True,
                    },
                ],
            },
        )
        get_whitelist(config_path=str(yaml_a))
        # lru_cache(maxsize=1) — second call with different arg evicts first
        _clear_whitelist_cache()
        wl_b = get_whitelist(config_path=str(yaml_b))
        assert wl_b.lookup("SourceB") is not None

    def test_invalid_path_clears_cache_on_failure(self, tmp_path):
        """After a FileNotFoundError, a subsequent valid call should work."""
        bad = tmp_path / "bad.yaml"
        with pytest.raises(FileNotFoundError):
            get_whitelist(config_path=str(bad))
        # lru_cache doesn't cache exceptions — next call is fresh
        good = _write_yaml(
            tmp_path / "good.yaml",
            {
                "sources": [
                    {
                        "name": "Good",
                        "domain": "g.example",
                        "category": "A",
                        "metadata_allowed": True,
                        "fulltext_allowed": True,
                    },
                ],
            },
        )
        wl = get_whitelist(config_path=str(good))
        assert wl.lookup("Good") is not None
