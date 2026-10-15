"""Stage approved sample Assets only in a fixed scratch project; retain packages/settings."""
import gzip, hashlib, json, shutil, tarfile, tempfile
from pathlib import Path, PurePosixPath
root = Path(__file__).resolve().parents[1]
report = json.loads((root/'Evidence/assetstore-package-inspection.json').read_text(encoding='utf-8-sig'))
source = Path(report['package'])
with source.open('rb') as stream:
    assert hashlib.file_digest(stream, 'sha256').hexdigest() == report['sha256']
target = (root/'Runtime/AssetStoreValidation').resolve()
assert target.is_relative_to(root.resolve()) and (target/'Packages/manifest.json').is_file()
written = 0
with tempfile.TemporaryFile(dir=root/'Runtime') as unpacked:
    with gzip.open(source, 'rb') as compressed:
        shutil.copyfileobj(compressed, unpacked, 4*1024*1024)
    unpacked.seek(0)
    archive = tarfile.open(fileobj=unpacked, mode='r:')
    members = {m.name:m for m in archive.getmembers()}
    for name, member in members.items():
        if not member.isfile() or not name.endswith('/pathname'):
            continue
        relative = PurePosixPath(archive.extractfile(member).read().decode('utf-8-sig').splitlines()[0])
        if not relative.parts or relative.parts[0] != 'Assets':
            continue
        if relative.is_absolute() or '..' in relative.parts or ':' in str(relative):
            raise ValueError('Unsafe sample asset path')
        destination = target.joinpath(*relative.parts).resolve()
        assert destination.is_relative_to(target)
        prefix = name.rsplit('/',1)[0]
        payload = members.get(prefix+'/asset')
        if payload and payload.isfile():
            data = archive.extractfile(payload).read()
            if destination.exists() and destination.read_bytes() != data:
                raise ValueError('Existing asset differs: '+str(relative))
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
            written += 1
        else:
            destination.mkdir(parents=True, exist_ok=True)
        metadata = members.get(prefix+'/asset.meta')
        meta_path = Path(str(destination)+'.meta')
        if metadata and metadata.isfile() and not meta_path.exists():
            meta_path.write_bytes(archive.extractfile(metadata).read())
print(json.dumps(dict(stagedAssets=written, target=str(target), sourceSha256=report['sha256'],
                     scope='Asset files and GUID metadata; source ProjectSettings and package versions not applied'),ensure_ascii=False))
