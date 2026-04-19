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

## Execution Model

Portable skills do not execute themselves. A host runtime is responsible for:

1. discovering skill packages
2. matching them against user intent
3. loading instructions progressively
4. negotiating capabilities
5. executing scripts or tool actions under host safety controls

## Compatibility Goal

The package should remain stable across hosts even when runtime behavior differs.
