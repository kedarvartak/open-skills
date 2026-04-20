from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


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
    hosts: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    raw: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class SkillPackage:
    root: Path
    metadata: SkillMetadata
    instructions: str

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


@dataclass(slots=True)
class RegistrySkillRecord:
    name: str
    latest_version: str
    versions: dict[str, RegistryRelease] = field(default_factory=dict)
