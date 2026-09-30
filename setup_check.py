"""Run once: python setup_check.py. Creates the data folder and checks everything the pipeline needs."""
import os, shutil, sys, importlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = Path(os.environ.get("ARGOS_DATA_DIR", r"C:\ArgosData"))
problems = []

if "my drive" in str(DATA).lower() or str(DATA).lower().startswith(str(HERE.parent).lower()):
    problems.append(f"Data folder {DATA} looks like it is on Google Drive. Set ARGOS_DATA_DIR to a local folder.")
else:
    for sub in ("", "models", "out"):
        (DATA / sub).mkdir(parents=True, exist_ok=True)
    print(f"Data folder ready: {DATA}")

if sys.version_info < (3, 12):
    problems.append(f"Python {sys.version.split()[0]} is too old; need 3.12 or newer.")
for mod in ("yaml", "feedparser", "trafilatura", "sklearn", "jinja2"):
    try:
        importlib.import_module(mod)
    except ImportError:
        problems.append(f"Missing package '{mod}'. Run: python -m pip install -r requirements.txt")
if not shutil.which("curl"):
    problems.append("curl not found (needed to fetch some feeds).")
try:
    import yaml
    n = len(yaml.safe_load((HERE / "sources.yaml").read_text(encoding="utf8"))["sources"])
    print(f"sources.yaml loads: {n} sources")
except Exception as e:
    problems.append(f"sources.yaml problem: {e}")

if problems:
    print("\nSetup FAILED:")
    for p in problems:
        print(" -", p)
    sys.exit(1)
print("\nsetup OK")
