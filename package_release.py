from __future__ import annotations
import fnmatch, pathlib, zipfile

ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / 'dist' / 'Spaceline-0.9.6.zip'
EXCLUDED_DIRS = {'.git', '.venv', '__pycache__', 'build', 'dist', '.spaceline-chrome-profile'}
EXCLUDED_NAMES = {'.env'}

def included(path: pathlib.Path) -> bool:
    rel = path.relative_to(ROOT)
    if any(part in EXCLUDED_DIRS for part in rel.parts):
        return False
    if path.name in EXCLUDED_NAMES or path.name.startswith('.env.') and path.name != '.env.example':
        return False
    if path.name.endswith(('.pyc', '.pyo', '.sqlite3', '.sqlite3-wal', '.sqlite3-shm', '.pem', '.key')):
        return False
    if 'service-account' in path.name.lower() or 'firebase-adminsdk' in path.name.lower():
        return False
    return path.is_file()

OUT.parent.mkdir(exist_ok=True)
with zipfile.ZipFile(OUT, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=8) as archive:
    for path in sorted(ROOT.rglob('*')):
        if included(path):
            archive.write(path, path.relative_to(ROOT).as_posix())
with zipfile.ZipFile(OUT) as archive:
    names = archive.namelist()
    assert 'app/main.py' in names and 'static/index.html' in names and 'tests/test_api.py' in names
    assert '.env.example' in names
    assert not any(name == '.env' or name.endswith('.pem') or 'service-account' in name.lower() for name in names)
print(OUT)
print(f'{len(names)} files; paths preserved')
