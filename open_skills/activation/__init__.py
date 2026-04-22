"""Explainable skill activation and task matching."""

from .engine import (
    AMBIGUITY_MARGIN,
    THRESHOLDS,
    ActivationMatch,
    activate_skills,
    score_skill,
)

__all__ = [
    "AMBIGUITY_MARGIN",
    "THRESHOLDS",
    "ActivationMatch",
    "activate_skills",
    "score_skill",
]
