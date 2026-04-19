# Architecture

Open Skills treats a skill as a portable package plus a host runtime contract.

## Design Principles

1. Portable by default
   A skill package should not assume a specific editor, terminal agent, or model vendor.
2. Explicit capabilities
   Hosts should know what a skill needs before activation or execution.
3. Progressive disclosure
   Load metadata first, full instructions second, references only when needed.
4. Graceful degradation
   If a host cannot support a capability, the skill should still expose the useful subset.
5. Human-readable source of truth
   The skill package should stay easy to author, diff, review, and version-control.

## Skill Package

Minimum package:

```text
my-skill/
  SKILL.md
```

Optional directories:

```text
my-skill/
  SKILL.md
  references/
  scripts/
  assets/
```

## Runtime Layers

### 1. Discovery

Find installed skills from known roots or a registry cache.

### 2. Matching

Determine whether a skill should activate for a task.

### 3. Loading

Load only the metadata first, then the full instructions, then specific supporting files.

### 4. Capability negotiation

Compare what the skill requests against what the host supports.

### 5. Execution

Run scripts or tool calls through host-specific adapters and permission rules.

## MVP Scope

The current MVP in this repository implements:

- package discovery
- frontmatter parsing
- structural validation
- capability declaration parsing

It does not yet implement:

- registry publishing
- signatures
- host-specific execution shims
- semantic routing
- dependency installation
