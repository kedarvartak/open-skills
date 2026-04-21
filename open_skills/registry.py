from __future__ import annotations

import json
import shutil
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urljoin, urlparse
from urllib.request import urlopen
from zipfile import ZipFile, ZIP_DEFLATED

from .loader import SkillLoadError, load_skill
from .models import RegistryRelease, RegistrySkillRecord, SkillMetadata, SkillPackage, SkillPermission
from .signing import compute_package_digest, read_signature, verify_package_signature
from .validator import validate_skill

LOCKFILE_NAME = "open-skills.lock.json"


class RegistryError(ValueError):
    """Raised when a registry operation fails."""


def default_registry_path() -> Path:
    return Path(".open-skills/registry").resolve()


def _index_path(registry_root: Path) -> Path:
    return registry_root / "index.json"


def _packages_root(registry_root: Path) -> Path:
    return registry_root / "packages"


def _archives_root(registry_root: Path) -> Path:
    return registry_root / "archives"


def _ensure_registry_layout(registry_root: Path) -> None:
    registry_root.mkdir(parents=True, exist_ok=True)
    _packages_root(registry_root).mkdir(parents=True, exist_ok=True)
    _archives_root(registry_root).mkdir(parents=True, exist_ok=True)
    index_path = _index_path(registry_root)
    if not index_path.exists():
        index_path.write_text(json.dumps({"schema_version": "0.2", "skills": {}}, indent=2) + "\n", encoding="utf-8")


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


def _load_registry_index(registry: str | Path) -> tuple[dict[str, object], str | None]:
    registry_text = str(registry)
    parsed = urlparse(registry_text)
    if parsed.scheme in {"http", "https", "file"}:
        index_url = registry_text if registry_text.endswith(".json") else urljoin(registry_text.rstrip("/") + "/", "index.json")
        with urlopen(index_url, timeout=30) as response:
            return json.loads(response.read().decode("utf-8")), index_url
    root = Path(registry).resolve()
    return _load_index(root), None


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
    index, _ = _load_registry_index(registry_root)
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
                package_digest=str(release_payload.get("package_digest", "")) or None,
                signature=dict(release_payload.get("signature", {})) or None,
                provenance=dict(release_payload.get("provenance", {})),
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
    provenance: dict[str, str] | None = None,
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
    relative_archive_path = Path("archives") / name / f"{version}.zip"
    package_dir = root / relative_package_path
    archive_path = root / relative_archive_path

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
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    if archive_path.exists():
        archive_path.unlink()
    _write_archive(package_dir, archive_path)

    package_digest = compute_package_digest(package_dir)
    signature = read_signature(package_dir)
    signature_payload = asdict(signature) if signature else None

    published_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    release_payload = {
        "package_path": str(relative_archive_path),
        "published_at": published_at,
        "metadata": _metadata_to_dict(skill.metadata),
        "package_digest": package_digest,
        "signature": signature_payload,
        "provenance": provenance or (signature.provenance if signature else {}),
    }
    existing_versions[version] = release_payload

    skill_record = index["skills"][name]
    all_versions = list(skill_record["versions"].keys())
    skill_record["latest_version"] = sorted(all_versions, key=_version_key)[-1]

    _write_index(root, index)

    return RegistryRelease(
        version=version,
        package_path=str(relative_archive_path),
        published_at=published_at,
        metadata=skill.metadata,
        package_digest=package_digest,
        signature=signature_payload,
        provenance=dict(release_payload["provenance"]),
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
            haystacks.extend(latest_release.metadata.triggers)
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
    lockfile: str | Path | None = LOCKFILE_NAME,
    public_key_path: str | Path | None = None,
) -> Path:
    registry_ref = str(registry_root)
    parsed = urlparse(registry_ref)
    is_remote = parsed.scheme in {"http", "https", "file"}
    root = Path(registry_root).resolve() if not is_remote else None
    index, index_url = _load_registry_index(registry_root)
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
    package_ref = str(release_payload.get("package_path", ""))

    destination = Path(destination_root).resolve() / name
    if destination.exists():
        if not force:
            raise RegistryError(f"Destination already exists: {destination}")
        shutil.rmtree(destination)

    destination.parent.mkdir(parents=True, exist_ok=True)
    if is_remote:
        source_url = _resolve_remote_package_url(registry_ref, index_url, package_ref)
        with TemporaryDirectory() as temp_dir:
            archive_path = Path(temp_dir) / f"{name}-{selected_version}.zip"
            _download_file(source_url, archive_path)
            _extract_archive(archive_path, destination)
    else:
        assert root is not None
        package_path = root / package_ref
        if not package_path.exists():
            raise RegistryError(f"Published package path is missing: {package_path}")
        if package_path.is_file() and package_path.suffix == ".zip":
            _extract_archive(package_path, destination)
        else:
            shutil.copytree(package_path, destination, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

    expected_digest = str(release_payload.get("package_digest", ""))
    actual_digest = compute_package_digest(destination)
    if expected_digest and expected_digest != actual_digest:
        shutil.rmtree(destination)
        raise RegistryError("Installed package digest does not match registry metadata")

    if public_key_path:
        verification = verify_package_signature(destination, public_key_path=public_key_path)
        if not verification.ok:
            shutil.rmtree(destination)
            raise RegistryError("; ".join(verification.errors))

    if lockfile:
        _write_lock_entry(
            Path(lockfile),
            name=name,
            version=selected_version,
            registry=registry_ref,
            package_digest=actual_digest,
            signature=dict(release_payload.get("signature", {})),
            provenance=dict(release_payload.get("provenance", {})),
        )
    return destination


def _write_archive(package_dir: Path, archive_path: Path) -> None:
    with ZipFile(archive_path, "w", ZIP_DEFLATED) as archive:
        for path in sorted(item for item in package_dir.rglob("*") if item.is_file()):
            if "__pycache__" in path.parts or path.suffix == ".pyc":
                continue
            archive.write(path, path.relative_to(package_dir).as_posix())


def _extract_archive(archive_path: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    with ZipFile(archive_path) as archive:
        for member in archive.infolist():
            target = destination / member.filename
            if not _is_safe_archive_target(destination, target):
                raise RegistryError(f"Unsafe archive path: {member.filename}")
            archive.extract(member, destination)


def _is_safe_archive_target(destination: Path, target: Path) -> bool:
    destination = destination.resolve()
    return destination == target.resolve() or destination in target.resolve().parents


def _resolve_remote_package_url(registry_ref: str, index_url: str | None, package_ref: str) -> str:
    if urlparse(package_ref).scheme in {"http", "https", "file"}:
        return package_ref
    base = index_url or registry_ref
    if base.endswith(".json"):
        base = base.rsplit("/", 1)[0] + "/"
    return urljoin(base.rstrip("/") + "/", package_ref)


def _download_file(url: str, destination: Path) -> None:
    with urlopen(url, timeout=30) as response:
        destination.write_bytes(response.read())


def _write_lock_entry(
    lockfile: Path,
    *,
    name: str,
    version: str,
    registry: str,
    package_digest: str,
    signature: dict[str, object],
    provenance: dict[str, str],
) -> None:
    payload = {"schema_version": "0.1", "skills": {}}
    if lockfile.exists():
        payload = json.loads(lockfile.read_text(encoding="utf-8"))
    payload.setdefault("skills", {})[name] = {
        "version": version,
        "registry": registry,
        "package_digest": package_digest,
        "signature": signature,
        "provenance": provenance,
    }
    lockfile.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
