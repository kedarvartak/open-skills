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

The current implementation lives in `open_skills/adapters/codex.py`.

It supports:

- discovering valid installed skills
- matching installed skills against a task string
- checking whether `codex` is a declared host
- negotiating requested capabilities against Codex defaults
- rendering a Codex-ready context block for injection by a host, extension, or wrapper

Default Codex capabilities:

- `read_files`
- `write_files`
- `run_shell`
- `run_python`

The adapter intentionally does not execute scripts directly. It exposes script paths and capability warnings so the Codex host can decide whether to request permission or skip unsupported behavior.

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
