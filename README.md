# Open Skills

Open Skills is a universal framework for portable AI agent skills.

The goal is simple:

- author a skill once
- validate it with a common toolchain
- run it across multiple hosts like Claude Code, Codex, Cursor, VS Code, and others

This repository starts with the first practical building blocks:

- a portable skill package layout
- a lightweight `SKILL.md` metadata contract
- a Python CLI for discovery and validation
- a minimal host adapter contract for capability negotiation
- adapter docs that separate portable skills from host-specific runtime behavior

## Core Idea

A skill should be portable at the package level and adaptable at the runtime level.

Portable pieces:

- skill metadata
- triggers
- instructions
- examples
- references
- assets
- declared capabilities
- declared permissions
- optional package signatures

Host-specific pieces:

- discovery
- matching
- permission prompts
- tool mapping
- script execution
- UI and marketplace integration

## Repository Layout

```text
docs/
  spec.md
  architecture.md
  adapters.md
open_skills/
  __init__.py
  adapters.py
  cli.py
  codex_adapter.py
  loader.py
  models.py
  registry.py
  signing.py
  validator.py
skills/
  hello-skill/
    SKILL.md
pyproject.toml
```

## Quick Start

List skills in a directory:

```bash
python3 -m open_skills.cli list ./skills
```

Validate a skill package:

```bash
python3 -m open_skills.cli validate ./skills/hello-skill
```

Show parsed metadata:

```bash
python3 -m open_skills.cli inspect ./skills/hello-skill
```

Compute, sign, and verify a package:

```bash
python3 -m open_skills.cli digest ./skills/hello-skill
python3 -m open_skills.cli sign ./skills/hello-skill --signer local-dev --key dev-secret
python3 -m open_skills.cli verify ./skills/hello-skill --key dev-secret
```

List skills available to the Codex adapter:

```bash
python3 -m open_skills.cli codex list --skills-dir ./installed-skills
```

Match installed skills for a task:

```bash
python3 -m open_skills.cli codex match "validate a portable skill" --skills-dir ./installed-skills
```

Render a skill into Codex-ready context:

```bash
python3 -m open_skills.cli codex render hello-skill --skills-dir ./installed-skills
```

Publish a skill to the local registry:

```bash
python3 -m open_skills.cli publish ./skills/hello-skill
```

Search the local registry:

```bash
python3 -m open_skills.cli search hello
```

Install from the local registry:

```bash
python3 -m open_skills.cli install hello-skill
```

By default, the local registry lives at `.open-skills/registry` and installs go to `./installed-skills`.

## Near-Term Roadmap

1. Add public-key signing, provenance, and trust policies.
2. Add remote registries and marketplace sync.
3. Add host adapters for Claude-style, Codex-style, and editor-extension runtimes.
4. Add semantic skill matching and capability negotiation.
5. Add remote registries and marketplace sync.
