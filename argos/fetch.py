"""Fetching through curl: it uses the Windows certificate store (Dan tri fails the TLS check in Python)."""
import os
import subprocess
import tempfile
from .config import COOKIE_JAR, USER_AGENT


def get(url, timeout=15, etag=None, last_modified=None, return_headers=False):
    """Return (status_code, body_bytes) or (status_code, body_bytes, headers_dict).
    Status 0 means connection failed. Supports conditional GET headers (ETag, Last-Modified)
    inspired by Media Cloud ingestion."""
    cmd = [
        "curl", "-sL", "-m", str(timeout), "--compressed", "-A", USER_AGENT,
        "-c", str(COOKIE_JAR), "-b", str(COOKIE_JAR)
    ]
    if etag:
        cmd.extend(["-H", f'If-None-Match: "{etag.strip(chr(34))}"'])
    if last_modified:
        cmd.extend(["-H", f"If-Modified-Since: {last_modified}"])

    hpath = None
    if return_headers:
        with tempfile.NamedTemporaryFile(delete=False) as tf:
            hpath = tf.name
        cmd.extend(["-D", hpath])

    cmd.extend(["-w", "\n%{http_code}", url])
    p = subprocess.run(cmd, capture_output=True)
    body, _, code = p.stdout.rpartition(b"\n")
    try:
        status_code = int(code)
    except ValueError:
        status_code = 0

    if not return_headers:
        return status_code, body

    headers = {}
    if hpath and os.path.exists(hpath):
        try:
            with open(hpath, "r", encoding="latin1", errors="replace") as f:
                for line in f:
                    if ":" in line:
                        k, _, v = line.partition(":")
                        headers[k.strip().lower()] = v.strip()
            os.unlink(hpath)
        except OSError:
            pass

    return status_code, body, headers
