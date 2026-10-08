"""Require release tag to match package metadata (run with Python 3.11+)."""
import os
from pathlib import Path
import tomllib

metadata = tomllib.loads(Path('pyproject.toml').read_text())
expected = 'v' + metadata['project']['version']
tag = os.environ['RELEASE_TAG']
if tag != expected:
    raise SystemExit(f'Release tag {tag!r} must match {expected!r}')
print(f'Release version verified: {tag}')
