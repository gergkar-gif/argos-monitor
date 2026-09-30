"""Fetching through curl: it uses the Windows certificate store (Dan tri fails the TLS check in Python)."""
import subprocess
from .config import COOKIE_JAR, USER_AGENT


def get(url, timeout=30):
    """Return (status_code, body_bytes). Status 0 means the connection failed."""
    p = subprocess.run(
        ["curl", "-sL", "-m", str(timeout), "--compressed", "-A", USER_AGENT,
         "-c", str(COOKIE_JAR), "-b", str(COOKIE_JAR), "-w", "\n%{http_code}", url],
        capture_output=True)
    body, _, code = p.stdout.rpartition(b"\n")
    try:
        return int(code), body
    except ValueError:
        return 0, b""
