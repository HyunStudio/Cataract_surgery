# Build with: python -m PyInstaller --noconfirm OphthoSim.spec
from pathlib import Path
import importlib.util

for required in ('pygame', 'moderngl', 'glcontext'):
    if importlib.util.find_spec(required) is None:
        raise SystemExit(f'Missing build dependency: {required}. Install requirements-build.txt first.')

root = Path(SPECPATH)
a = Analysis([str(root / 'desktop.py')], pathex=[str(root)],
             binaries=[], datas=[(str(root / 'assets'), 'assets')],
             hiddenimports=['moderngl', 'glcontext', 'glcontext.wgl'],
             hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[],
             noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='OphthoSim',
          debug=False, bootloader_ignore_signals=False, strip=False,
          upx=False, console=True)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False,
               name='OphthoSim')
