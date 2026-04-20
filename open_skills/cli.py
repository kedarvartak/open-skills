from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .codex_adapter import CodexAdapter, DEFAULT_CODEX_CAPABILITIES
from .loader import SkillLoadError, discover_skills, load_skill
from .validator import validate_skill


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="open-skills", description="Universal skill toolkit")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List discovered skills")
    list_parser.add_argument("path", help="Directory that contains skill folders")

    inspect_parser = subparsers.add_parser("inspect", help="Inspect a skill package")
    inspect_parser.add_argument("path", help="Path to a skill directory")

    validate_parser = subparsers.add_parser("validate", help="Validate a skill package")
    validate_parser.add_argument("path", help="Path to a skill directory")

    codex_parser = subparsers.add_parser("codex", help="Codex host adapter commands")
    codex_subparsers = codex_parser.add_subparsers(dest="codex_command", required=True)

    codex_list_parser = codex_subparsers.add_parser("list", help="List Codex-compatible skills")
    codex_list_parser.add_argument(
        "--skills-dir",
        default="./installed-skills",
        help="Directory that contains installed skill folders",
    )

    codex_match_parser = codex_subparsers.add_parser("match", help="Match skills for a task")
    codex_match_parser.add_argument("task", help="Task description to match against installed skills")
    codex_match_parser.add_argument(
        "--skills-dir",
        default="./installed-skills",
        help="Directory that contains installed skill folders",
    )
    codex_match_parser.add_argument("--limit", type=int, default=5, help="Maximum matches to show")

    codex_render_parser = codex_subparsers.add_parser(
        "render",
        help="Render a skill as Codex-ready context",
    )
    codex_render_parser.add_argument("skill", help="Skill name or path")
    codex_render_parser.add_argument(
        "--skills-dir",
        default="./installed-skills",
        help="Directory that contains installed skill folders",
    )
    codex_render_parser.add_argument(
        "--capability",
        action="append",
        choices=sorted(DEFAULT_CODEX_CAPABILITIES | {"network_access", "mcp_access"}),
        help="Override Codex capabilities; may be passed multiple times",
    )
    codex_render_parser.add_argument("--json", action="store_true", help="Print adapter output as JSON")

    return parser


def _cmd_list(path: str) -> int:
    skills = discover_skills(path)
    for skill_path in skills:
        print(skill_path)
    return 0


def _cmd_inspect(path: str) -> int:
    try:
        skill = load_skill(path)
    except SkillLoadError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    payload = {
        "root": str(skill.root),
        "name": skill.metadata.name,
        "description": skill.metadata.description,
        "version": skill.metadata.version,
        "spec_version": skill.metadata.spec_version,
        "author": skill.metadata.author,
        "homepage": skill.metadata.homepage,
        "license": skill.metadata.license,
        "capabilities": skill.metadata.capabilities,
        "hosts": skill.metadata.hosts,
        "dependencies": skill.metadata.dependencies,
    }
    print(json.dumps(payload, indent=2))
    return 0


def _cmd_validate(path: str) -> int:
    try:
        skill = load_skill(path)
    except SkillLoadError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    errors = validate_skill(skill)
    if errors:
        print(f"{Path(path).resolve()}: invalid")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"{Path(path).resolve()}: valid")
    return 0


def _cmd_codex_list(skills_dir: str) -> int:
    adapter = CodexAdapter()
    for skill in adapter.discover(skills_dir):
        marker = "codex" if adapter.supports_host(skill) else "generic"
        print(f"{skill.metadata.name}@{skill.metadata.version} [{marker}]")
        print(f"  {skill.metadata.description}")
    return 0


def _cmd_codex_match(task: str, skills_dir: str, limit: int) -> int:
    adapter = CodexAdapter()
    matches = adapter.match(task, skills_dir, limit=limit)
    for skill in matches:
        print(f"{skill.metadata.name}@{skill.metadata.version}")
        print(f"  {skill.metadata.description}")
    return 0


def _cmd_codex_render(
    skill_ref: str,
    skills_dir: str,
    capabilities: list[str] | None,
    as_json: bool,
) -> int:
    adapter = CodexAdapter(capabilities=set(capabilities) if capabilities else None)
    try:
        skill = adapter.resolve_skill(skill_ref, skills_dir)
    except SkillLoadError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    errors = validate_skill(skill)
    if errors:
        print(f"{skill.root}: invalid", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    context = adapter.materialize(skill)
    if as_json:
        payload = {
            "name": skill.metadata.name,
            "version": skill.metadata.version,
            "root": str(skill.root),
            "supports_host": context.supports_host,
            "supported_capabilities": context.capability_report.supported,
            "missing_capabilities": context.capability_report.missing,
            "references": [str(path) for path in context.references],
            "scripts": [str(path) for path in context.scripts],
            "assets": [str(path) for path in context.assets],
            "warnings": context.warnings,
            "prompt": context.prompt,
        }
        print(json.dumps(payload, indent=2))
        return 0

    print(context.prompt, end="")
    return 0


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "list":
        return _cmd_list(args.path)
    if args.command == "inspect":
        return _cmd_inspect(args.path)
    if args.command == "validate":
        return _cmd_validate(args.path)
    if args.command == "codex":
        if args.codex_command == "list":
            return _cmd_codex_list(args.skills_dir)
        if args.codex_command == "match":
            return _cmd_codex_match(args.task, args.skills_dir, args.limit)
        if args.codex_command == "render":
            return _cmd_codex_render(args.skill, args.skills_dir, args.capability, args.json)

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
