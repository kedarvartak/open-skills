from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

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


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "list":
        return _cmd_list(args.path)
    if args.command == "inspect":
        return _cmd_inspect(args.path)
    if args.command == "validate":
        return _cmd_validate(args.path)

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
