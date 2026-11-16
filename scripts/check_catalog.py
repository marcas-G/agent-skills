#!/usr/bin/env python3
"""Validate local consolidated skills, plugin marketplace and source integrity."""
from __future__ import annotations
import json
from pathlib import Path
import sys
import yaml

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "plain", "termcard", "cross-domain-exploration", "req-collect",
    "fractal", "refactor-agent", "test-enforcer", "optloop",
}
NATIVE = {
    "plain": "plainkit", "termcard": "plainkit",
    "cross-domain-exploration": "plainkit", "req-collect": "req-collector",
    "fractal": "fractal", "refactor-agent": "refactor-agent",
    "test-enforcer": "test-enforcer", "optloop": "optloop",
}
DIRECT = {
    "plain": "plugins/plainkit/skills/plain",
    "termcard": "plugins/plainkit/skills/termcard",
    "cross-domain-exploration": "plugins/plainkit/skills/cross-domain-exploration",
    "req-collect": "plugins/req-collector/skills/req-collect",
}
CATEGORIES = {"reasoning", "requirements", "engineering", "automation"}
REQUIRED_RUNTIME = [
    "plugins/fractal/scripts/fractal.py",
    "plugins/fractal/hooks/hooks.json",
    "plugins/refactor-agent/scripts/refactor.py",
    "plugins/test-enforcer/scripts/verify.py",
    "plugins/test-enforcer/hooks/hooks.json",
    "plugins/optloop/scripts/optloop.py",
    "plugins/optloop/bin/optloop",
    "plugins/optloop/runtime/claude-home/CLAUDE.md",
]
errors = []


def require(condition, detail):
    if not condition:
        errors.append(detail)


def load_frontmatter(path):
    if not path.is_file():
        require(False, f"Missing skill: {path.relative_to(ROOT)}")
        return {}
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        require(False, f"Invalid YAML frontmatter: {path.relative_to(ROOT)}")
        return {}
    return yaml.safe_load(text.split("---\n", 2)[1]) or {}


catalog = yaml.safe_load((ROOT / "catalog.yaml").read_text(encoding="utf-8"))
require(catalog.get("schema_version") == 1, "Unexpected schema version")
records = catalog.get("skills", [])
require(isinstance(records, list) and len(records) == 8, "Expected 8 catalog entries")
found = set()
for row in records:
    if not isinstance(row, dict):
        errors.append("Invalid catalog entry")
        continue
    name = row.get("id")
    require(name in EXPECTED, f"Unexpected id {name}")
    require(name not in found, f"Duplicate id {name}")
    found.add(name)
    if name not in NATIVE:
        continue
    require(row.get("category") in CATEGORIES, f"{name}: invalid category")
    require(row.get("repository") == "marcas-G/agent-skills", f"{name}: wrong repository")
    require(row.get("native_plugin_path") == "plugins/" + NATIVE[name], f"{name}: wrong native plugin")
    require(row.get("source_path") == f"skills/{name}/SKILL.md", f"{name}: wrong source")
    require(row.get("status") == "bundled-not-runtime-verified", f"{name}: unsupported status")
    require(isinstance(row.get("triggers"), list) and bool(row["triggers"]), f"{name}: missing triggers")
    front = load_frontmatter(ROOT / row.get("source_path", "missing"))
    require(front.get("name") == name, f"{name}: frontmatter name mismatch")
    require(isinstance(front.get("description"), str) and bool(front["description"]), f"{name}: missing description")

require(found == EXPECTED, "Skill IDs missing from catalog")

for category in CATEGORIES:
    require((ROOT / "categories" / (category + ".md")).is_file(), f"Missing category {category}")
for path in ("README.md", "README.en.md", "SOURCES.md", "scripts/install.py", "docs/compatibility.md"):
    require((ROOT / path).is_file(), f"Missing document or installer {path}")

marketplace = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text(encoding="utf-8"))
plugins = marketplace.get("plugins", [])
require(marketplace.get("name") == "agent-skills", "Marketplace name mismatch")
require(len(plugins) == 6, "Expected six native plugins")
seen = set()
for entry in plugins:
    name, source = entry.get("name", ""), entry.get("source", "")
    require(name not in seen, f"Duplicate marketplace plugin {name}")
    seen.add(name)
    require(source == "./plugins/" + name, f"{name}: invalid marketplace source path")
    manifest_file = ROOT / "plugins" / name / ".claude-plugin/plugin.json"
    require(manifest_file.is_file(), f"{name}: missing native manifest")
    if manifest_file.is_file():
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        require(manifest.get("name") == name, f"{name}: native manifest name mismatch")
require(seen == set(NATIVE.values()), "Marketplace plugins do not match catalog")

for name, original in DIRECT.items():
    skill = ROOT / "skills" / name
    src = ROOT / original
    if src.is_dir():
        for path in src.rglob("*"):
            if path.is_file():
                rel = path.relative_to(src)
                copy = skill / rel
                require(copy.is_file(), f"{name}: missing mirrored file {rel}")
                if copy.is_file():
                    require(copy.read_bytes() == path.read_bytes(),
                            f"{name}: diverged original file {rel}")
    else:
        errors.append(f"{name}: missing original source {src}")

for path in REQUIRED_RUNTIME:
    require((ROOT / path).is_file(), f"Missing native runtime asset: {path}")

print(f"Catalog check: {len(records)} skills; {len(plugins)} native plugins; {len(CATEGORIES)} categories")
if errors:
    for message in errors:
        print("FAIL:", message, file=sys.stderr)
    raise SystemExit(1)
print("PASS: structure, frontmatter, source mirrors and marketplace metadata")
print("Note: this does not test actual agent installation, hook execution, or Docker.")
