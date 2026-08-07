"""Cache-first HTTP client for the scraper.

Every page is fetched at most once per URL: if a cache file already exists
for a page, it is read from disk and the network is never touched (unless
force=True). Live requests are rate-limited to a minimum delay between
requests (BR's robots.txt sets a 3s crawl-delay for User-agent: *) and retry
with exponential backoff on transient failures / 403 / 429.
"""
import json
import random
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

USER_AGENT = (
    "BlitzMLBAllStarAggregator/1.0 "
    "(+contact: dannyross200316@gmail.com; take-home project; "
    "respects robots.txt crawl-delay)"
)

DEFAULT_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
}

MIN_DELAY_SECONDS = 3.0
JITTER_SECONDS = 1.5
MAX_RETRIES = 4
BACKOFF_BASE_SECONDS = 5.0


class FetchError(Exception):
    pass


def _now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _meta_path(cache_path: Path) -> Path:
    return cache_path.with_name(cache_path.name + ".meta.json")


class CachingClient:
    def __init__(self, min_delay=MIN_DELAY_SECONDS, force=False, session=None,
                 max_retries=MAX_RETRIES, sleep_fn=time.sleep):
        self.min_delay = min_delay
        self.force = force
        self.session = session or requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        self.max_retries = max_retries
        self._sleep = sleep_fn
        self._last_request_monotonic = None
        self.live_request_count = 0
        self.cache_hit_count = 0

    def fetch(self, url: str, cache_path: Path) -> tuple[str, dict]:
        """Return (html_text, meta) for url, using the on-disk cache first."""
        cache_path = Path(cache_path)
        meta_path = _meta_path(cache_path)

        if not self.force and cache_path.exists():
            self.cache_hit_count += 1
            html = cache_path.read_text(encoding="utf-8")
            meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {
                "url": url, "fetched_at": None, "from_cache_without_meta": True,
            }
            return html, meta

        html = self._fetch_live(url)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(html, encoding="utf-8")
        meta = {"url": url, "fetched_at": _now_iso()}
        meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        return html, meta

    def _throttle(self):
        if self._last_request_monotonic is not None:
            elapsed = time.monotonic() - self._last_request_monotonic
            wait = self.min_delay + random.uniform(0, JITTER_SECONDS) - elapsed
            if wait > 0:
                self._sleep(wait)
        self._last_request_monotonic = time.monotonic()

    def _fetch_live(self, url: str) -> str:
        last_exc = None
        for attempt in range(1, self.max_retries + 1):
            self._throttle()
            try:
                resp = self.session.get(url, timeout=20)
            except (requests.RequestException, MemoryError, OSError) as exc:
                # MemoryError/OSError can surface from a corrupted/truncated
                # response mid-stream; treat as transient like any other
                # network failure rather than crashing the whole run.
                last_exc = exc
                self._sleep(BACKOFF_BASE_SECONDS * attempt)
                continue

            if resp.status_code == 200:
                self.live_request_count += 1
                # BR / theshowratings.com don't always send a charset param
                # on Content-Type, so `requests` falls back to RFC-2616's
                # default of ISO-8859-1 for resp.text even though the body
                # is actually UTF-8 -- decode explicitly to avoid mojibake
                # on accented player names (Muñoz, Ramírez, Rodón, ...).
                resp.encoding = "utf-8"
                return resp.text
            if resp.status_code in (403, 429, 503):
                last_exc = FetchError(f"{resp.status_code} for {url}")
                self._sleep(BACKOFF_BASE_SECONDS * attempt)
                continue
            raise FetchError(f"Unexpected status {resp.status_code} for {url}")

        raise FetchError(
            f"Failed to fetch {url} after {self.max_retries} attempts: {last_exc}"
        )
