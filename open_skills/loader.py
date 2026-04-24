from __future__ import annotations

from pathlib import Path

from .models import (
    MaterializedResource,
    SkillMaterialization,
    SkillMetadata,
    SkillPackage,
    SkillPermission,
    SkillResourceManifest,
)

MATERIALIZATION_STAGES = ("metadata", "instructions", "references", "assets", "scripts")
LARGE_RESOURCE_WARNING_CHARS = 4_000
LARGE_PACKAGE_WARNING_CHARS = 16_000


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


def _coerce_string_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return _parse_list(str(value))


def _parse_permission(value: str) -> SkillPermission:
    capability, *rest = [part.strip() for part in value.split(":")]
    scope = rest[0] if len(rest) >= 1 and rest[0] else "workspace"
    mode = rest[1] if len(rest) >= 2 and rest[1] else "ask"
    return SkillPermission(capability=capability, scope=scope, mode=mode)


def _parse_permissions(value: object) -> list[SkillPermission]:
    return [_parse_permission(item) for item in _coerce_string_list(value)]


def _parse_frontmatter(text: str) -> tuple[dict[str, object], str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise SkillLoadError("SKILL.md must start with YAML-style frontmatter delimited by ---")

    frontmatter: dict[str, object] = {}
    end_index = None

    current_list_key: str | None = None
    current_mapping_item: dict[str, object] | None = None

    for index in range(1, len(lines)):
        line = lines[index]
        if line.strip() == "---":
            end_index = index
            break
        if not line.strip():
            continue

        stripped = line.strip()
        if current_mapping_item and line.startswith("  ") and ":" in stripped and not stripped.startswith("- "):
            key, raw_value = stripped.split(":", 1)
            current_mapping_item[key.strip()] = _parse_scalar(raw_value.strip())
            continue
        if current_list_key and stripped.startswith("- "):
            raw_item = stripped[2:].strip()
            frontmatter.setdefault(current_list_key, [])
            assert isinstance(frontmatter[current_list_key], list)
            if raw_item and (": " in raw_item or raw_item.endswith(":")):
                item_key, raw_value = raw_item.split(":", 1)
                current_mapping_item = {item_key.strip(): _parse_scalar(raw_value.strip())}
                frontmatter[current_list_key].append(current_mapping_item)
            else:
                current_mapping_item = None
                frontmatter[current_list_key].append(_parse_scalar(raw_item))
            continue

        if ":" not in line:
            raise SkillLoadError(f"Invalid frontmatter line: {line}")
        key, raw_value = line.split(":", 1)
        key = key.strip()
        raw_value = raw_value.strip()
        current_list_key = None
        current_mapping_item = None
        if not raw_value:
            frontmatter[key] = []
            current_list_key = key
            continue
        if raw_value.startswith("["):
            frontmatter[key] = _parse_list(raw_value)
        else:
            frontmatter[key] = _parse_scalar(raw_value)

    if end_index is None:
        raise SkillLoadError("SKILL.md frontmatter is missing a closing ---")

    body = "\n".join(lines[end_index + 1 :]).strip()
    return frontmatter, body


def _parse_resource_manifests(
    value: object,
    *,
    directory: str,
) -> list[SkillResourceManifest]:
    manifests: list[SkillResourceManifest] = []
    if value is None:
        return manifests
    if not isinstance(value, list):
        value = _parse_list(str(value))

    for item in value:
        if isinstance(item, dict):
            path = str(item.get("path", "")).strip()
            if not path:
                continue
            manifests.append(
                SkillResourceManifest(
                    path=path,
                    when=str(item["when"]).strip() if "when" in item else None,
                    summary=str(item["summary"]).strip() if "summary" in item else None,
                )
            )
            continue

        path = str(item).strip()
        if not path:
            continue
        normalized = path if "/" in path else f"{directory}/{path}"
        manifests.append(SkillResourceManifest(path=normalized))
    return manifests


def _auto_resource_manifests(root: Path, directory: str) -> list[SkillResourceManifest]:
    base = root / directory
    if not base.exists() or not base.is_dir():
        return []
    return [
        SkillResourceManifest(path=str(path.relative_to(root)))
        for path in sorted(item for item in base.rglob("*") if item.is_file())
    ]


def _tokenize(value: str) -> set[str]:
    return {
        token
        for token in "".join(ch.lower() if ch.isalnum() else " " for ch in value).split()
        if len(token) >= 3
    }


def _matches_task(task: str | None, manifest: SkillResourceManifest) -> bool:
    if not task:
        return manifest.when is None
    if not manifest.when:
        return True

    task_tokens = _tokenize(task)
    when_tokens = _tokenize(manifest.when)
    if not when_tokens:
        return True
    return bool(task_tokens & when_tokens)


def _summarize_text(text: str, limit: int = 220) -> str:
    compact = " ".join(line.strip() for line in text.splitlines() if line.strip())
    if len(compact) <= limit:
        return compact
    return compact[: max(0, limit - 3)].rstrip() + "..."


def _read_resource_content(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ""


def _budget_slice(content: str, remaining: int | None) -> tuple[str | None, bool, int]:
    if remaining is not None and remaining <= 0:
        return None, False, 0
    if remaining is None or len(content) <= remaining:
        return content, False, len(content)
    return content[:remaining], True, remaining


def _materialize_resources(
    skill: SkillPackage,
    manifests: list[SkillResourceManifest],
    *,
    kind: str,
    task: str | None,
    include_content: bool,
    remaining_chars: int | None,
) -> tuple[list[MaterializedResource], int]:
    resources: list[MaterializedResource] = []
    used_chars = 0

    for manifest in manifests:
        path = (skill.root / manifest.path).resolve()
        if not path.exists() or not path.is_file():
            continue

        content = _read_resource_content(path)
        summary = manifest.summary or _summarize_text(content or manifest.path)
        selected = _matches_task(task, manifest)
        resource_content: str | None = None
        truncated = False
        if include_content and selected:
            remaining = None if remaining_chars is None else max(0, remaining_chars - used_chars)
            resource_content, truncated, consumed = _budget_slice(content, remaining)
            used_chars += consumed
        resources.append(
            MaterializedResource(
                path=path,
                relative_path=str(path.relative_to(skill.root)),
                kind=kind,
                when=manifest.when,
                summary=summary,
                size_chars=len(content),
                selected=selected,
                content=resource_content,
                truncated=truncated,
            )
        )
    return resources, used_chars


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
        capabilities=_coerce_string_list(raw_metadata.get("capabilities", [])),
        triggers=_coerce_string_list(raw_metadata.get("triggers", [])),
        permissions=_parse_permissions(raw_metadata.get("permissions", [])),
        hosts=_coerce_string_list(raw_metadata.get("hosts", [])),
        dependencies=_coerce_string_list(raw_metadata.get("dependencies", [])),
        raw=raw_metadata,
    )

    reference_manifests = _parse_resource_manifests(
        raw_metadata.get("references"),
        directory="references",
    ) or _auto_resource_manifests(root, "references")
    script_manifests = _parse_resource_manifests(
        raw_metadata.get("scripts"),
        directory="scripts",
    ) or _auto_resource_manifests(root, "scripts")
    asset_manifests = _parse_resource_manifests(
        raw_metadata.get("assets"),
        directory="assets",
    ) or _auto_resource_manifests(root, "assets")

    return SkillPackage(
        root=root,
        metadata=metadata,
        instructions=instructions,
        reference_manifests=reference_manifests,
        script_manifests=script_manifests,
        asset_manifests=asset_manifests,
    )


def materialize_skill(
    skill: SkillPackage,
    *,
    stage: str = "metadata",
    task: str | None = None,
    max_chars: int | None = None,
) -> SkillMaterialization:
    if stage not in MATERIALIZATION_STAGES:
        valid = ", ".join(MATERIALIZATION_STAGES)
        raise SkillLoadError(f"Unsupported materialization stage `{stage}`. Expected one of: {valid}")

    metadata_payload: dict[str, object] = {
        "name": skill.metadata.name,
        "description": skill.metadata.description,
        "version": skill.metadata.version,
        "spec_version": skill.metadata.spec_version,
        "capabilities": list(skill.metadata.capabilities),
        "triggers": list(skill.metadata.triggers),
        "hosts": list(skill.metadata.hosts),
        "dependencies": list(skill.metadata.dependencies),
        "permissions": [
            {
                "capability": permission.capability,
                "scope": permission.scope,
                "mode": permission.mode,
            }
            for permission in skill.metadata.permissions
        ],
    }

    materialization = SkillMaterialization(
        stage=stage,
        skill=skill,
        task=task,
        max_chars=max_chars,
        metadata=metadata_payload,
    )
    total_chars = len(str(metadata_payload))

    if stage == "metadata":
        materialization.total_chars = total_chars
        materialization.warnings.extend(_materialization_warnings(skill, materialization))
        return materialization

    remaining = None if max_chars is None else max(0, max_chars - total_chars)
    instructions, instructions_truncated, used_instruction_chars = _budget_slice(
        skill.instructions,
        remaining,
    )
    materialization.instructions = instructions
    total_chars += used_instruction_chars
    if instructions_truncated:
        materialization.warnings.append("Instruction body was truncated to fit the materialization budget.")

    if stage in {"references", "assets", "scripts"}:
        resources, used = _materialize_resources(
            skill,
            skill.reference_manifests,
            kind="reference",
            task=task,
            include_content=stage == "references",
            remaining_chars=None if max_chars is None else max(0, max_chars - total_chars),
        )
        materialization.references = resources
        total_chars += used

    if stage in {"assets", "scripts"}:
        resources, used = _materialize_resources(
            skill,
            skill.asset_manifests,
            kind="asset",
            task=task,
            include_content=stage == "assets",
            remaining_chars=None if max_chars is None else max(0, max_chars - total_chars),
        )
        materialization.assets = resources
        total_chars += used

    if stage == "scripts":
        resources, used = _materialize_resources(
            skill,
            skill.script_manifests,
            kind="script",
            task=task,
            include_content=True,
            remaining_chars=None if max_chars is None else max(0, max_chars - total_chars),
        )
        materialization.scripts = resources
        total_chars += used

    materialization.total_chars = total_chars
    materialization.warnings.extend(_materialization_warnings(skill, materialization))
    return materialization


def _materialization_warnings(
    skill: SkillPackage,
    materialization: SkillMaterialization,
) -> list[str]:
    warnings: list[str] = []
    if materialization.total_chars > LARGE_PACKAGE_WARNING_CHARS:
        warnings.append(
            "This skill materialization is large and may be too eager for host context injection."
        )

    for resource in (
        list(materialization.references) + list(materialization.assets) + list(materialization.scripts)
    ):
        if resource.size_chars > LARGE_RESOURCE_WARNING_CHARS:
            warnings.append(
                f"{resource.relative_path} is large ({resource.size_chars} chars); prefer summaries or narrower manifests."
            )
        if resource.selected and resource.when is None and resource.kind == "reference":
            warnings.append(
                f"{resource.relative_path} has no `when` selector, so it is always eligible during reference loading."
            )

    if skill.reference_manifests and all(manifest.when is None for manifest in skill.reference_manifests):
        warnings.append("Reference manifests do not include `when` selectors yet, so progressive loading is coarse.")
    return warnings


def discover_skills(root_dir: str | Path) -> list[Path]:
    root = Path(root_dir).resolve()
    if not root.exists():
        return []
    return sorted(path.parent for path in root.glob("*/SKILL.md"))
