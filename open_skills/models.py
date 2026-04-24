from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class SkillPermission:
    capability: str
    scope: str = "workspace"
    mode: str = "ask"


@dataclass(slots=True)
class SkillMetadata:
    name: str
    description: str
    version: str = "0.1.0"
    spec_version: str = "0.1"
    author: str | None = None
    homepage: str | None = None
    license: str | None = None
    capabilities: list[str] = field(default_factory=list)
    triggers: list[str] = field(default_factory=list)
    permissions: list[SkillPermission] = field(default_factory=list)
    hosts: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    raw: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class SkillPackage:
    root: Path
    metadata: SkillMetadata
    instructions: str
    reference_manifests: list["SkillResourceManifest"] = field(default_factory=list)
    script_manifests: list["SkillResourceManifest"] = field(default_factory=list)
    asset_manifests: list["SkillResourceManifest"] = field(default_factory=list)

    @property
    def skill_file(self) -> Path:
        return self.root / "SKILL.md"

    @property
    def references_dir(self) -> Path:
        return self.root / "references"

    @property
    def scripts_dir(self) -> Path:
        return self.root / "scripts"

    @property
    def assets_dir(self) -> Path:
        return self.root / "assets"


@dataclass(slots=True)
class RegistryRelease:
    version: str
    package_path: str
    published_at: str
    metadata: SkillMetadata
    package_digest: str | None = None
    signature: dict[str, object] | None = None
    provenance: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class RegistrySkillRecord:
    name: str
    latest_version: str
    versions: dict[str, RegistryRelease] = field(default_factory=dict)


@dataclass(slots=True)
class SkillResourceManifest:
    path: str
    when: str | None = None
    summary: str | None = None


@dataclass(slots=True)
class MaterializedResource:
    path: Path
    relative_path: str
    kind: str
    when: str | None = None
    summary: str | None = None
    size_chars: int = 0
    selected: bool = False
    content: str | None = None
    truncated: bool = False


@dataclass(slots=True)
class SkillMaterialization:
    stage: str
    skill: SkillPackage
    task: str | None = None
    max_chars: int | None = None
    metadata: dict[str, object] = field(default_factory=dict)
    instructions: str | None = None
    references: list[MaterializedResource] = field(default_factory=list)
    assets: list[MaterializedResource] = field(default_factory=list)
    scripts: list[MaterializedResource] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    total_chars: int = 0
