#!/usr/bin/env python3
"""Local structural checks only: no GitHub access or runtime-install claims."""
from pathlib import Path
import sys

try:
    import yaml
except ImportError:
    raise SystemExit("PyYAML required: python3 -m pip install pyyaml")

root = Path(__file__).resolve().parents[1]
cat = yaml.safe_load((root / 'catalog.yaml').read_text(encoding='utf-8'))
errors = []
expected_categories = {'reasoning', 'requirements', 'engineering', 'automation'}
if cat.get('schema_version') != 1:
    errors.append('unsupported schema_version')
records = cat.get('skills')
if not isinstance(records, list):
    errors.append('skills must be a list')
    records = []
ids = set()
for i, entry in enumerate(records):
    if not isinstance(entry, dict):
        errors.append(f'entry {i} not a mapping')
        continue
    k = entry.get('id')
    if not isinstance(k, str) or not k or k in ids:
        errors.append(f'invalid/duplicate id {k!r}')
    ids.add(k)
    for field in ('description', 'repository', 'branch', 'source_path', 'entrypoint', 'version', 'kind', 'status'):
        if not isinstance(entry.get(field), str) or not entry[field].strip():
            errors.append(f'{k}: missing/invalid {field}')
    for field in ('triggers', 'prerequisites'):
        if not isinstance(entry.get(field), list) or not entry[field]:
            errors.append(f'{k}: missing/invalid {field}')
    category = entry.get('category')
    if category not in expected_categories:
        errors.append(f'{k}: unknown category {category!r}')
    elif not (root / 'categories' / (category + '.md')).is_file():
        errors.append(f'{k}: category file missing')
    repo, path = entry.get('repository', ''), entry.get('source_path', '')
    if not (isinstance(repo, str) and repo.count('/') == 1 and all(repo.split('/'))):
        errors.append(f'{k}: invalid repository')
    if not (isinstance(path, str) and path.endswith('/SKILL.md') and '..' not in path.split('/') and not path.startswith('/')):
        errors.append(f'{k}: invalid source_path')
if len(records) != 8:
    errors.append(f'expected 8 capabilities; got {len(records)}')
print(f'Catalog structural check: {len(records)} records, {len(expected_categories)} categories')
if errors:
    for e in errors:
        print('FAIL:', e)
    sys.exit(1)
print('PASS: local structure. Remote source existence/runtime installation not tested.')
