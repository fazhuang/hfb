"""Source admission API — online 0306 §3 checklist + review flow."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, ValidationException
from app.db.database import get_session
from app.middleware.auth import get_current_user, require_permission
from app.models.source_admission import (
    ENTRY_KEYS,
    ENTRY_KEY_TO_TYPE,
    SourceAdmissionEntry,
    SourceAdmissionStatus,
)
from app.repositories.source_admission import SourceAdmissionRepository
from app.schemas.source_admission import (
    SourceAdmissionEntryResponse,
    SourceAdmissionEntryUpsert,
    SourceAdmissionListResponse,
    SourceAdmissionReviewRequest,
    SourceAdmissionReviewResponse,
    SourceAdmissionSummary,
)
from app.utils.response import api_response

router = APIRouter(tags=["Source Admissions"])


def _validate_entry_key(entry_key: str) -> None:
    if entry_key not in ENTRY_KEYS:
        raise ValidationException(
            f"Unknown entry key '{entry_key}'; expected one of {', '.join(ENTRY_KEYS)}"
        )


def _build_rows(
    entries: list[SourceAdmissionEntry],
) -> tuple[list[SourceAdmissionEntryResponse], SourceAdmissionSummary]:
    """Assemble the fixed 13-row view with placeholders for unfilled rows."""
    by_key = {e.entry_key: e for e in entries}
    rows: list[SourceAdmissionEntryResponse] = []
    for key in ENTRY_KEYS:
        entry = by_key.get(key)
        if entry is None:
            rows.append(
                SourceAdmissionEntryResponse(
                    id=None,
                    entry_key=key,
                    source_type=ENTRY_KEY_TO_TYPE[key],
                    source_uri=None,
                    authorization_basis=None,
                    version_label=None,
                    import_scope=None,
                    binding_plan=None,
                    risk_note=None,
                    status="empty",
                    submitted_by=None,
                    submitted_at=None,
                    reviewed_by=None,
                    reviewed_at=None,
                    review_note=None,
                )
            )
        else:
            rows.append(SourceAdmissionEntryResponse.model_validate(entry))

    statuses = [r.status for r in rows]
    summary = SourceAdmissionSummary(
        total_rows=len(ENTRY_KEYS),
        filled=sum(1 for s in statuses if s != "empty"),
        submitted=statuses.count("submitted"),
        approved=statuses.count("approved"),
        rejected=statuses.count("rejected"),
        complete=statuses.count("approved") == len(ENTRY_KEYS),
    )
    return rows, summary


@router.get(
    "/source-admissions",
    response_model=SourceAdmissionListResponse,
    dependencies=[Depends(require_permission("source_admission", "read"))],
)
async def list_source_admissions(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SourceAdmissionListResponse:
    """Return the 13-row checklist view + progress summary."""
    repo = SourceAdmissionRepository(session)
    entries = await repo.list_active()
    rows, summary = _build_rows(entries)
    return SourceAdmissionListResponse(items=rows, summary=summary)


@router.put(
    "/source-admissions/{entry_key}",
    response_model=dict[str, Any],
    dependencies=[Depends(require_permission("source_admission", "create"))],
)
async def upsert_source_admission(
    entry_key: Annotated[str, Path(min_length=1, max_length=20)],
    body: SourceAdmissionEntryUpsert,
    session: Annotated[AsyncSession, Depends(get_session)],
    user_id: Annotated[str, Depends(get_current_user)],
) -> dict[str, Any]:
    """Fill or update one checklist row (Research Lead); sets status=submitted."""
    _validate_entry_key(entry_key)
    repo = SourceAdmissionRepository(session)
    entry = await repo.get_by_entry_key(entry_key)
    now = datetime.now(UTC)

    if entry is None:
        entry = SourceAdmissionEntry(
            entry_key=entry_key,
            source_type=ENTRY_KEY_TO_TYPE[entry_key],
            **body.model_dump(),
            status=SourceAdmissionStatus.SUBMITTED,
            submitted_by=user_id,
            submitted_at=now,
        )
        session.add(entry)
    else:
        for field, value in body.model_dump().items():
            setattr(entry, field, value)
        entry.status = SourceAdmissionStatus.SUBMITTED
        entry.submitted_by = user_id
        entry.submitted_at = now
        entry.reviewed_by = None
        entry.reviewed_at = None
        entry.review_note = None

    await session.commit()
    await session.refresh(entry)
    return api_response(
        data=SourceAdmissionEntryResponse.model_validate(entry).model_dump(
            mode="json"
        ),
        message=f"Row {entry_key} submitted for review",
    )


@router.post(
    "/source-admissions/{entry_key}/review",
    response_model=SourceAdmissionReviewResponse,
    dependencies=[Depends(require_permission("source_admission", "review"))],
)
async def review_source_admission(
    entry_key: Annotated[str, Path(min_length=1, max_length=20)],
    body: SourceAdmissionReviewRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    user_id: Annotated[str, Depends(get_current_user)],
) -> SourceAdmissionReviewResponse:
    """Approve or reject a submitted row (Steering Committee)."""
    _validate_entry_key(entry_key)
    repo = SourceAdmissionRepository(session)
    entry = await repo.get_by_entry_key(entry_key)
    if entry is None:
        raise NotFoundException("SourceAdmissionEntry", entry_key)
    if entry.status != SourceAdmissionStatus.SUBMITTED:
        raise ValidationException(
            f"Row {entry_key} is {entry.status.value}; only submitted rows can be reviewed"
        )

    entry.status = (
        SourceAdmissionStatus.APPROVED
        if body.decision == "approve"
        else SourceAdmissionStatus.REJECTED
    )
    entry.reviewed_by = user_id
    entry.reviewed_at = datetime.now(UTC)
    entry.review_note = body.note
    await session.commit()

    return SourceAdmissionReviewResponse(
        success=True,
        entry_key=entry_key,
        status=entry.status,
        message=f"Row {entry_key} {entry.status.value}",
    )
