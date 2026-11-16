#!/usr/bin/env python3
"""Install portable Agent Skills into local user or project folders.

The native Claude Code Marketplace provides stronger plugin integration.
This installer never activates hooks, downloads dependencies, or starts a loop.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parents[1]
SKILLS = (
    "plain", "termcard", "cross-domain-exploration", "req-collect",
    "fractal", "refactor-agent", "test-enforcer", "optloop",
)
RUNTIME = {
    "fractal": "fractal",
    "refactor-agent": "refactor-agent",
    "test-enforcer": "test-enforcer",
    "optloop": "optloop",
}
PROJECT_LOCATIONS = {
    "universal": ".agents/skills",
    "codex": ".agents/skills",
    "cursor": ".cursor/skills",
    "opencode": ".opencode/skills",
    "gemini": ".gemini/skills",
    "copilot": ".github/skills",
    "claude": ".claude/skills",
}
USER_LOCATIONS = {
    "universal": ".agents/skills",
    "codex": ".agents/skills",
    "cursor": ".cursor/skills",
    "opencode": ".config/opencode/skills",
    "gemini": ".gemini/skills",
    "copilot": ".copilot/skills",
    "claude": ".claude/skills",
}


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--agent", choices=PROJECT_LOCATIONS, default="universal",
                   help="Target skill discovery directory (default: universal .agents/skills)")
    p.add_argument("--scope", choices=("user", "project"), default="user")
    p.add_argument("--target", type=Path, help="Override home/project base directory")
    p.add_argument("--only", nargs="+", choices=SKILLS, help="Install only selected skills")
    p.add_argument("--no-runtime", action="store_true",
                   help="Omit bundled executable plugin payloads from 4 adapter skills")
    p.add_argument("--force", action="store_true", help="Replace already installed skill directories")
    p.add_argument("--dry-run", action="store_true", help="Print actions without writing files")
    p.add_argument("--list", action="store_true", help="Print skill IDs and exit")
    return p.parse_args(argv)


def install(args):
    if args.list:
        print("\n".join(SKILLS))
        return 0
    root = (args.target if args.target else (Path.home() if args.scope == "user" else Path.cwd())).expanduser().resolve()
    rel = USER_LOCATIONS[args.agent] if args.scope == "user" else PROJECT_LOCATIONS[args.agent]
    skill_root = root / rel
    chosen = args.only or SKILLS
    errors = []
    for name in chosen:
        source = HERE / "skills" / name
        destination = skill_root / name
        if not (source / "SKILL.md").is_file():
            errors.append(f"MISSING SOURCE: {source}")
            continue
        if destination.exists() and not args.force:
            errors.append(f"EXISTS: {destination} (use --force to replace)")
            continue
        print(f"{'PLAN' if args.dry_run else 'INSTALL'} {name} -> {destination}")
        if args.dry_run:
            continue
        if destination.exists():
            if destination.is_symlink() or not destination.is_dir():
                errors.append(f"UNSAFE TARGET: {destination}")
                continue
            shutil.rmtree(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, destination)
        if not args.no_runtime and name in RUNTIME:
            payload = HERE / "plugins" / RUNTIME[name]
            if not (payload / ".claude-plugin" / "plugin.json").is_file():
                errors.append(f"MISSING RUNTIME: {payload}")
                continue
            shutil.copytree(payload, destination / "_plugin")
    for error in errors:
        print(error, file=sys.stderr)
    if errors:
        return 1
    print(f"OK: {len(chosen)} portable skill(s). Native hooks/commands are not installed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(install(parse_args()))
