"""Release safety contracts: mismatches must fail before credentials are available."""
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]


class ReleaseTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'pyproject.toml').write_text('[project]\nname="fish-speech-api"\nversion="0.1.0"\n')
        (self.root / 'uv.lock').write_text('[[package]]\nname="fish-speech-api"\nversion="0.1.0"\n')
        (self.root / '.release-please-manifest.json').write_text('{}')

    def run_check(self, tag='', *args):
        return subprocess.run([sys.executable, str(ROOT / 'scripts/check_release.py'), *args],
                              cwd=self.root, env={**os.environ, 'RELEASE_TAG': tag},
                              text=True, capture_output=True)

    def archives(self, version='0.1.0', extra=None):
        dist = self.root / 'dist'
        dist.mkdir(exist_ok=True)
        metadata = f'Metadata-Version: 2.4\nName: fish-speech-api\nVersion: {version}\n'
        with zipfile.ZipFile(dist / 'fish_speech_api-0.1.0-py3-none-any.whl', 'w') as archive:
            archive.writestr('fish_speech_api-0.1.0.dist-info/METADATA', metadata)
            archive.writestr('fish_speech_api-0.1.0.dist-info/licenses/LICENSE', 'MIT')
            for name in ['__init__.py', 'client.py']:
                archive.writestr('fishapi/' + name, '')
            if extra:
                archive.writestr(extra, 'secret')
        with tarfile.open(dist / 'fish_speech_api-0.1.0.tar.gz', 'w:gz') as archive:
            for name, data in {'PKG-INFO': metadata, 'pyproject.toml': '[project]',
                               'LICENSE': 'MIT', 'README.md': '# Client',
                               'src/fishapi/__init__.py': '', 'src/fishapi/client.py': ''}.items():
                info = tarfile.TarInfo('fish_speech_api-0.1.0/' + name)
                payload = data.encode()
                info.size = len(payload)
                archive.addfile(info, io.BytesIO(payload))

    def test_build_without_tag_and_first_release(self):
        self.assertEqual(self.run_check().returncode, 0)
        self.assertEqual(self.run_check('v0.1.0').returncode, 0)

    def test_wrong_tag_is_rejected(self):
        self.assertNotEqual(self.run_check('v0.2.0').returncode, 0)

    def test_lock_drift_is_rejected(self):
        (self.root / 'uv.lock').write_text('[[package]]\nname="fish-speech-api"\nversion="0.0.9"\n')
        self.assertNotEqual(self.run_check('v0.1.0').returncode, 0)

    def test_manifest_drift_is_rejected(self):
        (self.root / '.release-please-manifest.json').write_text('{".": "0.0.9"}')
        self.assertNotEqual(self.run_check('v0.1.0').returncode, 0)

    def test_prerelease_is_rejected_by_stable_policy(self):
        (self.root / 'pyproject.toml').write_text('[project]\nname="fish-speech-api"\nversion="0.1.0rc1"\n')
        (self.root / 'uv.lock').write_text('[[package]]\nname="fish-speech-api"\nversion="0.1.0rc1"\n')
        self.assertNotEqual(self.run_check('v0.1.0rc1').returncode, 0)

    def test_artifact_metadata_mismatch_is_rejected(self):
        self.archives(version='0.0.9')
        self.assertNotEqual(self.run_check('v0.1.0', '--dist', 'dist').returncode, 0)

    def test_unexpected_wheel_content_is_rejected(self):
        self.archives(extra='.env')
        self.assertNotEqual(self.run_check('v0.1.0', '--dist', 'dist').returncode, 0)

    def test_valid_artifacts_create_hash_record(self):
        self.archives()
        (self.root / 'dist/.gitignore').write_text('*')
        result = self.run_check('v0.1.0', '--dist', 'dist', '--record', 'release.json', '--sha', 'a' * 40)
        self.assertEqual(result.returncode, 0, result.stderr)
        record = json.loads((self.root / 'release.json').read_text())
        self.assertEqual(record['version'], '0.1.0')
        self.assertEqual(record['source_sha'], 'a' * 40)
        self.assertEqual(len(record['files']), 2)
        self.assertTrue(all(len(value) == 64 for value in record['files'].values()))

    def test_missing_distribution_is_rejected(self):
        (self.root / 'dist').mkdir()
        self.assertNotEqual(self.run_check('v0.1.0', '--dist', 'dist').returncode, 0)


class RegistryTest(unittest.TestCase):
    def test_registry_hash_comparison(self):
        path = ROOT / 'scripts/verify_pypi.py'
        self.assertTrue(path.exists(), 'Registry verifier is required')
        spec = importlib.util.spec_from_file_location('verify_pypi', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        expected = {'a.whl': 'a' * 64, 'a.tar.gz': 'b' * 64}
        good = {'info': {'name': 'fish-speech-api', 'version': '0.1.0'}, 'urls': [
            {'filename': name, 'digests': {'sha256': digest}, 'yanked': False}
            for name, digest in expected.items()]}
        self.assertTrue(module.matches(good, expected))
        good['urls'][0]['digests']['sha256'] = 'c' * 64
        with self.assertRaises(ValueError):
            module.matches(good, expected)
        good['urls'].pop(0)
        self.assertFalse(module.matches(good, expected))
        good['urls'][0]['yanked'] = True
        with self.assertRaises(ValueError):
            module.matches(good, expected)


if __name__ == '__main__':
    unittest.main()
