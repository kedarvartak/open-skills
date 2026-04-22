from __future__ import annotations

from dataclasses import dataclass, field

from ..core.models import SkillPackage


@dataclass(slots=True)
class HostContext:
    name: str
    capabilities: set[str] = field(default_factory=set)


@dataclass(slots=True)
class CapabilityReport:
    supported: list[str]
    missing: list[str]

    @property
    def ok(self) -> bool:
        return not self.missing


class HostAdapter:
    """Minimal adapter contract for host runtimes."""

    def __init__(self, context: HostContext) -> None:
        self.context = context

    def negotiate(self, skill: SkillPackage) -> CapabilityReport:
        requested = set(skill.metadata.capabilities)
        requested.update(permission.capability for permission in skill.metadata.permissions)
        supported = sorted(requested & self.context.capabilities)
        missing = sorted(requested - self.context.capabilities)
        return CapabilityReport(supported=supported, missing=missing)

    def supports_host(self, skill: SkillPackage) -> bool:
        declared_hosts = set(skill.metadata.hosts)
        return not declared_hosts or self.context.name in declared_hosts
