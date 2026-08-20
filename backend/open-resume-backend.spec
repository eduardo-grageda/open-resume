# -*- mode: python ; coding: utf-8 -*-

import sys

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['..'],
    binaries=[],
    datas=[],
    hiddenimports=[
        'uvicorn',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'fastapi',
        'fastapi.middleware',
        'fastapi.middleware.cors',
        'pydantic',
        'pydantic.deprecated',
        'pydantic.decorators',
        'weasyprint',
        'pdfplumber',
        'markdown2',
        'beautifulsoup4',
        'bs4',
        'apscheduler',
        'apscheduler.schedulers',
        'apscheduler.schedulers.asyncio',
        'apscheduler.schedulers.base',
        'apscheduler.jobstores',
        'apscheduler.jobstores.base',
        'apscheduler.jobstores.memory',
        'apscheduler.triggers',
        'apscheduler.triggers.cron',
        'pymongo',
        'httpx',
        'python_multipart',
        'multipart',
        'email.mime',
        'email.mime.text',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'unittest',
        'test',
        'setuptools',
        'pip',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

a.binaries += collect_dynamic_libs('curl_cffi')

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='open-resume-backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)