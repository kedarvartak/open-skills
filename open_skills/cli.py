from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .loader import SkillLoadError, discover_skills, load_skill
from .registry import (
    RegistryError,
    default_registry_path,
    install_skill,
    publish_skill,
    search_registry,
)
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

    publish_parser = subparsers.add_parser("publish", help="Publish a skill to a local registry")
    publish_parser.add_argument("path", help="Path to a skill directory")
    publish_parser.add_argument(
        "--registry",
        default=str(default_registry_path()),
        help="Path to the local registry directory",
    )
    publish_parser.add_argument("--force", action="store_true", help="Overwrite an existing version")

    search_parser = subparsers.add_parser("search", help="Search skills in a local registry")
    search_parser.add_argument("query", nargs="?", help="Optional search query")
    search_parser.add_argument(
        "--registry",
        default=str(default_registry_path()),
        help="Path to the local registry directory",
    )
    search_parser.add_argument("--json", action="store_true", help="Print results as JSON")

    install_parser = subparsers.add_parser("install", help="Install a skill from a local registry")
    install_parser.add_argument("name", help="Skill name")
    install_parser.add_argument(
        "--version",
        help="Specific skill version to install; defaults to latest",
    )
    install_parser.add_argument(
        "--registry",
        default=str(default_registry_path()),
        help="Path to the local registry directory",
    )
    install_parser.add_argument(
        "--dest",
        default=str(Path("./installed-skills").resolve()),
        help="Directory where the skill should be installed",
    )
    install_parser.add_argument("--force", action="store_true", help="Overwrite an existing install")

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


def _cmd_publish(path: str, registry: str, force: bool) -> int:
    try:
        release = publish_skill(path, registry, force=force)
    except RegistryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(
        f"published {release.metadata.name}@{release.version} "
        f"to {(Path(registry).resolve() / release.package_path)}"
    )
    return 0


def _cmd_search(registry: str, query: str | None, as_json: bool) -> int:
    records = search_registry(registry, query)
    if as_json:
        payload = []
        for record in records:
            latest_release = record.versions.get(record.latest_version)
            payload.append(
                {
                    "name": record.name,
                    "latest_version": record.latest_version,
                    "description": latest_release.metadata.description if latest_release else "",
                    "capabilities": latest_release.metadata.capabilities if latest_release else [],
                    "hosts": latest_release.metadata.hosts if latest_release else [],
                }
            )
        print(json.dumps(payload, indent=2))
        return 0

    for record in records:
        latest_release = record.versions.get(record.latest_version)
        description = latest_release.metadata.description if latest_release else ""
        print(f"{record.name}@{record.latest_version}")
        if description:
            print(f"  {description}")
    return 0


def _cmd_install(name: str, registry: str, dest: str, version: str | None, force: bool) -> int:
    try:
        destination = install_skill(name, registry, dest, version=version, force=force)
    except RegistryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"installed {name} to {destination}")
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
    if args.command == "publish":
        return _cmd_publish(args.path, args.registry, args.force)
    if args.command == "search":
        return _cmd_search(args.registry, args.query, args.json)
    if args.command == "install":
        return _cmd_install(args.name, args.registry, args.dest, args.version, args.force)

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
