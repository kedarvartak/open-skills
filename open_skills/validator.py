from __future__ import annotations

import re

from .models import SkillPackage

NAME_PATTERN = re.compile(r"^[a-z0-9-]{1,64}$")


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

    hosts = metadata.hosts
    if any(not item or not isinstance(item, str) for item in hosts):
        errors.append("Hosts must be non-empty strings")

    for dirname in ("references", "scripts", "assets"):
        path = skill.root / dirname
        if path.exists() and not path.is_dir():
            errors.append(f"{dirname}/ must be a directory when present")

    return errors
