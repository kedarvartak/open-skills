# Open Skills Spec Draft

Version: `0.1`

This draft defines the portable core of an Open Skills package.

## Required File

Every skill package must contain:

```text
SKILL.md
```

## Optional Directories

```text
references/
scripts/
assets/
```

## Frontmatter

`SKILL.md` must begin with frontmatter delimited by `---`.

Required keys:

- `name`
- `description`

Recommended keys:

- `version`
- `spec_version`
- `author`
- `license`
- `homepage`
- `capabilities`
- `triggers`
- `permissions`
- `hosts`
- `dependencies`

## Naming Rules

- `name` must use lowercase letters, numbers, and hyphens only
- max length: 64 characters
- package directory name should match `name`

## Capability Rules

Capabilities declare what a skill expects from a host runtime.

Initial common capabilities:

- `read_files`
- `write_files`
- `run_shell`
- `run_python`
- `network_access`
- `mcp_access`

Hosts may support richer internal capabilities, but should map them onto these shared names where possible.

## Trigger Rules

Triggers are matching hints used by host adapters and marketplaces.

Example:

```yaml
triggers:
  - validate skill package
  - inspect skill metadata
  - portable skill example
```

Triggers should be short phrases that describe when the skill is useful. They are not commands and should not grant any extra permission.

## Permission Rules

Permissions declare what a skill may need at runtime. They are more specific than capabilities because they include a scope and a mode.

Compact format:

```yaml
permissions:
  - read_files:workspace:allow
  - write_files:workspace:ask
  - network_access:api:ask
```

Format:

```text
capability:scope:mode
```

Modes:

- `allow`: host may use this permission without another prompt if already trusted
- `ask`: host should request user approval before use
- `deny`: host should treat this permission as unavailable

Scopes are intentionally host-defined in `0.1`. Common scopes include:

- `workspace`
- `skill_package`
- `api`
- `registry`

Capabilities are kept for backward compatibility and coarse host negotiation. New skills should prefer `permissions` while also listing broad `capabilities` when useful for older hosts.

## Signed Packages

Open Skills packages may include:

```text
OPEN_SKILLS_SIGNATURE.json
```

The signature file is generated from a deterministic digest of every package file except:

- `OPEN_SKILLS_SIGNATURE.json`
- `__pycache__/`
- `*.pyc`

Current `0.1` signing uses `hmac-sha256` for local trust domains.

Signature payload:

```json
{
  "signer": "local-dev",
  "algorithm": "hmac-sha256",
  "package_digest": "...",
  "signature": "...",
  "signed_at": "2026-04-20T00:00:00+00:00"
}
```

This is not yet a public-key marketplace trust model. It is a deterministic package-integrity and local-trust mechanism that gives the registry and adapters something concrete to verify.

## Execution Model

Portable skills do not execute themselves. A host runtime is responsible for:

1. discovering skill packages
2. matching them against user intent
3. loading instructions progressively
4. negotiating capabilities
5. negotiating permissions
6. verifying signatures when trust policy requires it
7. executing scripts or tool actions under host safety controls

## Compatibility Goal

The package should remain stable across hosts even when runtime behavior differs.
