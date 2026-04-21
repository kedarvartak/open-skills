from __future__ import annotations

import json
import shutil
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .loader import SkillLoadError, load_skill
from .models import RegistryRelease, RegistrySkillRecord, SkillMetadata, SkillPackage, SkillPermission
from .validator import validate_skill


class RegistryError(ValueError):
    """Raised when a registry operation fails."""


def default_registry_path() -> Path:
    return Path(".open-skills/registry").resolve()


def _index_path(registry_root: Path) -> Path:
    return registry_root / "index.json"


def _packages_root(registry_root: Path) -> Path:
    return registry_root / "packages"


def _ensure_registry_layout(registry_root: Path) -> None:
    registry_root.mkdir(parents=True, exist_ok=True)
    _packages_root(registry_root).mkdir(parents=True, exist_ok=True)
    index_path = _index_path(registry_root)
    if not index_path.exists():
        index_path.write_text(json.dumps({"skills": {}}, indent=2) + "\n", encoding="utf-8")


def _metadata_from_dict(payload: dict[str, object]) -> SkillMetadata:
    return SkillMetadata(
        name=str(payload.get("name", "")),
        description=str(payload.get("description", "")),
        version=str(payload.get("version", "0.1.0")),
        spec_version=str(payload.get("spec_version", "0.1")),
        author=str(payload["author"]) if payload.get("author") is not None else None,
        homepage=str(payload["homepage"]) if payload.get("homepage") is not None else None,
        license=str(payload["license"]) if payload.get("license") is not None else None,
        capabilities=list(payload.get("capabilities", [])),
        triggers=list(payload.get("triggers", [])),
        permissions=[
            SkillPermission(
                capability=str(item.get("capability", "")),
                scope=str(item.get("scope", "workspace")),
                mode=str(item.get("mode", "ask")),
            )
            for item in list(payload.get("permissions", []))
            if isinstance(item, dict)
        ],
        hosts=list(payload.get("hosts", [])),
        dependencies=list(payload.get("dependencies", [])),
        raw=dict(payload.get("raw", {})),
    )


def _metadata_to_dict(metadata: SkillMetadata) -> dict[str, object]:
    payload = asdict(metadata)
    return payload


def _load_index(registry_root: Path) -> dict[str, object]:
    _ensure_registry_layout(registry_root)
    return json.loads(_index_path(registry_root).read_text(encoding="utf-8"))


def _write_index(registry_root: Path, index: dict[str, object]) -> None:
    _index_path(registry_root).write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")


def _version_key(version: str) -> tuple[int, ...]:
    parts: list[int] = []
    for part in version.split("."):
        try:
            parts.append(int(part))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def load_registry(registry_root: str | Path) -> list[RegistrySkillRecord]:
    root = Path(registry_root).resolve()
    index = _load_index(root)
    records: list[RegistrySkillRecord] = []

    for name, payload in sorted(index.get("skills", {}).items()):
        versions: dict[str, RegistryRelease] = {}
        payload = dict(payload)
        raw_versions = dict(payload.get("versions", {}))
        for version, release_payload in raw_versions.items():
            release_payload = dict(release_payload)
            versions[version] = RegistryRelease(
                version=version,
                package_path=str(release_payload.get("package_path", "")),
                published_at=str(release_payload.get("published_at", "")),
                metadata=_metadata_from_dict(dict(release_payload.get("metadata", {}))),
            )
        latest_version = str(payload.get("latest_version", ""))
        if not latest_version and versions:
            latest_version = sorted(versions, key=_version_key)[-1]
        records.append(
            RegistrySkillRecord(
                name=str(name),
                latest_version=latest_version,
                versions=versions,
            )
        )

    return records


def publish_skill(
    skill_root: str | Path,
    registry_root: str | Path,
    *,
    force: bool = False,
) -> RegistryRelease:
    try:
        skill = load_skill(skill_root)
    except SkillLoadError as exc:
        raise RegistryError(str(exc)) from exc

    errors = validate_skill(skill)
    if errors:
        raise RegistryError("; ".join(errors))

    root = Path(registry_root).resolve()
    index = _load_index(root)

    name = skill.metadata.name
    version = skill.metadata.version
    relative_package_path = Path("packages") / name / version
    package_dir = root / relative_package_path

    existing_versions = (
        index.setdefault("skills", {})
        .setdefault(name, {})
        .setdefault("versions", {})
    )
    if version in existing_versions and not force:
        raise RegistryError(f"{name}@{version} already exists in registry")

    if package_dir.exists():
        if not force:
            raise RegistryError(f"Registry package path already exists: {package_dir}")
        shutil.rmtree(package_dir)

    package_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(skill.root, package_dir, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

    published_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    release_payload = {
        "package_path": str(relative_package_path),
        "published_at": published_at,
        "metadata": _metadata_to_dict(skill.metadata),
    }
    existing_versions[version] = release_payload

    skill_record = index["skills"][name]
    all_versions = list(skill_record["versions"].keys())
    skill_record["latest_version"] = sorted(all_versions, key=_version_key)[-1]

    _write_index(root, index)

    return RegistryRelease(
        version=version,
        package_path=str(relative_package_path),
        published_at=published_at,
        metadata=skill.metadata,
    )


def search_registry(registry_root: str | Path, query: str | None = None) -> list[RegistrySkillRecord]:
    records = load_registry(registry_root)
    if not query:
        return records

    needle = query.lower()
    matches: list[RegistrySkillRecord] = []
    for record in records:
        latest_release = record.versions.get(record.latest_version)
        haystacks = [record.name]
        if latest_release:
            haystacks.append(latest_release.metadata.description)
            haystacks.extend(latest_release.metadata.capabilities)
            haystacks.extend(latest_release.metadata.hosts)
        joined = " ".join(haystacks).lower()
        if needle in joined:
            matches.append(record)
    return matches


def install_skill(
    name: str,
    registry_root: str | Path,
    destination_root: str | Path,
    *,
    version: str | None = None,
    force: bool = False,
) -> Path:
    root = Path(registry_root).resolve()
    index = _load_index(root)
    skill_payload = dict(index.get("skills", {}).get(name, {}))
    if not skill_payload:
        raise RegistryError(f"Skill not found in registry: {name}")

    versions = dict(skill_payload.get("versions", {}))
    selected_version = version or str(skill_payload.get("latest_version", ""))
    if not selected_version:
        raise RegistryError(f"No versions available for skill: {name}")
    if selected_version not in versions:
        raise RegistryError(f"Version not found for {name}: {selected_version}")

    release_payload = dict(versions[selected_version])
    package_path = root / str(release_payload.get("package_path", ""))
    if not package_path.exists():
        raise RegistryError(f"Published package path is missing: {package_path}")

    destination = Path(destination_root).resolve() / name
    if destination.exists():
        if not force:
            raise RegistryError(f"Destination already exists: {destination}")
        shutil.rmtree(destination)

    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(package_path, destination, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    return destination
