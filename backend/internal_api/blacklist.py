from pathlib import Path
from backend.logger import get_logger

log = get_logger()

ROOT = Path(__file__).parent.parent.parent
BLACKLIST_PATH = ROOT / "data" / "synthetic" / "blacklist.csv"

_blacklist: set = set()


def load_blacklist() -> None:
    global _blacklist
    if not BLACKLIST_PATH.exists():
        log.warning("blacklist", status="file_not_found", path=str(BLACKLIST_PATH))
        _blacklist = set()
        return

    with open(BLACKLIST_PATH, "r") as f:
        _blacklist = {line.strip() for line in f if line.strip()}

    log.info("blacklist", status="loaded", count=len(_blacklist))


def is_blacklisted(account_id: str) -> bool:
    return account_id in _blacklist


def get_blacklist() -> set:
    return _blacklist