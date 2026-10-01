import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("ARGOS_DATA_DIR", r"C:\ArgosData"))
DB_PATH = DATA_DIR / "argos.db"
COUNTRIES_DIR = ROOT / "countries"
# Some servers (VOV) refuse a browser-like User-Agent, so we identify honestly.
USER_AGENT = "Mozilla/5.0 (compatible; ArgosMonitor/0.1)"
COOKIE_JAR = DATA_DIR / "cookies.txt"  # QDND needs cookies kept between requests
