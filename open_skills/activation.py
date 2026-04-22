from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .loader import SkillLoadError, discover_skills, load_skill
from .models import SkillPackage
from .validator import validate_skill

THRESHOLDS = {
    "broad": 0.20,
    "balanced": 0.40,
    "strict": 0.70,
}

AMBIGUITY_MARGIN = 0.08
STOPWORDS = {
    "a",
    "an",
    "and",
    "for",
    "in",
    "my",
    "of",
    "on",
    "or",
    "the",
    "this",
    "to",
    "with",
}


@dataclass(slots=True)
class ActivationMatch:
    skill: SkillPackage
    score: float
    threshold: str
    matched_triggers: list[str] = field(default_factory=list)
    matched_permissions: list[str] = field(default_factory=list)
    matched_fields: dict[str, list[str]] = field(default_factory=dict)
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def activate_skills(
    task: str,
    skills_dir: str | Path,
    *,
    host: str | None = None,
    threshold: str = "balanced",
    limit: int = 5,
) -> list[ActivationMatch]:
    if threshold not in THRESHOLDS:
        raise ValueError(f"Unknown activation threshold: {threshold}")

    matches: list[ActivationMatch] = []
    for skill_path in discover_skills(skills_dir):
        try:
            skill = load_skill(skill_path)
        except SkillLoadError:
            continue
        if validate_skill(skill):
            continue
        if host and not _supports_host(skill, host):
            continue

        match = score_skill(task, skill, threshold=threshold)
        if match.score >= THRESHOLDS[threshold]:
            matches.append(match)

    matches.sort(key=lambda item: item.score, reverse=True)
    selected = matches[:limit]
    _mark_ambiguous_matches(selected)
    return selected


def score_skill(task: str, skill: SkillPackage, *, threshold: str = "balanced") -> ActivationMatch:
    query = _normalize(task)
    query_terms = _terms(task)
    metadata = skill.metadata
    matched_fields: dict[str, list[str]] = {}
    reasons: list[str] = []

    score = 0.0

    name_text = metadata.name.replace("-", " ")
    if name_text and name_text in query:
        score += 0.25
        matched_fields["name"] = [metadata.name]
        reasons.append(f"task mentions the skill name `{metadata.name}`")
    else:
        name_matches = _matched_terms(query_terms, name_text)
        if name_matches:
            score += 0.15 * _coverage(name_matches, _terms(name_text))
            matched_fields["name"] = name_matches
            reasons.append("task overlaps with the skill name")

    description_matches = _matched_terms(query_terms, metadata.description)
    if description_matches:
        score += 0.20 * _coverage(description_matches, query_terms)
        matched_fields["description"] = description_matches
        reasons.append("task overlaps with the skill description")

    trigger_score, matched_triggers, trigger_terms = _score_triggers(query, query_terms, metadata.triggers)
    if trigger_score:
        score += trigger_score
        matched_fields["triggers"] = matched_triggers or trigger_terms
        if matched_triggers:
            reasons.append("task directly matches declared triggers")
        else:
            reasons.append("task partially overlaps with declared triggers")

    heading_matches = _matched_terms(query_terms, " ".join(_instruction_headings(skill.instructions)))
    if heading_matches:
        score += 0.10 * _coverage(heading_matches, query_terms)
        matched_fields["instruction_headings"] = heading_matches
        reasons.append("task overlaps with instruction headings")

    capability_text = " ".join(metadata.capabilities)
    permission_labels = [
        f"{permission.capability}:{permission.scope}:{permission.mode}"
        for permission in metadata.permissions
    ]
    permission_text = " ".join(permission_labels)
    capability_matches = _matched_terms(query_terms, f"{capability_text} {permission_text}")
    matched_permissions = [
        label for label in permission_labels if _matched_terms(query_terms, label.replace("_", " "))
    ]
    if capability_matches:
        score += 0.15 * _coverage(capability_matches, query_terms)
        matched_fields["capabilities_permissions"] = capability_matches
        reasons.append("task overlaps with declared capabilities or permissions")

    score = min(score, 1.0)
    if score == 0:
        reasons.append("no meaningful metadata overlap detected")

    return ActivationMatch(
        skill=skill,
        score=round(score, 4),
        threshold=threshold,
        matched_triggers=matched_triggers,
        matched_permissions=matched_permissions,
        matched_fields=matched_fields,
        reasons=reasons,
    )


def _supports_host(skill: SkillPackage, host: str) -> bool:
    return not skill.metadata.hosts or host in skill.metadata.hosts


def _score_triggers(
    query: str,
    query_terms: set[str],
    triggers: list[str],
) -> tuple[float, list[str], list[str]]:
    if not triggers:
        return 0.0, [], []

    exact_matches: list[str] = []
    partial_terms: set[str] = set()
    best_partial = 0.0

    for trigger in triggers:
        normalized_trigger = _normalize(trigger)
        trigger_terms = _terms(trigger)
        if normalized_trigger and normalized_trigger in query:
            exact_matches.append(trigger)
        matches = _matched_terms(query_terms, trigger)
        if matches:
            partial_terms.update(matches)
            best_partial = max(best_partial, _coverage(matches, trigger_terms))

    score = 0.0
    if exact_matches:
        score += min(0.55, 0.45 + (0.05 * len(exact_matches)))
    if partial_terms:
        score += 0.20 * best_partial
    return min(score, 0.60), exact_matches, sorted(partial_terms)


def _mark_ambiguous_matches(matches: list[ActivationMatch]) -> None:
    if len(matches) < 2:
        return
    top_score = matches[0].score
    ambiguous = [match for match in matches if top_score - match.score <= AMBIGUITY_MARGIN]
    if len(ambiguous) < 2:
        return
    names = ", ".join(match.skill.metadata.name for match in ambiguous)
    for match in ambiguous:
        match.warnings.append(f"ambiguous activation group: {names}")


def _instruction_headings(instructions: str) -> list[str]:
    headings: list[str] = []
    for line in instructions.splitlines():
        match = re.match(r"^#{1,6}\s+(.+)$", line.strip())
        if match:
            headings.append(match.group(1))
    return headings


def _matched_terms(query_terms: set[str], text: str) -> list[str]:
    text_terms = _terms(text)
    return sorted(query_terms & text_terms)


def _coverage(matches: list[str] | set[str], terms: set[str]) -> float:
    if not terms:
        return 0.0
    return min(len(matches) / len(terms), 1.0)


def _terms(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9_]+", text.lower().replace("-", " "))
        if token and token not in STOPWORDS
    }


def _normalize(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9_]+", text.lower().replace("-", " ")))
