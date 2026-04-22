from __future__ import annotations

import re

from .models import SkillPackage

NAME_PATTERN = re.compile(r"^[a-z0-9-]{1,64}$")
PERMISSION_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
PERMISSION_MODES = {"allow", "ask", "deny"}


def validate_skill(skill: SkillPackage) -> list[str]:
    errors: list[str] = []
    metadata = skill.metadata

    if not metadata.name:
        errors.append("Missing required field: name")
    elif not NAME_PATTERN.fullmatch(metadata.name):
        errors.append("Skill name must contain only lowercase letters, numbers, and hyphens")

    if skill.root.name != metadata.name:
        errors.append("Directory name must match metadata.name")

    if not metadata.description:
        errors.append("Missing required field: description")
    elif len(metadata.description) > 1024:
        errors.append("Description must be 1024 characters or fewer")

    if not skill.instructions.strip():
        errors.append("SKILL.md must contain instruction content after frontmatter")

    capabilities = metadata.capabilities
    if any(not item or not isinstance(item, str) for item in capabilities):
        errors.append("Capabilities must be non-empty strings")

    triggers = metadata.triggers
    if any(not item or not isinstance(item, str) for item in triggers):
        errors.append("Triggers must be non-empty strings")

    for permission in metadata.permissions:
        if not PERMISSION_PATTERN.fullmatch(permission.capability):
            errors.append(f"Invalid permission capability: {permission.capability}")
        if not permission.scope:
            errors.append(f"Permission scope is required for {permission.capability}")
        if permission.mode not in PERMISSION_MODES:
            errors.append(
                f"Permission mode for {permission.capability} must be one of: "
                + ", ".join(sorted(PERMISSION_MODES))
            )

    hosts = metadata.hosts
    if any(not item or not isinstance(item, str) for item in hosts):
        errors.append("Hosts must be non-empty strings")

    for dirname in ("references", "scripts", "assets"):
        path = skill.root / dirname
        if path.exists() and not path.is_dir():
            errors.append(f"{dirname}/ must be a directory when present")

    return errors
