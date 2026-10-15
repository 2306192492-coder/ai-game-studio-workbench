import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('unreal_adapter', ROOT / 'Tools/unreal_adapter.py')
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


class UnrealAdapterTests(unittest.TestCase):
    def config(self):
        return {'engine_root': 'C:/Program Files/Epic Games/UE_5.8',
                'project': str(ROOT / 'UnrealProject/AIStudio.uproject'),
                'map_asset': '/Game/AIStudio/Maps/WorkbenchValidation', 'timeout_seconds': 600}

    def test_editor_plan_keeps_paths_as_arguments_and_disables_rendering(self):
        command = adapter.make_plan(self.config(), 'prepare', Path('Evidence/test with spaces'))
        self.assertIn('Program Files', command[0])
        self.assertIn('-NullRHI', command)
        self.assertIn('-run=pythonscript', command)
        self.assertEqual(self.config()['project'], command[1])

    def test_dry_run_does_not_launch_or_write_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(adapter, 'ROOT', Path(directory)), patch.object(adapter, 'load_config', return_value=self.config()):
                with patch.object(adapter.subprocess, 'Popen') as process, contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(0, adapter.main(['prepare', '--dry-run']))
                    process.assert_not_called()
                self.assertEqual([], list(Path(directory).iterdir()))

    def test_automation_requires_nonempty_completed_results(self):
        report = dict(succeeded=0, succeededWithWarnings=0, failed=0, notRun=0, inProcess=0)
        self.assertFalse(adapter.automation_passed({}))
        self.assertFalse(adapter.automation_passed(report))
        report['succeeded'] = 2
        self.assertTrue(adapter.automation_passed(report))
        for field in ('failed', 'notRun', 'inProcess'):
            with self.subTest(field=field):
                self.assertFalse(adapter.automation_passed(dict(report, **{field: 1})))

    def test_stale_editor_report_cannot_pass(self):
        request = dict(runId='new-run', action='probe')
        report = dict(runId='old-run', action='probe', passed=True, checks=[{'passed': True}])
        self.assertFalse(adapter.editor_passed(report, request))
        report['runId'] = 'new-run'
        self.assertTrue(adapter.editor_passed(report, request))
        report['checks'] = []
        self.assertFalse(adapter.editor_passed(report, request))

    def test_test_filter_rejects_command_injection(self):
        for query in ('', 'System.Core;Quit', 'System.Core\nQuit', 'A"B'):
            with self.subTest(query=query), self.assertRaises(ValueError):
                adapter.make_plan(self.config(), 'test', Path('Evidence/test'), query)

    def test_batch_rejects_shell_expansion(self):
        for unsafe in ('%TEMP%', 'a&b', 'a|b', 'a!b'):
            with self.subTest(unsafe=unsafe), self.assertRaises(ValueError):
                adapter.batch_command(['RunUAT.bat', '-project=' + unsafe])

    @unittest.skipUnless(os.name == 'nt', 'Windows batch quoting')
    def test_batch_preserves_spaces_on_windows(self):
        with tempfile.TemporaryDirectory(prefix='workbench batch ') as directory:
            script = Path(directory) / 'arguments.cmd'
            script.write_text('@echo off\necho [%~1]\necho [%~2]\n', encoding='ascii')
            result = subprocess.run(adapter.batch_command([str(script), 'a path with spaces', '-name=value']),
                                    capture_output=True, text=True)
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual(['[a path with spaces]', '[-name=value]'], result.stdout.splitlines())

    def test_import_requires_selected_registered_source(self):
        with self.assertRaises(ValueError):
            adapter.validate_import('unknown', 'somewhere/model.fbx')

    def test_import_namespace_cannot_escape_into_sibling_or_parent(self):
        self.assertTrue(adapter.import_destination_valid('/Game/AIStudio/Imports/Props'))
        for path in ('/Game/AIStudio/ImportsOther', '/Game/AIStudio/Imports/../Maps', '/Game/Other'):
            with self.subTest(path=path):
                self.assertFalse(adapter.import_destination_valid(path))

    def test_package_boot_needs_completed_map_load_and_clean_exit(self):
        map_asset = '/Game/AIStudio/Maps/WorkbenchValidation'
        text = 'LogLoad: Took 0.05 seconds to LoadMap(' + map_asset + ')'
        self.assertTrue(adapter.package_boot_passed(text, map_asset, 0))
        self.assertFalse(adapter.package_boot_passed('LoadMap: ' + map_asset, map_asset, 0))
        self.assertFalse(adapter.package_boot_passed(text, map_asset, 1))
        self.assertFalse(adapter.package_boot_passed(text + '\nFatal error: crash', map_asset, 0))

    def test_changed_or_escaping_package_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / 'package'
            package.mkdir()
            executable = package / 'AIStudio.exe'
            executable.write_bytes(b'synthetic launcher fixture')
            report = dict(action='build', passed=True, configuration='Development', files=[dict(path='AIStudio.exe', sha256=adapter.file_sha256(executable))])
            report_file = root / 'result.json'
            report_file.write_text(json.dumps(report), encoding='utf8')
            self.assertEqual(executable, adapter.verified_package(report_file, 'AIStudio'))
            executable.write_bytes(b'changed')
            with self.assertRaises(ValueError):
                adapter.verified_package(report_file, 'AIStudio')
            report['files'][0]['path'] = '../outside.exe'
            report_file.write_text(json.dumps(report), encoding='utf8')
            with self.assertRaises(ValueError):
                adapter.verified_package(report_file, 'AIStudio')

    def test_build_plan_has_distinct_archive_and_validation_map(self):
        command = adapter.make_plan(self.config(), 'build', Path('Evidence/new-run'))
        self.assertIn('-map=/Game/AIStudio/Maps/WorkbenchValidation', command)
        self.assertIn('-archivedirectory=Evidence/new-run/package', [v.replace('\\', '/') for v in command])


class SharedAssetGateTests(unittest.TestCase):
    def gate(self, record, engine, stage='import', change_source=False):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'Tools').mkdir()
            (root / 'Registry').mkdir()
            script = root / 'Tools/asset_gate.py'
            script.write_bytes((ROOT / 'Integrations/HybridAssets/Tools/asset_gate.py').read_bytes())
            (root / 'Registry/asset-manifest.json').write_text(json.dumps({'assets': [record]}), encoding='utf8')
            result = subprocess.run([sys.executable, str(script), '--asset', record['id'],
                                     '--engine', engine, '--stage', stage], capture_output=True, text=True)
            return json.loads(result.stdout)

    def test_ue_only_asset_cannot_cross_to_unity(self):
        asset = dict(id='vendor', license_verified=True, ue_only=True, files=[])
        self.assertFalse(self.gate(asset, 'Unity')['allowed'])
        self.assertTrue(self.gate(asset, 'Unreal')['allowed'])

    def test_import_is_not_runtime_promotion(self):
        asset = dict(id='candidate', license_verified=True, files=[])
        self.assertTrue(self.gate(asset, 'Unreal')['allowed'])
        self.assertFalse(self.gate(asset, 'Unreal', 'promote')['allowed'])

    def test_runtime_proof_is_engine_specific(self):
        asset = dict(id='candidate', license_verified=True, files=[], quality_status='prototype_verified',
                     runtime_verified_engines=['Unity'])
        self.assertTrue(self.gate(asset, 'Unity', 'promote')['allowed'])
        self.assertFalse(self.gate(asset, 'Unreal', 'promote')['allowed'])


if __name__ == '__main__':
    unittest.main()
