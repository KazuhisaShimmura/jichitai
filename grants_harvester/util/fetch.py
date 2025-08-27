
import time, os, json
from typing import Optional, Dict
import requests

DEFAULT_UA = "Eucalia-GrantsHarvester/1.0 (+https://example.org/)"
CACHE_DIR = os.environ.get("GRANTS_CACHE_DIR", ".cache/harvester")
os.makedirs(CACHE_DIR, exist_ok=True)
ETAG_DB = os.path.join(CACHE_DIR, "etag_index.json")

def _load_db() -> Dict:
    if os.path.exists(ETAG_DB):
        try:
            return json.load(open(ETAG_DB, "r", encoding="utf-8"))
        except (json.JSONDecodeError, IOError):
            return {}
    return {}

def _save_db(db: Dict):
    tmp = ETAG_DB + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)
    os.replace(tmp, ETAG_DB)

class HttpFetcher:
    def __init__(self, min_interval_sec: float = 0.0, timeout: float = 20.0, ua: str = DEFAULT_UA):
        self.min_interval_sec = min_interval_sec
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": ua})
        self._last_fetch = 0.0
        self._db = _load_db()

    def get(self, url: str, use_cache_headers: bool = True) -> requests.Response:
        # polite spacing
        now = time.time()
        if now - self._last_fetch < self.min_interval_sec:
            time.sleep(self.min_interval_sec - (now - self._last_fetch))
        self._last_fetch = time.time()

        headers = {}
        if use_cache_headers and url in self._db:
            meta = self._db[url]
            if "etag" in meta:
                headers["If-None-Match"] = meta["etag"]
            if "last_modified" in meta:
                headers["If-Modified-Since"] = meta["last_modified"]

        resp = self.session.get(url, headers=headers, timeout=self.timeout, allow_redirects=True)
        if resp.status_code == 304:
            # Return a minimal Response-like object with 304
            return resp

        # update cache headers
        etag = resp.headers.get("ETag")
        lm = resp.headers.get("Last-Modified")
        self._db[url] = {}
        if etag: self._db[url]["etag"] = etag
        if lm: self._db[url]["last_modified"] = lm
        _save_db(self._db)
        return resp
