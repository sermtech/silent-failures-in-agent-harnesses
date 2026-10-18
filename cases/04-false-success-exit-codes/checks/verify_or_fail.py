"""verify_or_fail: run a command, then check a POSTCONDITION, not the exit code.

Usage as a library:
    run_and_verify(["curl", "-fL", "-o", "m.gguf", url],
                   sha256_is("m.gguf", "<lfs.oid>"))
Postconditions are callables returning (ok: bool, detail: str).
Fail-fast: any failed postcondition raises PostconditionFailed, even when exit == 0.
Run `python -X utf8 verify_or_fail.py` for the self-test.
"""
import hashlib
import os
import subprocess
import sys
import tempfile
import urllib.request
import urllib.error


class PostconditionFailed(RuntimeError):
    pass


def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def file_hash_changed(path):
    """Snapshot now; the returned check passes only if the hash differs afterwards."""
    before = _sha(path) if os.path.exists(path) else None
    def check():
        after = _sha(path) if os.path.exists(path) else None
        return after != before, f"{os.path.basename(path)}: sha256 before={before and before[:12]} after={after and after[:12]}"
    return check


def size_equals(path, expected):
    def check():
        got = os.path.getsize(path) if os.path.exists(path) else -1
        return got == expected, f"{os.path.basename(path)}: size {got} expected {expected}"
    return check


def sha256_is(path, expected):
    def check():
        got = _sha(path) if os.path.exists(path) else "<missing>"
        return got == expected.lower(), f"{os.path.basename(path)}: sha256 {got[:12]} expected {expected[:12]}"
    return check


def http_status_is(url, expected=200, timeout=10):
    def check():
        try:
            code = urllib.request.urlopen(url, timeout=timeout).status
        except urllib.error.HTTPError as e:
            code = e.code
        return code == expected, f"GET {url}: status {code} expected {expected}"
    return check


def run_and_verify(cmd, *postconditions):
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise PostconditionFailed(f"command exited {proc.returncode}: {proc.stderr.strip()[:200]}")
    for check in postconditions:
        ok, detail = check()
        if not ok:
            raise PostconditionFailed(f"exit code was 0 but postcondition FAILED: {detail}")
    return proc


def _selftest():
    tmp = tempfile.mkdtemp()
    target = os.path.join(tmp, "models.json")
    with open(target, "w") as f:
        f.write('{"models": []}')
    # A "lying" command: prints a success line, exits 0, changes nothing.
    liar = [sys.executable, "-c", "print('Model catalogs refreshed'); raise SystemExit(0)"]
    # An honest command: actually rewrites the file.
    honest = [sys.executable, "-c", f"open(r'{target}','w').write('{{\"models\": [1]}}')"]
    failures = 0

    print("1) lying command (exit 0, success text, no effect), postcondition: file hash changed")
    try:
        run_and_verify(liar, file_hash_changed(target))
        print("   MISSED the lie")
        failures += 1
    except PostconditionFailed as e:
        print("   CAUGHT:", e)

    print("2) honest command, same postcondition")
    try:
        run_and_verify(honest, file_hash_changed(target))
        print("   PASSED as expected")
    except PostconditionFailed as e:
        print("   unexpected failure:", e)
        failures += 1

    print("3) truncated download (exit 0, 5 of 10 bytes), postcondition: size equals 10")
    dl = os.path.join(tmp, "model.bin")
    short = [sys.executable, "-c", f"open(r'{dl}','wb').write(b'12345')"]
    try:
        run_and_verify(short, size_equals(dl, 10))
        print("   MISSED the truncation")
        failures += 1
    except PostconditionFailed as e:
        print("   CAUGHT:", e)

    print("4) wrong checksum on the same file")
    try:
        run_and_verify([sys.executable, "-c", "pass"], sha256_is(dl, "0" * 64))
        print("   MISSED the mismatch")
        failures += 1
    except PostconditionFailed as e:
        print("   CAUGHT:", e)

    print("SELFTEST", "PASSED" if failures == 0 else "FAILED")
    return failures


if __name__ == "__main__":
    sys.exit(1 if _selftest() else 0)
