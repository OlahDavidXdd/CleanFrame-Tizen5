"""Build and sign through an existing official Tizen SDK profile (Windows).

Mirrors package.py's checks and output, but uses subprocess pipes instead of
pty/termios (neither exists on Windows). Because stdin here is a plain pipe,
not a real terminal, the Tizen CLI's own password prompt may fail outright
(Java's Console is unavailable on a non-tty stdin) rather than being
answerable from this script. So this only supports the documented default:
signing with the SDK's own saved profile access (password_file left null /
omitted in .local/signing.json). If the SDK still asks for a password,
save it in Certificate Manager (so signing needs no prompt at all) instead
of relying on password_file here.
"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import zipfile

from font_assets import write_widget_archive
from local_config import ROOT, load_settings
from private_files import check_signed_widget


def sign(command, timeout=60):
    # SDK output can include profile credentials. Never copy it to diagnostics.
    process = subprocess.Popen(
        command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, bufsize=0,
    )
    output = b''
    deadline = time.monotonic() + timeout
    try:
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ValueError('SDK signing timed out.')
            chunk = process.stdout.read1(8192) if hasattr(process.stdout, 'read1') else process.stdout.read(8192)
            if not chunk:
                if process.poll() is not None:
                    break
                time.sleep(0.05)
                continue
            output += chunk
            if len(output) > 1024 * 1024:
                raise ValueError('SDK produced excessive signing output.')
            if b'password:' in output.lower():
                raise ValueError('SDK requested a password. This Windows runner cannot answer an interactive '
                                  'prompt here; save the profile password in Certificate Manager so signing needs none.')
        try:
            return process.wait(timeout=max(0, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            raise ValueError('SDK signing timed out.') from None
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()


def main(root=ROOT):
    if sys.platform != 'win32':
        raise SystemExit('This is the Windows signing runner. Use npm run package on macOS/Linux.')
    settings = load_settings(root)
    if settings['password_file'] is not None:
        raise ValueError('password_file is not supported by this Windows runner. '
                          'Leave it null/omitted in .local/signing.json and save the profile password in Certificate Manager instead.')
    cli = settings['sdk_path'] / 'tools/ide/bin/tizen.bat'
    if not cli.is_file():
        raise ValueError('Tizen CLI missing. Set sdk_path in .local/signing.json; see docs/development.md.')
    dist = root / 'dist'
    dist.mkdir(exist_ok=True)
    unsigned = dist / 'CleanFrame-unsigned.wgt'
    write_widget_archive(unsigned, root=root, identity=settings['identity'])
    # A fresh folder prevents a previous signed widget masking a failed build.
    signed_dir = Path(tempfile.mkdtemp(prefix='signed-', dir=dist))
    command = [str(cli), 'package', '-t', 'wgt', '-s', settings['profile'], '-o', str(signed_dir), '--', str(unsigned)]
    if sign(command):
        raise ValueError('SDK signing failed. Check the selected profile and password access in Certificate Manager.')
    signed = signed_dir / unsigned.name
    check_signed_widget(signed, settings['identity'])
    target = dist / 'CleanFrame.wgt'
    # Promote on the same filesystem so a failed copy preserves the last build.
    ready = signed_dir / 'validated.wgt'
    ready.write_bytes(signed.read_bytes())
    ready.replace(target)
    print('Signed widget created: ' + str(target))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, zipfile.BadZipFile) as error:
        # Known validation messages contain no credentials. Suppress SDK/OS payloads.
        message = str(error) if isinstance(error, ValueError) else 'Cannot complete packaging. Check SDK/profile setup and local file permissions.'
        raise SystemExit(message) from None
