import contextlib
from datetime import datetime, timedelta, timezone
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('nvidia_diagnostics', ROOT / 'Tools/nvidia_diagnostics.py')
diag = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diag)
NOW = datetime(2026, 10, 16, 4, tzinfo=timezone.utc)


def snapshot():
    values = {
        'driver': {'installedDriver': {'version': '617.42', 'channel': 'STUDIO'}},
        'applications': {'applications': []},
        'overlay': {'statsOverlayEnabled': True},
        'current_game': {'running': False},
    }
    return {'schema_version': 1, 'source': 'codex-native-tools',
            'collected_at': NOW.isoformat(),
            'results': {diag.QUERIES[k]: {'structuredContent': v} for k, v in values.items()}}


class NvidiaDiagnosticsTests(unittest.TestCase):
    def test_no_hardware_or_snapshot_is_an_optional_skip_for_both_engines(self):
        for engine in ('Unity', 'Unreal'):
            report = diag.make_report(engine, now=NOW,
                                      presence=diag.local_presence({}, 'linux'))
            self.assertTrue(report['optional'])
            self.assertEqual('not_queried', report['mcp']['status'])
            self.assertFalse(report['performance_metrics_collected'])
            self.assertEqual('unsupported_platform', report['local']['status'])

    def test_presence_never_reads_discovery_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bridge = root / 'programs/NVIDIA Corporation/NVIDIA App/McpServer/NvAppMcpServer.exe'
            bridge.parent.mkdir(parents=True)
            bridge.touch()
            manifest = root / 'local/NVIDIA Corporation/NvAppMcpServer/server.json'
            manifest.parent.mkdir(parents=True)
            manifest.write_text('not even JSON; must never be read', encoding='utf8')
            with patch.object(Path, 'read_text', side_effect=AssertionError('no credential reads')):
                result = diag.local_presence({'ProgramFiles': str(root / 'programs'),
                                              'LOCALAPPDATA': str(root / 'local')}, 'win32')
            self.assertTrue(result['bridge_present'])
            self.assertTrue(result['discovery_file_present'])
            self.assertNotIn('mcp', result)

    def test_valid_snapshot_is_shared_and_does_not_claim_gameplay_or_metrics(self):
        for engine in ('Unity', 'Unreal'):
            report = diag.make_report(engine, snapshot(), now=NOW, presence={})
            self.assertEqual('ready', report['mcp']['status'])
            self.assertEqual('supplied_native_mcp_snapshot', report['mcp']['source'])
            self.assertFalse(report['performance_metrics_collected'])
            self.assertEqual(engine, report['engine'])

    def test_overlay_error_does_not_invalidate_driver_and_retains_error_code(self):
        value = snapshot()
        value['results'][diag.QUERIES['overlay']] = {
            'isError': True, 'structuredContent': {'code': 'overlay_not_available', 'retryable': True},
            'content': [{'type': 'text', 'text': 'untrusted details'}]}
        report = diag.summarize_snapshot(value, NOW)
        self.assertEqual('partial', report['status'])
        self.assertEqual('ok', report['queries']['driver']['status'])
        self.assertEqual({'status': 'error', 'code': 'overlay_not_available', 'retryable': True},
                         report['queries']['overlay'])
        # A success-shaped payload accompanying isError cannot pass.
        value['results'][diag.QUERIES['driver']]['isError'] = True
        self.assertEqual('error', diag.summarize_snapshot(value, NOW)['queries']['driver']['status'])

    def test_missing_fields_stay_missing_and_no_game_has_no_identity(self):
        value = snapshot()
        value['results'][diag.QUERIES['current_game']]['structuredContent'].update(
            gameName='stale identity', processId=999, fullscreen=True)
        value['results'][diag.QUERIES['overlay']]['structuredContent'].update(recordingActive='false')
        report = diag.summarize_snapshot(value, NOW)
        self.assertEqual({'running': False}, report['queries']['current_game']['data'])
        self.assertNotIn('recordingActive', report['queries']['overlay']['data'])

    def test_text_and_missing_results_are_never_inferred_as_success(self):
        value = snapshot()
        value['results'] = {diag.QUERIES['driver']: {'content': [{'type': 'text', 'text': 'connected'}]}}
        result = diag.summarize_snapshot(value, NOW)
        self.assertEqual('unavailable', result['status'])
        self.assertEqual('invalid_result', result['queries']['driver']['status'])
        self.assertEqual('not_queried', result['queries']['overlay']['status'])

    def test_rejects_stale_future_and_timezone_free_snapshots(self):
        for time in (NOW - timedelta(minutes=16), NOW + timedelta(minutes=1), NOW.replace(tzinfo=None)):
            value = snapshot()
            value['collected_at'] = time.isoformat()
            with self.subTest(time=time), self.assertRaises(ValueError):
                diag.summarize_snapshot(value, NOW)
        for value in (None, {}, {'schema_version': 1, 'source': 'server.json', 'results': {}}):
            with self.assertRaises(ValueError):
                diag.summarize_snapshot(value, NOW)

    def test_raw_text_metadata_auth_and_unknown_tools_are_not_copied(self):
        value = snapshot()
        marker = 'synthetic-sensitive-marker'
        value['results'][diag.QUERIES['driver']].update(
            content=[{'type': 'text', 'text': marker}], _meta={'authorization': marker})
        value['results'][diag.QUERIES['driver']]['structuredContent']['token'] = marker
        value['results']['nvapp_private_tool'] = {'structuredContent': {'secret': marker}}
        report = diag.summarize_snapshot(value, NOW)
        self.assertEqual('ready', report['status'])
        self.assertNotIn(marker, json.dumps(report))

    def test_unavailable_optimization_reason_is_preserved_without_enabling_actions(self):
        value = snapshot()
        value['results'][diag.QUERIES['applications']]['structuredContent'] = {'applications': [{
            'game': 'Exact App', 'opsSupported': True,
            'optimizationProfiles': {'ac': {'availablePresets': [],
                                          'unavailableReason': 'game_configuration_unavailable'}}}]}
        result = diag.summarize_snapshot(value, NOW)
        app = result['queries']['applications']['data']['applications'][0]
        self.assertEqual('game_configuration_unavailable', app['optimizationProfiles']['ac']['unavailableReason'])
        self.assertNotIn('actions', app)

    def test_dry_run_does_not_read_input_or_write_output(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(diag, 'ROOT', Path(directory)), patch.object(diag, 'local_presence', side_effect=AssertionError()):
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(0, diag.main(['--snapshot', 'nonexistent.json', '--dry-run']))
            self.assertEqual([], list(Path(directory).iterdir()))

    def test_cli_no_snapshot_and_invalid_input_have_distinct_exit_codes(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(diag, 'ROOT', Path(directory)), patch.object(diag, 'local_presence', return_value={'status': 'not_installed'}):
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(0, diag.main(['--engine', 'Unreal']))
                reports = list(Path(directory).rglob('result.json'))
                self.assertEqual(1, len(reports))
                self.assertEqual('not_queried', json.loads(reports[0].read_text())['mcp']['status'])
                invalid = Path(directory) / 'bad.json'
                invalid.write_text('null', encoding='utf8')
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    self.assertEqual(2, diag.main(['--snapshot', str(invalid)]))
                self.assertEqual('invalid_snapshot', json.loads(output.getvalue())['status'])
                self.assertEqual(1, len(list(Path(directory).rglob('result.json'))))

    @unittest.skipUnless(os.name == 'nt', 'Windows shared PowerShell entry')
    def test_both_shared_routes_work_without_engine_configs(self):
        shell = shutil.which('pwsh') or shutil.which('powershell')
        if not shell:
            self.skipTest('PowerShell not installed')
        with tempfile.TemporaryDirectory(prefix='nvidia shared route ') as directory:
            root = Path(directory)
            tools = root / 'Tools'
            tools.mkdir()
            for name in ('Invoke-Workbench.ps1', 'nvidia_diagnostics.py'):
                shutil.copyfile(ROOT / 'Tools' / name, tools / name)
            for engine in ('Unity', 'Unreal'):
                result = subprocess.run([shell, '-NoProfile', '-File', str(tools / 'Invoke-Workbench.ps1'),
                                         '-Engine', engine, '-Action', 'NvidiaCheck'],
                                        capture_output=True, text=True, timeout=30)
                self.assertEqual(0, result.returncode, result.stderr)
                self.assertEqual('not_queried', json.loads(result.stdout)['status'])
            self.assertEqual(2, len(list(root.rglob('result.json'))))


if __name__ == '__main__':
    unittest.main()
