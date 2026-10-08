"""Validate source versions and the exact distributions destined for PyPI."""
import argparse
from email.parser import BytesParser
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import tarfile
import zipfile

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10 development/CI only.
    import tomli as tomllib


def source_version(root, tag):
    project = tomllib.loads((root / 'pyproject.toml').read_text())['project']
    version = project['version']
    if project['name'] != 'fish-speech-api' or not re.fullmatch(r'(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)', version):
        raise ValueError('Expected fish-speech-api with a stable X.Y.Z version')
    locked = [p['version'] for p in tomllib.loads((root / 'uv.lock').read_text())['package']
              if p['name'] == project['name']]
    if locked != [version]:
        raise ValueError('uv.lock project version must match pyproject.toml')
    manifest_path = root / '.release-please-manifest.json'
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        if manifest.get('.', version) != version:
            raise ValueError('Release Please manifest must match pyproject.toml')
    if tag and tag != 'v' + version:
        raise ValueError(f'Release tag {tag!r} must match v{version}')
    return version


def check_metadata(data, version):
    metadata = BytesParser().parsebytes(data)
    name = re.sub(r'[-_.]+', '-', metadata['Name'] or '').lower()
    if name != 'fish-speech-api' or metadata['Version'] != version:
        raise ValueError('Distribution metadata does not match source name/version')


def safe_paths(names):
    for name in names:
        path = PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts or any(
            part in {'.env', '.git', '.venv', '__pycache__', 'checkpoints', 'data'}
            or part.endswith(('.pyc', '.pem', '.key', '.wav', '.pt', '.pth'))
            for part in path.parts
        ):
            raise ValueError(f'Unexpected or unsafe packaged file: {name}')


def check_distributions(dist, version):
    wheels = list(dist.glob('*.whl'))
    sdists = list(dist.glob('*.tar.gz'))
    outputs = [p for p in dist.iterdir() if p.name != '.gitignore']
    if len(wheels) != 1 or len(sdists) != 1 or len(outputs) != 2:
        raise ValueError('Expected exactly one wheel and one sdist in a clean dist directory')
    stem = 'fish_speech_api-' + version
    if wheels[0].name != stem + '-py3-none-any.whl' or sdists[0].name != stem + '.tar.gz':
        raise ValueError('Unexpected distribution filenames/version')
    with zipfile.ZipFile(wheels[0]) as archive:
        names = archive.namelist()
        safe_paths(names)
        required = {'fishapi/__init__.py', 'fishapi/client.py', stem + '.dist-info/licenses/LICENSE'}
        if not required.issubset(names) or any(
            not name.startswith(('fishapi/', stem + '.dist-info/')) for name in names
        ):
            raise ValueError('Wheel is missing package/license files or includes unrelated files')
        check_metadata(archive.read(stem + '.dist-info/METADATA'), version)
    with tarfile.open(sdists[0]) as archive:
        members = archive.getmembers()
        names = [m.name for m in members]
        safe_paths(names)
        if any(not (m.isfile() or m.isdir()) for m in members):
            raise ValueError('Links and special files are not allowed in the sdist')
        if any(not n.startswith(stem + '/') for n in names):
            raise ValueError('Unexpected sdist root')
        required = {'PKG-INFO', 'pyproject.toml', 'README.md', 'LICENSE',
                    'src/fishapi/__init__.py', 'src/fishapi/client.py'}
        if not {stem + '/' + n for n in required}.issubset(names):
            raise ValueError('Sdist is missing build/package files')
        check_metadata(archive.extractfile(stem + '/PKG-INFO').read(), version)
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in wheels + sdists}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tag', default=os.environ.get('RELEASE_TAG', ''))
    parser.add_argument('--dist', type=Path)
    parser.add_argument('--record', type=Path)
    parser.add_argument('--sha', default='')
    args = parser.parse_args()
    try:
        version = source_version(Path.cwd(), args.tag)
        files = check_distributions(args.dist, version) if args.dist else None
        if args.record:
            if files is None or not re.fullmatch('[0-9a-f]{40}', args.sha):
                raise ValueError('A record requires validated distributions and a full source SHA')
            args.record.write_text(json.dumps({'name': 'fish-speech-api', 'version': version,
                                              'source_sha': args.sha, 'files': files}, indent=2) + '\n')
        print(f'Validated fish-speech-api {version}' + (' and distribution contents' if files else ''))
    except (ValueError, KeyError, OSError) as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == '__main__':
    main()
