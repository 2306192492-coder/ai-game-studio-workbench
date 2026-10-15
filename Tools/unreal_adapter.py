"""Windows UE5 adapter. Dry runs never start processes or create evidence."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'Config/unreal.local.json'
MAP = re.compile(r'^/Game/AIStudio/[A-Za-z0-9_]+(?:/[A-Za-z0-9_]+)*$')


def load_config(path=CONFIG):
    if not path.is_file():
        raise ValueError('Run Initialize-Workstation.ps1 and edit Config/unreal.local.json')
    config = json.loads(path.read_text(encoding='utf-8-sig'))
    config['engine_root'] = str(Path(config['engine_root']).resolve())
    config['project'] = str((ROOT / config['project']).resolve())
    if not MAP.fullmatch(config['map_asset']):
        raise ValueError('Validation map must be in /Game/AIStudio with simple asset names')
    if config.get('build_configuration', 'Development') not in {'Development', 'Shipping'}:
        raise ValueError('Unsupported build configuration')
    if not 1 <= int(config.get('timeout_seconds', 600)) <= 7200:
        raise ValueError('Timeout must be between 1 and 7200 seconds')
    return config


def engine_paths(config):
    engine = Path(config['engine_root']) / 'Engine'
    return {'editor': engine / 'Binaries/Win64/UnrealEditor.exe',
            'commandlet': engine / 'Binaries/Win64/UnrealEditor-Cmd.exe',
            'uat': engine / 'Build/BatchFiles/RunUAT.bat',
            'version': engine / 'Build/Build.version'}


def file_sha256(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def import_destination_valid(destination):
    base = '/Game/AIStudio/Imports'
    return bool(MAP.fullmatch(destination) and (destination == base or destination.startswith(base + '/')))


def verified_package(report_path, project_name):
    report = json.loads(report_path.read_text(encoding='utf-8-sig'))
    if report.get('action') != 'build' or report.get('passed') is not True or not report.get('files'):
        raise ValueError('Supply a successful build result.json with a nonempty file inventory')
    if report.get('configuration') != 'Development':
        raise ValueError('Finite package boot requires a recorded Development build')
    package = (report_path.parent / 'package').resolve()
    executables = []
    for item in report['files']:
        path = (package / item['path']).resolve()
        if not path.is_relative_to(package) or not path.is_file() or file_sha256(path) != item['sha256']:
            raise ValueError('Packaged file is missing, escaped the archive or changed: ' + item['path'])
        if path.name.lower() == (project_name + '.exe').lower():
            executables.append(path)
    if not executables:
        raise ValueError('Project launcher missing from verified package')
    return min(executables, key=lambda p: len(p.parts))


def package_boot_passed(log, map_asset, exit_code):
    loaded = re.search(r'Took [0-9.]+ seconds to LoadMap\(' + re.escape(map_asset) + r'\)', log)
    fatal = re.search(r'Fatal error:|Unhandled Exception:|Assertion failed:', log, re.IGNORECASE)
    return exit_code == 0 and loaded is not None and fatal is None


def make_plan(config, action, output, test_filter=None):
    paths = engine_paths(config)
    project = config['project']
    base = [str(paths['commandlet']), project, '-unattended', '-nop4', '-nosplash',
            '-nosound', '-NullRHI', '-UTF8Output', '-stdout', '-FullStdOutLogOutput',
            '-abslog=' + str(output / 'editor.log')]
    if action in {'prepare', 'probe', 'verify', 'import'}:
        return base + ['-run=pythonscript', '-script=' + str(ROOT / 'Adapters/Unreal/editor_task.py')]
    if action == 'start':
        return [str(paths['editor']), project, '-log']
    if action == 'test':
        if not test_filter or not re.fullmatch(r'[A-Za-z0-9_. +:-]+', test_filter):
            raise ValueError('Supply a real test name/filter using --filter; command separators are forbidden')
        return base + ['-ExecCmds=Automation RunTests ' + test_filter,
                       '-TestExit=Automation Test Queue Empty',
                       '-ReportExportPath=' + str(output / 'automation')]
    if action == 'build':
        return [str(paths['uat']), 'BuildCookRun', '-project=' + project, '-noP4',
                '-platform=Win64', '-clientconfig=' + config.get('build_configuration', 'Development'),
                '-build', '-cook', '-stage', '-pak', '-iostore', '-package', '-archive',
                '-map=' + config['map_asset'], '-unattended', '-utf8output',
                '-archivedirectory=' + str(output / 'package')]
    raise ValueError('Unsupported action: ' + action)


def automation_passed(report):
    """An empty selection, missing counters, pending tests or any failure cannot pass."""
    keys = ('succeeded', 'succeededWithWarnings', 'failed', 'notRun', 'inProcess')
    if not all(k in report and type(report[k]) is int and report[k] >= 0 for k in keys):
        return False
    return (report['succeeded'] + report['succeededWithWarnings'] > 0
            and report['failed'] == report['notRun'] == report['inProcess'] == 0)


def editor_passed(report, request):
    checks = report.get('checks')
    return (report.get('runId') == request['runId'] and report.get('action') == request['action']
            and report.get('passed') is True and isinstance(checks, list) and len(checks) > 0
            and all(c.get('passed') is True for c in checks))


def validate_import(asset_id, source):
    if not asset_id or not source:
        raise ValueError('Import requires --asset-id and --source registered in the shared manifest')
    integration = ROOT / 'Integrations/HybridAssets'
    manifest = json.loads((integration / 'Registry/asset-manifest.json').read_text(encoding='utf-8-sig'))
    record = next((a for a in manifest['assets'] if a['id'] == asset_id), None)
    path = Path(source).resolve()
    if path.suffix.lower() not in {'.fbx', '.png', '.jpg', '.jpeg', '.tga', '.exr'}:
        raise ValueError('Initial UE import adapter accepts FBX and image textures')
    if record is None or not any((integration / f['path']).resolve() == path for f in record.get('files', [])):
        raise ValueError('Source file must belong to the selected asset record')
    gate = subprocess.run([sys.executable, str(integration / 'Tools/asset_gate.py'),
                           '--asset', asset_id, '--engine', 'Unreal', '--stage', 'import'],
                          capture_output=True, text=True, encoding='utf8')
    if gate.returncode:
        raise ValueError('Shared asset gate refused import: ' + gate.stdout.strip())
    return str(path)


def batch_command(command):
    # A .bat is interpreted by cmd.exe on Windows. Reject expansion/control characters.
    if any(re.search(r'["%&|<>^!\r\n]', value) for value in command):
        raise ValueError('Batch arguments contain unsupported shell control characters')
    line = ' '.join('"' + value + '"' for value in command)
    # Pass the complete command line as a string: list2cmdline's backslash escaping
    # is for C argv parsing, whereas cmd.exe needs doubled outer quotes for /s /c.
    return '"' + os.environ.get('COMSPEC', 'cmd.exe') + '" /d /s /c "' + line + '"'


def execute(command, output, request, timeout):
    environment = os.environ.copy()
    environment['AISTUDIO_UE_REQUEST'] = str(output / 'request.json')
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    actual = batch_command(command) if command[0].lower().endswith('.bat') else command
    with (output / 'process.log').open('wb') as log:
        process = subprocess.Popen(actual, env=environment, stdout=log, stderr=subprocess.STDOUT,
                                   creationflags=creationflags)
        try:
            return process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            # Only this invocation's child is terminated; existing Editors are untouched.
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            raise ValueError('Owned UE task timed out; logs retained. Check any UAT children before retrying')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['status', 'start', 'prepare', 'probe', 'verify', 'import', 'build', 'test', 'run'])
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--asset-id')
    parser.add_argument('--source')
    parser.add_argument('--destination', default='/Game/AIStudio/Imports')
    parser.add_argument('--filter')
    parser.add_argument('--build-report', type=Path)
    args = parser.parse_args(argv)
    config = load_config()
    paths = engine_paths(config)
    if args.action == 'status':
        version = json.loads(paths['version'].read_text(encoding='utf-8-sig')) if paths['version'].is_file() else None
        ready = Path(config['project']).is_file() and all(paths[k].is_file() for k in ('editor', 'commandlet', 'uat'))
        print(json.dumps({'engine': 'Unreal', 'installed': ready, 'version': version,
                          'project': config['project'], 'scope': 'File inventory only; no runtime proof'}, indent=2))
        return 0 if ready else 1
    run_id = uuid.uuid4().hex
    output = ROOT / 'Evidence/Unreal' / (args.action + '-' + run_id)
    if args.action == 'run':
        if not args.build_report:
            raise ValueError('Run requires --build-report pointing to the exact build result.json')
        if config.get('build_configuration', 'Development') != 'Development':
            raise ValueError('Finite benchmark boot check requires a Development build')
        launcher = verified_package(args.build_report.resolve(), Path(config['project']).stem)
        command = [str(launcher), '-NullRHI', '-nosound', '-unattended', '-nosplash',
                   '-benchmark', '-seconds=3', '-fps=30', '-stdout', '-FullStdOutLogOutput',
                   '-abslog=' + str(output / 'game.log')]
    else:
        command = make_plan(config, args.action, output, args.filter)
    request = {'runId': run_id, 'action': args.action, 'project': config['project'],
               'map': config['map_asset'], 'report': str(output / 'editor-report.json')}
    if args.action == 'import':
        if not import_destination_valid(args.destination):
            raise ValueError('Import destination must be in /Game/AIStudio/Imports')
        request.update(source=args.source, destination=args.destination)
        if not args.dry_run:
            request['source'] = validate_import(args.asset_id, args.source)
    if args.dry_run:
        print(json.dumps({'engine': 'Unreal', 'action': args.action, 'command': command,
                          'scope': 'Plan only; no process, asset gate or engine validation'}, indent=2))
        return 0
    if not Path(command[0]).is_file() or not Path(config['project']).is_file():
        raise ValueError('Configured engine executable or project is missing')
    if args.action == 'start':
        process = subprocess.Popen(command)
        print(json.dumps({'startedPid': process.pid, 'scope': 'Editor started only; not validated'}))
        return 0
    output.mkdir(parents=True, exist_ok=False)
    (output / 'request.json').write_text(json.dumps(request, indent=2), encoding='utf8')
    exit_code = execute(command, output, request, int(config.get('timeout_seconds', 600)))
    result = {'engine': 'Unreal', 'action': args.action, 'runId': run_id,
              'exitCode': exit_code, 'completedUtc': datetime.now(timezone.utc).isoformat(),
              'passed': False, 'scope': 'NullRHI editor data checks; no GPU rendering or gameplay proof'}
    if args.action == 'run':
        log_file = output / 'game.log'
        log = log_file.read_text(encoding='utf-8-sig', errors='replace') if log_file.is_file() else ''
        result['passed'] = package_boot_passed(log, config['map_asset'], exit_code)
        result['scope'] = 'Verified package boot and map load under NullRHI; no GPU frame or player input proof'
    elif args.action == 'build':
        result['configuration'] = config.get('build_configuration', 'Development')
        files = sorted(p for p in (output / 'package').rglob('*') if p.is_file())
        result['files'] = [{'path': p.relative_to(output / 'package').as_posix(),
                            'sha256': file_sha256(p)} for p in files]
        result['passed'] = exit_code == 0 and any(p.suffix.lower() == '.exe' for p in files) and any(p.suffix.lower() == '.pak' for p in files)
        result['scope'] = 'UAT process and archive file inventory; packaged game has not been launched'
    elif args.action == 'test':
        report_file = output / 'automation/index.json'
        report = json.loads(report_file.read_text(encoding='utf-8-sig')) if report_file.is_file() else {}
        result['passed'] = exit_code == 0 and automation_passed(report)
        result['scope'] = 'Selected UE Automation tests under NullRHI; not visual or physical input acceptance'
    else:
        report_file = output / 'editor-report.json'
        report = json.loads(report_file.read_text(encoding='utf-8-sig')) if report_file.is_file() else {}
        result['passed'] = exit_code == 0 and editor_passed(report, request)
        result['editor'] = report
    (output / 'result.json').write_text(json.dumps(result, indent=2), encoding='utf8')
    print(json.dumps({'passed': result['passed'], 'report': str(output / 'result.json'),
                      'scope': result['scope']}, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError, KeyError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(2)
