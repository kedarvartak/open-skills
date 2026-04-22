# Core

The core feature owns the portable skill package model.

It contains:

- `models.py`: shared dataclasses for skill metadata, permissions, packages, and registry records.
- `loader.py`: `SKILL.md` frontmatter parsing and skill discovery.
- `validator.py`: package structure, metadata, trigger, host, and permission validation.

This layer should stay independent of any specific IDE, registry, or agent host.
