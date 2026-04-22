# Open Skills TODO

This document tracks the next product priorities for Open Skills.

The current focus is not production distribution polish. The priority is to make the core skill experience excellent: authoring, discovery, activation, context loading, permissions, and host portability.

## Production Caveat

The current public-key signing implementation is useful for proving the trust and distribution model, but it should not be treated as production-grade cryptography.

Before production release:

- Replace the pure-Python RSA internals with an audited library such as `cryptography`, Sigstore, Minisign, or another mature signing stack.
- Add key rotation, revocation, publisher allowlists, and trust policy files.
- Add signed registry indexes, not only signed packages.
- Add CI tests that verify tampering, wrong-key verification, digest mismatch, and archive path traversal cases.

This caveat should stay visible until the signing layer is replaced or independently reviewed.

## Product Direction

Claude Code skills prove that reusable agent instructions are valuable. Open Skills should do that too, but with a broader promise:

- Skills should work across agents and IDEs.
- Skills should be easy to author and debug.
- Skills should activate reliably without manual folder thinking.
- Skills should expose permissions clearly before they influence the agent.
- Skills should be portable packages, not hidden behavior tied to one vendor.

The distribution layer matters, but it should support the core workflow instead of becoming the product too early.

## Comparison With Claude Code Skills

| Area | Claude Code Skills | Open Skills Target |
| --- | --- | --- |
| Package format | Folder with `SKILL.md` and optional resources | Same simple package model, plus portable metadata and adapter contracts |
| Activation | Host-specific skill discovery and matching | Cross-host trigger matching with inspectable scoring and debug output |
| Portability | Best inside Claude/Anthropic environments | Works across Codex, Cursor, VS Code, Claude-style hosts, and future agent runtimes |
| Permissions | Mostly host/runtime controlled | Skill-declared permissions plus host negotiation and visible warnings |
| Authoring | Markdown-first, simple | Markdown-first, with linting, previews, templates, examples, and tests |
| Debugging | Limited visibility into why a skill activates | Explain why a skill matched, what context loaded, and which permissions were used |
| Composition | Skill use is mostly implicit | Explicit support for skill chaining, conflicts, dependencies, and priority rules |
| Marketplace | Vendor/platform tied | Open registry format, local/global installs, remote indexes, version pinning |

The goal is not to clone Claude Code. The goal is to keep the simplicity while adding portability, transparency, and better tooling.

## Priority 1: Skill Activation Engine

Build a real activation layer that decides which skills apply to a user task.

Status: initial implementation exists via `python3 -m open_skills.cli activate`.

Why this matters:

If activation is weak, the whole product feels like a folder manager. The magic is not the `SKILL.md` file. The magic is knowing when and how to use it.

Core features:

- Add an `activate` CLI command that takes a task string and returns ranked matching skills.
- Score using `name`, `description`, `triggers`, `capabilities`, `permissions`, and instruction headings.
- Return a clear explanation for each match.
- Support activation thresholds: `strict`, `balanced`, and `broad`.
- Support host filters, for example `--host codex`.
- Detect when no skill should activate.
- Detect ambiguous matches and show why they conflict.

Example:

```bash
python3 -m open_skills.cli activate "debug my pytest failure" --skills-dir ~/.open-skills/skills --host codex --explain
```

Expected output:

```text
pytest-debugger@1.2.0 score=0.86
matched triggers: debug pytest failure, inspect stack trace
matched permissions: read_files:workspace:allow, run_shell:workspace:ask
reason: task mentions pytest and debugging; skill specializes in test failure triage
```

How this beats Claude Code:

- Users can see why a skill activated.
- Hosts can share the same activation behavior.
- Developers can tune skills without guessing.

## Priority 2: Progressive Context Loader

Implement progressive disclosure as a first-class runtime behavior.

Why this matters:

Skills can become bloated if the host loads everything immediately. We need the runtime to load only the right amount of context at the right time.

Core features:

- Add a `materialize` API that returns staged context:
  - metadata only
  - instruction body
  - selected references
  - selected assets
  - selected scripts
- Add reference manifests so skills can describe when files are relevant.
- Add max-token or max-character budgets for materialization.
- Add summaries for large references.
- Add warnings when a skill package is too large or too eager.
- Add adapter-friendly JSON output.

Example package metadata:

```yaml
references:
  - path: references/debugging.md
    when: task mentions stack traces, logs, or failures
  - path: references/pytest.md
    when: task mentions pytest
```

How this beats Claude Code:

- Context loading becomes portable and inspectable.
- IDEs can preview what will be injected.
- Large skill packages remain usable without flooding the model.

## Priority 3: Skill Authoring Toolkit

Make skill creation dramatically easier.

Why this matters:

If authoring is annoying, the marketplace will be empty. Great skill ecosystems need great author tools.

Core features:

- Add `new` command to scaffold skills from templates.
- Add templates for common skill types:
  - coding workflow
  - API integration
  - debugging workflow
  - design review
  - data analysis
  - repo-specific team workflow
- Add `lint` command with actionable feedback.
- Add `preview` command to show how the skill will appear to a host.
- Add `test` command with fixture tasks and expected activation results.
- Add `doctor` command to catch missing files, oversized references, weak triggers, and unsafe permissions.

Example:

```bash
python3 -m open_skills.cli new pytest-debugger --template debugging
python3 -m open_skills.cli lint ./skills/pytest-debugger
python3 -m open_skills.cli test ./skills/pytest-debugger
```

How this beats Claude Code:

- Skill authors get feedback before publishing.
- Teams can test whether a skill activates correctly.
- Marketplace quality improves because bad packages are easier to catch.

## Priority 4: Host Adapter SDK

Turn adapters into a formal SDK.

Why this matters:

The project only wins if different tools can integrate Open Skills without each host reinventing behavior.

Core features:

- Define a stable `HostAdapter` protocol.
- Add shared adapter lifecycle:
  - discover
  - activate
  - negotiate permissions
  - materialize context
  - report execution hints
- Add adapter capability profiles:
  - `codex`
  - `claude-code`
  - `cursor`
  - `vscode`
  - `generic-cli`
- Add compatibility reports for each skill.
- Add adapter conformance tests.

How this beats Claude Code:

- Claude skills are excellent inside one host.
- Open Skills can become predictable across many hosts.

## Priority 5: Permission UX And Safety Model

Make permissions understandable before a skill affects an agent.

Why this matters:

Skills are instructions that can influence tool use. Users should understand what a skill may ask the agent to do.

Core features:

- Add a permission report command.
- Group permissions by risk level.
- Show why each permission is requested.
- Support permission modes:
  - `allow`
  - `ask`
  - `deny`
- Support host-specific permission mapping.
- Warn when instructions mention behavior not declared in permissions.

Example:

```bash
python3 -m open_skills.cli permissions ./skills/deploy-helper --host codex
```

How this beats Claude Code:

- Permission expectations become visible and portable.
- Hosts can make safer choices with less custom logic.

## Priority 6: Skill Composition And Conflict Handling

Support multiple skills without making the agent confused.

Why this matters:

Real tasks often need more than one skill. But blindly stacking instructions creates conflicts.

Core features:

- Add skill priority rules.
- Add dependency declarations.
- Add conflict declarations.
- Detect overlapping permissions.
- Detect contradictory runtime instructions.
- Materialize multiple skills into a single ordered context bundle.

Example:

```yaml
depends_on: [python-debugging]
conflicts_with: [jest-debugger]
priority: 80
```

How this beats Claude Code:

- Skill use becomes composable instead of accidental.
- Teams can build skill sets, not just isolated skill folders.

## Priority 7: Global Skill Store

Move installed skills out of project repos by default.

Why this matters:

Repo-local `installed-skills/` is fine for development, but users should not have every project bloated with installed packages.

Core features:

- Use a user-level default store:
  - Linux: `~/.local/share/open-skills`
  - macOS: `~/Library/Application Support/open-skills`
  - Windows: `%APPDATA%\\open-skills`
- Keep project-level `open-skills.lock.json`.
- Support optional vendoring for teams that want checked-in skills.
- Add `where` command to show active store paths.

How this beats Claude Code:

- Skills become portable across tools and repos.
- Projects can pin versions without copying packages everywhere.

## Priority 8: Skill Test Harness

Let authors prove a skill works.

Why this matters:

Marketplace quality depends on repeatable tests.

Core features:

- Add `tests/activation.json` fixtures.
- Add expected match thresholds.
- Add expected permission reports.
- Add expected materialized context snapshots.
- Add CI-friendly output.

Example:

```json
[
  {
    "task": "fix this pytest fixture error",
    "should_match": true,
    "minimum_score": 0.75
  }
]
```

How this beats Claude Code:

- Skills can be reviewed and tested like software.
- Marketplace ranking can use quality signals instead of only popularity.

## Near-Term Implementation Order

1. Implement `activate` with explainable scoring.
2. Implement staged `materialize` with context budgets.
3. Implement `new`, `lint`, `preview`, and `test`.
4. Formalize the adapter SDK and conformance tests.
5. Add permission reports and host-specific mapping.
6. Add composition rules for multi-skill activation.
7. Move installs to a global user store with project lockfiles.
8. Return to production-grade trust, registry sync, and marketplace features.

## Definition Of Better Than Claude Code

Open Skills becomes meaningfully better when a user can:

- Install a skill once and use it in multiple IDEs.
- Understand why a skill activated.
- Preview exactly what context will be injected.
- Know what permissions a skill may request.
- Test a skill before publishing it.
- Pin a skill version without vendoring its whole package.
- Compose multiple skills without hidden instruction conflicts.

That is the product center. Distribution, signing, and marketplace polish should serve this core experience.
