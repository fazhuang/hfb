"""
Infrastructure check importer used by main.py lifespan.
"""

from app.startup.check_infrastructure import run_health_checks

__all__ = ["run_health_checks"]
