from __future__ import annotations

from pathlib import Path

from .models import SkillMetadata, SkillPackage


class SkillLoadError(ValueError):
    """Raised when a skill package cannot be loaded."""


def _parse_scalar(value: str) -> str:
    value = value.strip()
    if value.startswith(("\"", "'")) and value.endswith(("\"", "'")) and len(value) >= 2:
        return value[1:-1]
    return value


def _parse_list(value: str) -> list[str]:
    value = value.strip()
    if not value:
        return []
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(item.strip()) for item in inner.split(",")]
    return [_parse_scalar(value)]


def _parse_frontmatter(text: str) -> tuple[dict[str, object], str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise SkillLoadError("SKILL.md must start with YAML-style frontmatter delimited by ---")

    frontmatter: dict[str, object] = {}
    end_index = None

    for index in range(1, len(lines)):
        line = lines[index]
        if line.strip() == "---":
            end_index = index
            break
        if not line.strip():
            continue
        if ":" not in line:
            raise SkillLoadError(f"Invalid frontmatter line: {line}")
        key, raw_value = line.split(":", 1)
        key = key.strip()
        raw_value = raw_value.strip()
        if raw_value.startswith("["):
            frontmatter[key] = _parse_list(raw_value)
        else:
            frontmatter[key] = _parse_scalar(raw_value)

    if end_index is None:
        raise SkillLoadError("SKILL.md frontmatter is missing a closing ---")

    body = "\n".join(lines[end_index + 1 :]).strip()
    return frontmatter, body


def load_skill(skill_root: str | Path) -> SkillPackage:
    root = Path(skill_root).resolve()
    skill_file = root / "SKILL.md"

    if not root.exists():
        raise SkillLoadError(f"Skill path does not exist: {root}")
    if not root.is_dir():
        raise SkillLoadError(f"Skill path is not a directory: {root}")
    if not skill_file.exists():
        raise SkillLoadError(f"Missing SKILL.md in {root}")

    text = skill_file.read_text(encoding="utf-8")
    raw_metadata, instructions = _parse_frontmatter(text)

    metadata = SkillMetadata(
        name=str(raw_metadata.get("name", "")),
        description=str(raw_metadata.get("description", "")),
        version=str(raw_metadata.get("version", "0.1.0")),
        spec_version=str(raw_metadata.get("spec_version", "0.1")),
        author=str(raw_metadata["author"]) if "author" in raw_metadata else None,
        homepage=str(raw_metadata["homepage"]) if "homepage" in raw_metadata else None,
        license=str(raw_metadata["license"]) if "license" in raw_metadata else None,
        capabilities=list(raw_metadata.get("capabilities", [])),
        hosts=list(raw_metadata.get("hosts", [])),
        dependencies=list(raw_metadata.get("dependencies", [])),
        raw=raw_metadata,
    )

    return SkillPackage(root=root, metadata=metadata, instructions=instructions)


def discover_skills(root_dir: str | Path) -> list[Path]:
    root = Path(root_dir).resolve()
    if not root.exists():
        return []
    return sorted(path.parent for path in root.glob("*/SKILL.md"))
