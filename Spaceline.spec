# PyInstaller spec for Spaceline (Windows one-file executable).
from PyInstaller.utils.hooks import collect_all

datas = [("static", "static"), ("skills", "skills")]
binaries = []
hiddenimports = [
    "app.main",
    "app.ai_provider",
    "app.key_vault",
    "app.workspace",
    "app.browser",
    "app.skills",
    "app.document_reader",
    "playwright.sync_api",
    "pypdf",
    "multipart",
    "firebase_admin",
]

# Include dynamically imported ASGI and validation modules.
for package in ("uvicorn", "fastapi", "starlette", "pydantic", "httpx", "httpcore", "anyio", "playwright", "pypdf", "multipart", "firebase_admin"):
    package_datas, package_binaries, package_hiddenimports = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hiddenimports

a = Analysis(
    ["run.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Spaceline",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
