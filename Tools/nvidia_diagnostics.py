"""Optional shared NVIDIA diagnostics; native MCP calls belong to the Codex host.

This module never starts a server, launches a game, changes settings or reads
discovery/config credentials. A supplied snapshot is data, not an authenticated
attestation or a performance test.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
QUERIES = {
    'driver': 'nvapp_client_get_driver_status',
    'applications': 'nvapp_client_get_applications',
    'overlay': 'nvapp_overlay_get_status',
    'current_game': 'nvapp_overlay_get_current_game_info',
}
CHANNELS = ('GAME_READY', 'STUDIO', 'NVIDIA_RECOMMENDED', 'LEADING_EDGE', 'CONSERVATIVE')
PRESETS = {'Balanced', 'Performance', 'Recommended', 'Quality'}


def local_presence(environment=None, platform=None):
    env = os.environ if environment is None else environment
    platform = sys.platform if platform is None else platform
    if platform != 'win32':
        return {'status': 'unsupported_platform', 'bridge_present': False}
    program_files = env.get('ProgramFiles')
    local_app_data = env.get('LOCALAPPDATA')
    bridge = (Path(program_files) / 'NVIDIA Corporation/NVIDIA App/McpServer/NvAppMcpServer.exe'
              if program_files else None)
    manifests = [Path(local_app_data) / path for path in (
        'NVIDIA Corporation/NVIDIA App/McpServer/server.json',
        'NVIDIA Corporation/NvAppMcpServer/server.json')] if local_app_data else []
    present = bridge is not None and bridge.is_file()
    return {'status': 'bridge_found' if present else 'not_installed',
            'bridge_present': present,
            'discovery_file_present': any(p.is_file() for p in manifests)}


def sanitize_data(query, data):
    """Select only useful typed fields; never copy MCP text, headers or metadata."""
    if not isinstance(data, dict):
        raise ValueError('missing_structured_content')
    clean = {}
    if query == 'driver':
        installed = data.get('installedDriver')
        if not isinstance(installed, dict) or not isinstance(installed.get('version'), str):
            raise ValueError('invalid_driver_result')
        if not re.fullmatch(r'[0-9]+(?:\.[0-9]+){1,3}', installed['version']):
            raise ValueError('invalid_driver_version')
        clean['installedDriver'] = {'version': installed['version']}
        if installed.get('channel') in CHANNELS:
            clean['installedDriver']['channel'] = installed['channel']
        if data.get('systemType') in ('GEFORCE', 'WORKSTATION'):
            clean['systemType'] = data['systemType']
    elif query == 'applications':
        apps = data.get('applications')
        if not isinstance(apps, list):
            raise ValueError('invalid_applications_result')
        selected = []
        for app in apps:
            if not isinstance(app, dict) or not isinstance(app.get('game'), str):
                raise ValueError('invalid_application')
            item = {'game': app['game']}
            for key in ('opsSupported', 'belowMinimumSpec', 'isCreativeApp'):
                if type(app.get(key)) is bool:
                    item[key] = app[key]
            profiles = app.get('optimizationProfiles')
            if isinstance(profiles, dict):
                item['optimizationProfiles'] = {}
                for power in ('ac', 'battery'):
                    profile = profiles.get(power)
                    if not isinstance(profile, dict):
                        continue
                    p = {}
                    if profile.get('currentState') in ('DISABLED', 'UNOPTIMIZED', 'CUSTOMIZED', 'OPTIMIZED', 'UNKNOWN'):
                        p['currentState'] = profile['currentState']
                    if isinstance(profile.get('availablePresets'), list):
                        p['availablePresets'] = [v for v in profile['availablePresets'] if isinstance(v, str) and v in PRESETS]
                    if isinstance(profile.get('unavailableReason'), str):
                        p['unavailableReason'] = profile['unavailableReason']
                    item['optimizationProfiles'][power] = p
            selected.append(item)
        clean['applications'] = selected
    elif query == 'overlay':
        for key in ('statsOverlayEnabled', 'recordingActive', 'instantReplayEnabled',
                    'highlightsEnabled', 'desktopCapture'):
            if type(data.get(key)) is bool:
                clean[key] = data[key]
        if not clean:
            raise ValueError('invalid_overlay_result')
    elif query == 'current_game':
        if type(data.get('running')) is not bool:
            raise ValueError('invalid_current_game_result')
        clean['running'] = data['running']
        if data['running']:
            if isinstance(data.get('gameName'), str):
                clean['gameName'] = data['gameName']
            if type(data.get('fullscreen')) is bool:
                clean['fullscreen'] = data['fullscreen']
    return clean


def summarize_snapshot(snapshot, now):
    if (not isinstance(snapshot, dict) or snapshot.get('schema_version') != 1
            or snapshot.get('source') != 'codex-native-tools'
            or not isinstance(snapshot.get('results'), dict)):
        raise ValueError('invalid_snapshot_envelope')
    try:
        collected = datetime.fromisoformat(snapshot['collected_at'].replace('Z', '+00:00'))
        if collected.tzinfo is None:
            raise ValueError('timezone required')
        age = (now - collected).total_seconds()
    except (KeyError, TypeError, AttributeError, ValueError):
        raise ValueError('invalid_snapshot_time') from None
    if not -30 <= age <= 900:
        raise ValueError('snapshot_outside_15_minute_window')
    results = {}
    for query, tool in QUERIES.items():
        result = snapshot['results'].get(tool)
        if result is None:
            results[query] = {'status': 'not_queried'}
            continue
        if not isinstance(result, dict) or ('isError' in result and type(result['isError']) is not bool):
            results[query] = {'status': 'invalid_result'}
            continue
        if result.get('isError') is True:
            error = {'status': 'error'}
            data = result.get('structuredContent')
            if isinstance(data, dict):
                code = data.get('code')
                if isinstance(code, str) and re.fullmatch(r'[A-Za-z][A-Za-z0-9_.:-]{0,99}', code):
                    error['code'] = code
                if type(data.get('retryable')) is bool:
                    error['retryable'] = data['retryable']
            results[query] = error
            continue
        try:
            data = sanitize_data(query, result.get('structuredContent'))
            results[query] = {'status': 'ok', 'data': data}
        except ValueError as exc:
            results[query] = {'status': 'invalid_result', 'code': str(exc)}
    count = sum(r['status'] == 'ok' for r in results.values())
    return {'status': 'ready' if count == len(QUERIES) else 'partial' if count else 'unavailable',
            'source': 'supplied_native_mcp_snapshot', 'collected_at': collected.isoformat(),
            'queries': results}


def make_report(engine, snapshot=None, now=None, presence=None):
    now = now or datetime.now(timezone.utc)
    observation = {'status': 'not_queried', 'source': 'no_snapshot'}
    if snapshot is not None:
        observation = summarize_snapshot(snapshot, now)
    return {'schema_version': 1, 'engine': engine, 'optional': True,
            'generated_at': now.isoformat(),
            'scope': 'workstation diagnostics only; no GPU render, performance or gameplay acceptance',
            'local': local_presence() if presence is None else presence,
            'mcp': observation,
            'next_step': ('Use native NVIDIA App tools in Codex to collect a fresh snapshot.'
                          if snapshot is None else 'Interpret each query separately; never infer missing fields.'),
            'performance_metrics_collected': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engine', choices=('Unity', 'Unreal'), default='Unity')
    parser.add_argument('--snapshot', type=Path, help='Fresh native MCP results; never server.json or Codex config')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args(argv)
    if args.dry_run:
        print(json.dumps({'engine': args.engine, 'action': 'NvidiaCheck', 'optional': True,
                          'native_calls': False, 'writes': False}))
        return 0
    try:
        snapshot = None
        if args.snapshot:
            if args.snapshot.stat().st_size > 2 * 1024 * 1024:
                raise ValueError('snapshot_too_large')
            snapshot = json.loads(args.snapshot.read_text(encoding='utf-8-sig'))
            if snapshot is None:
                raise ValueError('invalid_snapshot_envelope')
        report = make_report(args.engine, snapshot)
    except (OSError, UnicodeError, ValueError, RecursionError):
        # Do not echo malformed input, paths or secrets from an accidentally supplied file.
        print(json.dumps({'status': 'invalid_snapshot', 'optional': True,
                          'message': 'Supply fresh native tool results in the documented envelope.'}))
        return 2
    output = ROOT / 'Evidence/Nvidia' / uuid.uuid4().hex
    output.mkdir(parents=True, exist_ok=False)
    (output / 'result.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps({'status': report['mcp']['status'], 'optional': True,
                      'report': str(output / 'result.json')}, ensure_ascii=False))
    # Absent hardware, unqueried MCP or unavailable Overlay is an optional skip.
    return 0


if __name__ == '__main__':
    sys.exit(main())
