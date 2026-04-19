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
- instructions
- examples
- references
- assets
- declared capabilities

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
  loader.py
  models.py
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

## Near-Term Roadmap

1. Expand the metadata contract into a versioned spec.
2. Add packaging and registry publishing commands.
3. Add host adapters for Claude-style, Codex-style, and editor-extension runtimes.
4. Add semantic skill matching and capability negotiation.
5. Add signatures, trust policies, and marketplace metadata.
