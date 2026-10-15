"""Read the approved Asset Store archive without extracting or executing it."""
import argparse, hashlib, json, tarfile
from collections import Counter
from pathlib import Path, PurePosixPath

parser = argparse.ArgumentParser()
parser.add_argument("package", type=Path)
args = parser.parse_args()
paths = []
with tarfile.open(args.package, "r:gz") as archive:
    for member in archive:
        if member.isfile() and member.name.endswith("/pathname"):
            path = archive.extractfile(member).read().decode("utf-8-sig").splitlines()[0].strip()
            normalized = PurePosixPath(path.replace("\\", "/"))
            if normalized.is_absolute() or ".." in normalized.parts or ":" in path:
                raise ValueError("Unsafe archive asset path")
            paths.append(path)
counts = Counter(Path(p).suffix.lower() or "directory" for p in paths)
report = dict(passed=bool(paths), package=str(args.package), bytes=args.package.stat().st_size,
              sha256=hashlib.file_digest(args.package.open("rb"), "sha256").hexdigest(),
              assetCount=len(paths), extensionCounts=dict(counts), assetPaths=paths,
              scope="Archive structure and source asset inventory; Unity import reported separately")
output = Path(__file__).resolve().parents[1]/"Evidence"/"assetstore-package-inspection.json"
output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({k:v for k,v in report.items() if k != "assetPaths"}, ensure_ascii=False))
