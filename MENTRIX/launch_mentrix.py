"""Simple Windows launcher: install small core requirements, choose a free local port, open browser."""
from __future__ import annotations
import getpass
import importlib
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time
import traceback
import urllib.request
import webbrowser

ROOT = Path(__file__).resolve().parent
LOG = ROOT / 'start_error_log.txt'
CORE_MODULES = ('fastapi', 'uvicorn', 'sympy', 'PIL', 'multipart', 'httpx', 'pydantic', 'fitz', 'pytesseract', 'qrcode')


def check_packages():
    # Never install project dependencies into the machine's global Python.
    if sys.prefix == sys.base_prefix:
        raise RuntimeError(
            'Please start via START_MENTRIX.bat, which creates an isolated .venv. '
            'Global Python package installations are disabled for safety.'
        )
    missing = []
    for module in CORE_MODULES:
        try:
            importlib.import_module(module)
        except ImportError:
            missing.append(module)
    if not missing:
        print('Libraries: ready.', flush=True)
        return
    print('Some libraries are missing: ' + ', '.join(missing), flush=True)
    print('Installing required libraries. Internet may be needed.', flush=True)
    result = subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', str(ROOT / 'requirements.txt')], cwd=ROOT)
    if result.returncode != 0:
        raise RuntimeError('Library installation failed. Check internet access, then run again.')
    for module in CORE_MODULES:
        importlib.import_module(module)
    print('Libraries installed.', flush=True)


def choose_port():
    # FIXED unique port to avoid silently opening an OLD MENTRIX app on :8010.
    port = 8765
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind(('127.0.0.1', port))
        except OSError:
            raise RuntimeError('Port 8765 is busy. Close other MENTRIX windows using 8765, then start this version again.')
    return port


def open_browser_when_ready(url):
    for _ in range(75):
        try:
            with urllib.request.urlopen(url + '/health', timeout=1) as response:
                if response.status == 200:
                    webbrowser.open(url + '/?build=mentrix-integrated-v1-sprint06-20261104')
                    return
        except Exception:
            time.sleep(0.4)
    print('Browser did not open. Copy this address into Chrome: ' + url, flush=True)


def main():
    print('MENTRIX INTEGRATED V1 + SPRINT 06 - NOV 2026', flush=True)
    print('Project folder: ' + str(ROOT), flush=True)
    print('This is a local test app, not a public student portal.\n', flush=True)
    check_packages()
    pin = os.environ.get('MENTRIX_STAFF_PIN', '')
    while len(pin) < 6:
        print('Create a staff PIN (6 or more characters).', flush=True)
        print('The PIN will NOT appear while you type. Press Enter when done.', flush=True)
        try:
            pin = getpass.getpass('Staff PIN: ')
        except (EOFError, KeyboardInterrupt):
            print('Start cancelled.')
            return 1
        if len(pin) < 6:
            print('Please use at least 6 characters.\n', flush=True)
    os.environ['MENTRIX_STAFF_PIN'] = pin
    admin_pin = os.environ.get('MENTRIX_ADMIN_PIN','')
    if len(admin_pin)<6:
        print('Optional Admin PIN (6+ characters); leave blank for TA-only login.',flush=True)
        try: admin_pin = getpass.getpass('Admin PIN (optional): ')
        except (EOFError, KeyboardInterrupt): admin_pin=''
    if len(admin_pin)>=6 and admin_pin!=pin: os.environ['MENTRIX_ADMIN_PIN']=admin_pin
    port = choose_port()
    url = f'http://127.0.0.1:{port}'
    print('\n------------------------------------------', flush=True)
    print('MENTRIX is starting...', flush=True)
    print('Website: ' + url, flush=True)
    print('Sign in with your TA PIN; optional Admin PIN has access to audit logs.', flush=True)
    print('DO NOT use old bookmarks such as 127.0.0.1:8010.', flush=True)
    print('IMPORTANT: Open ONLY this exact address, not port 8010.', flush=True)
    print('Keep this window open. Press Ctrl+C to stop.', flush=True)
    print('------------------------------------------\n', flush=True)
    threading.Thread(target=open_browser_when_ready, args=(url,), daemon=True).start()
    import uvicorn
    uvicorn.run('app:app', host='127.0.0.1', port=port, reload=False, log_level='info', access_log=False)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print('MENTRIX stopped.')
        sys.exit(0)
    except Exception:
        trace = traceback.format_exc()
        LOG.write_text(trace, encoding='utf-8')
        print('\nSTART ERROR: ' + str(trace.splitlines()[-1]), flush=True)
        print('More details: ' + str(LOG), flush=True)
        sys.exit(1)
