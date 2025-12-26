# -*- mode: python ; coding: utf-8 -*-

import os
from pathlib import Path

# 获取项目根目录（AllBuilder 的父目录）
project_root = Path(__file__).parent.parent.absolute()
websockify_script = project_root / "Websockify" / "websocketproxy.py"
websockify_dir = project_root / "Websockify"

a = Analysis(
    [str(websockify_script)],
    pathex=[str(project_root)],
    binaries=[],
    datas=[(str(websockify_dir), 'websockify')],
    hiddenimports=[
        # 只保留必需的核心依赖
        'websockify',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=2,  # 启用最高级别优化
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='websocketproxy',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,  # Windows上禁用strip（strip是Unix/Linux工具）
    upx=False,
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
