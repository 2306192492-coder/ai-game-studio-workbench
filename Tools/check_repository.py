"""Check the source-only publication boundary without starting any production tool."""
import ast
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BINARY_SUFFIXES = {'.fbx', '.glb', '.blend', '.png', '.jpg', '.wav', '.mp4',
                   '.safetensors', '.pt', '.pth', '.exe', '.dll', '.zip', '.unitypackage',
                   '.uasset', '.umap', '.pak', '.utoc', '.ucas', '.pdb'}
PRIVATE_PARTS = {'Backups', 'Downloads', 'Models', 'Runtime', 'Builds', 'Library',
                 'Temp', 'Logs', 'UserSettings', '__pycache__', 'Saved', 'Intermediate',
                 'DerivedDataCache', 'Binaries', '.vs'}
TOKEN = re.compile(r'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|'
                   r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)')
PERSONAL_PATH = re.compile(r'[A-Za-z]:[\\/]Users[\\/](?!Public[\\/]|Default[\\/])[^\\/\s"\']+')
INI_SECRET = re.compile(r'^[ \t]*(?:SecurityToken|AuthToken|ApiKey|Password|ClientSecret)[ \t]*=[ \t]*\S[^\r\n]*$', re.MULTILINE | re.IGNORECASE)


def check_file(relative, content):
    path = Path(relative)
    problems = []
    # Runtime source directories are code; runtime output at repository root is private.
    private = set(path.parts[:-1]) & (PRIVATE_PARTS - {'Runtime'})
    if path.parts[0] in {'Runtime', 'Evidence', 'AssetsSource'} or private:
        problems.append('private output/input directory')
    if path.name in {'machine.json', 'workstation.local.json', 'unreal.local.json'} or path.name.startswith('.env'):
        problems.append('local configuration')
    if path.suffix.lower() in BINARY_SUFFIXES:
        problems.append('binary asset or package')
    if TOKEN.search(content) or (path.suffix.lower() == '.ini' and INI_SECRET.search(content)):
        problems.append('credential-like content')
    if PERSONAL_PATH.search(content):
        problems.append('personal workstation path')
    if path.suffix == '.py':
        try:
            ast.parse(content, filename=relative)
        except SyntaxError:
            problems.append('Python syntax error')
    if path.suffix in {'.json', '.asmdef', '.uproject', '.uplugin'}:
        try:
            json.loads(content)
        except ValueError:
            problems.append('JSON syntax error')
    return problems


def publication_files(root):
    if (root / '.git').exists():
        result = subprocess.run(['git', '-C', str(root), 'ls-files', '-z'],
                                check=True, capture_output=True)
        return [root / name.decode('utf8') for name in result.stdout.split(b'\0') if name]
    return [p for p in root.rglob('*') if p.is_file() and '.git' not in p.parts
            and '__pycache__' not in p.parts]


def main():
    failures = []
    files = publication_files(ROOT)
    for file in files:
        relative = file.relative_to(ROOT).as_posix()
        try:
            content = file.read_text(encoding='utf-8-sig')
        except UnicodeError:
            failures.append((relative, ['non-text file']))
            continue
        problems = check_file(relative, content)
        if problems:
            failures.append((relative, problems))
    print(json.dumps({'scope': 'source publication boundary; no Unity/game validation',
                      'files': len(files), 'passed': not failures,
                      'failures': failures}, ensure_ascii=False, indent=2))
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
