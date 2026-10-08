"""Fail closed before upload; confirm exact PyPI file hashes after upload."""
import argparse
import json
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


def matches(payload, expected):
    found = {item['filename']: item for item in payload['urls']}
    for name, digest in expected.items():
        if name in found:
            item = found[name]
            if item.get('yanked') or item['digests']['sha256'] != digest:
                raise ValueError(f'Conflicting or yanked PyPI file: {name}; reconcile manually')
    return all(name in found for name in expected)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('record', type=Path)
    parser.add_argument('--preflight', action='store_true')
    args = parser.parse_args()
    record = json.loads(args.record.read_text())
    url = f"https://pypi.org/pypi/{record['name']}/{record['version']}/json"
    attempts = 1 if args.preflight else 12
    for attempt in range(attempts):
        try:
            with urlopen(url, timeout=15) as response:
                payload = json.load(response)
            if args.preflight:
                raise SystemExit('This PyPI version already exists. Compare retained hashes and follow docs/publishing.md; no files uploaded.')
            if matches(payload, record['files']):
                print(f"Confirmed {record['name']}=={record['version']} with matching PyPI hashes")
                return
        except HTTPError as exc:
            if exc.code == 404 and args.preflight:
                print('Version absent from PyPI; name ownership still requires owner setup')
                return
            if exc.code not in {404, 429, 500, 502, 503, 504}:
                raise
            if args.preflight:
                raise SystemExit(f'PyPI preflight unavailable: HTTP {exc.code}; refusing upload') from exc
        except (URLError, TimeoutError) as exc:
            if args.preflight:
                raise SystemExit(f'PyPI preflight unavailable: {exc}; refusing upload') from exc
        if attempt + 1 < attempts:
            time.sleep(10)
    raise SystemExit('PyPI availability/hash verification incomplete after bounded retries; inspect the release before retrying')


if __name__ == '__main__':
    main()
