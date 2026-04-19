# Host Adapters

Host adapters make a portable skill usable inside a specific tool.

## Adapter Responsibilities

Every adapter should answer the same questions:

1. Where are skills discovered from?
2. How does the host choose a skill?
3. How are capabilities mapped to host tools?
4. How are permissions and safety checks enforced?
5. How are scripts or references exposed to the agent?

## Claude-Style Adapter

Maps closely to the original skills model:

- reads skill metadata for matching
- loads `SKILL.md` when relevant
- loads `references/` and `assets/` lazily
- may execute `scripts/` if the runtime allows it

## Codex-Style Adapter

Wraps the skill package into:

- a system/developer prompt fragment
- optional tool-use hints
- capability checks against local execution tools
- a local workspace resolver for assets and references

## Cursor / VS Code Adapter

Likely implemented as an extension or sidecar service:

- syncs installed skills from a local registry cache
- exposes skill metadata inside the editor UI
- injects selected or auto-matched skill instructions into agent sessions
- enforces editor and workspace permissions

## Universal Capability Names

The first shared vocabulary should stay small:

- `read_files`
- `write_files`
- `run_shell`
- `run_python`
- `network_access`
- `mcp_access`

Hosts can map these to richer internal permission models.

## Adapter API Shape

An adapter can eventually implement an interface like:

```text
discover() -> list[SkillSummary]
match(task, skills) -> list[SkillSummary]
negotiate(skill, host_capabilities) -> CapabilityReport
materialize(skill) -> LoadedSkill
execute(skill, context) -> SkillRunResult
```

That keeps the portable package stable even if host behavior differs a lot.
