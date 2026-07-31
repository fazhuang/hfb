"""
Entity status lifecycle state machine — Day 1 spec.

States:  draft → active → archived → deleted
         draft ──────────────→ deleted
         active ─────────────→ deleted

Deleted is terminal.  Pure functions — no framework, no DB dependency.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Day 1 state machine (draft → active → archived → deleted)
# ---------------------------------------------------------------------------

_VALID_TRANSITIONS: dict[str, frozenset[str]] = {
    "draft": frozenset({"active", "deleted"}),
    "active": frozenset({"archived", "deleted"}),
    "archived": frozenset({"deleted"}),
    "deleted": frozenset(),  # terminal
}

_STATES: frozenset[str] = frozenset(_VALID_TRANSITIONS.keys())


def is_valid_state(state: str) -> bool:
    """Return True if *state* is a known state name."""
    return state in _STATES


def can_transition(current: str, target: str) -> bool:
    """Check whether *target* is a valid transition from *current*."""
    allowed = _VALID_TRANSITIONS.get(current, frozenset())
    return target in allowed


def validate_transition(current: str, target: str) -> None:
    """Raise InvalidStatusTransitionError if the transition is not allowed.

    Also rejects unknown current or target states.
    """
    if not is_valid_state(current):
        raise InvalidStatusTransitionError(
            f"Unknown current status: '{current}'. Valid states: {sorted(_STATES)}"
        )
    if not is_valid_state(target):
        raise InvalidStatusTransitionError(
            f"Unknown target status: '{target}'. Valid states: {sorted(_STATES)}"
        )
    if not can_transition(current, target):
        raise InvalidStatusTransitionError(
            f"Invalid status transition: '{current}' → '{target}'"
        )


def is_terminal(state: str) -> bool:
    """Return True if *state* has no outgoing transitions."""
    return len(_VALID_TRANSITIONS.get(state, frozenset())) == 0


# ---------------------------------------------------------------------------
# Status machine exception
# ---------------------------------------------------------------------------


class InvalidStatusTransitionError(ValueError):
    """Raised when a status transition is not allowed by the state machine."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.error_code = "INVALID_STATUS_TRANSITION"
