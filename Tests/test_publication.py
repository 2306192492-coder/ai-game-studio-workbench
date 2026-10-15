import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('publication', ROOT / 'Tools/check_repository.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class PublicationTests(unittest.TestCase):
    def test_rejects_private_inputs(self):
        for path in ['Models/model.pt', 'Config/workstation.local.json',
                     'Integrations/HybridAssets/machine.json', 'Runtime/process.json',
                     'Project/Library/metadata.json', 'AssetsSource/vendor.fbx']:
            with self.subTest(path=path):
                self.assertTrue(module.check_file(path, '{}'))

    def test_rejects_credentials_without_echoing_them(self):
        value = 'gh' + 'p_' + 'x' * 36
        self.assertIn('credential-like content', module.check_file('Config/config.json', json.dumps(value)))

    def test_accepts_runtime_code(self):
        self.assertEqual([], module.check_file('Project/Assets/Studio/Runtime/Probe.cs', 'class Probe {}'))

    def test_rejects_invalid_python_and_json(self):
        self.assertTrue(module.check_file('Tools/broken.py', 'def :'))
        self.assertTrue(module.check_file('Config/broken.json', '{'))

    def test_asset_gate_rejects_unknown_asset(self):
        command = [sys.executable, str(ROOT / 'Integrations/HybridAssets/Tools/asset_gate.py'),
                   '--asset', 'not-registered', '--scope', 'public']
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(2, result.returncode)
        self.assertFalse(json.loads(result.stdout)['allowed'])

    def test_asset_gate_checks_transitive_restrictions_and_hashes(self):
        # Use an isolated fixture tree; never alter the operator's registry or assets.
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory)
            (fixture / 'Tools').mkdir()
            (fixture / 'Registry').mkdir()
            script = fixture / 'Tools/asset_gate.py'
            script.write_bytes((ROOT / 'Integrations/HybridAssets/Tools/asset_gate.py').read_bytes())
            records = {'assets': [
                {'id': 'base', 'license_verified': True, 'public_release_approved': False,
                 'files': [{'path': 'missing.glb', 'sha256': '0' * 64}]},
                {'id': 'derived', 'license_verified': True, 'public_release_approved': True,
                 'derived_from': ['base'], 'quality_status': 'prototype_verified'}]}
            (fixture / 'Registry/asset-manifest.json').write_text(json.dumps(records), encoding='utf8')
            result = subprocess.run([sys.executable, str(script), '--asset', 'derived', '--scope', 'public'],
                                    capture_output=True, text=True)
            report = json.loads(result.stdout)
            self.assertEqual(2, result.returncode)
            self.assertIn('base', report['checked_dependencies'])
            self.assertTrue(any('public release' in p for p in report['problems']))
            self.assertTrue(any('missing' in p for p in report['problems']))


if __name__ == '__main__':
    unittest.main()
