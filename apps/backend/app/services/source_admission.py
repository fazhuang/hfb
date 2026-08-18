"""Source-admission gate for classical full-text upload.

Fail-closed: the ``POST /api/v1/documents/upload`` route stays frozen until a
Research Lead completes the manual source admission checklist
(``docs/03-data/0306_Manual_Research_Source_Admission_Checklist.md``) and the
deploy flips ``SOURCE_ADMISSION_OPEN``.

The gate is deliberately config-only. It never accepts client-supplied text
(such as ``authorization_basis``) as an unlock signal — admission is a
deployment decision, not a per-request claim.
"""

from app.core.config import settings


def is_source_admission_open() -> bool:
    """Return whether classical full-text upload is admitted.

    Frozen (False) by default. The only unlock path is the server-side
    ``SOURCE_ADMISSION_OPEN`` environment flag.
    """
    return bool(settings.SOURCE_ADMISSION_OPEN)
