---
name: hello-skill
description: A minimal example skill for the Open Skills format that demonstrates portable metadata, instructions, and capability declarations.
version: 0.1.0
spec_version: 0.1
author: Open Skills
license: MIT
capabilities: [read_files]
hosts: [claude-code, codex, cursor, vscode]
dependencies: []
---

# Hello Skill

This is a minimal portable skill package.

Use this skill when:

- you want to validate the package format
- you want an example for authoring a new skill
- you want to test host adapter loading

## Instructions

When activated, the host should:

1. Load this file's metadata first.
2. Present the description to the skill matching layer.
3. Load the instruction body only when the task matches.
4. Respect the declared capabilities before attempting tool use.

## Notes

This skill intentionally does not require scripts or references so it can run as the simplest possible compatibility test.
