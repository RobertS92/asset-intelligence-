"""Polite HTTP client: robots check, rate limit, retries, raw save + manifest."""

from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from exodus.common.storage import manifest_path, raw_dir

DEFAULT_DELAY_S = 3.0
_last_request: dict[str, float] = {}


class RobotsBlockedError(RuntimeError):
    """Raised when robots.txt disallows the requested path."""


class PoliteClient:
    """Shared fetcher for all source modules. Never call httpx/requests directly."""

    def __init__(
        self,
        contact_email: str | None = None,
        delay_s: float = DEFAULT_DELAY_S,
        timeout_s: float = 60.0,
    ) -> None:
        email = contact_email or os.environ.get("EXODUS_CONTACT_EMAIL", "exodus@localhost")
        self.contact_email = email
        self.delay_s = delay_s
        self.timeout_s = timeout_s
        self.user_agent = f"ExodusAssetSignals/0.1 (+research; contact={email}; polite-bot)"
        self._robots: dict[str, RobotFileParser] = {}
        self._client = httpx.Client(
            headers={"User-Agent": self.user_agent},
            timeout=timeout_s,
            follow_redirects=True,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> PoliteClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _host(self, url: str) -> str:
        return urlparse(url).netloc

    def _wait(self, host: str) -> None:
        now = time.monotonic()
        last = _last_request.get(host, 0.0)
        sleep_for = self.delay_s - (now - last)
        if sleep_for > 0:
            time.sleep(sleep_for)
        _last_request[host] = time.monotonic()

    def _robots_parser(self, url: str) -> RobotFileParser:
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        if base not in self._robots:
            rp = RobotFileParser()
            robots_url = f"{base}/robots.txt"
            try:
                self._wait(parsed.netloc)
                resp = self._client.get(robots_url)
                if resp.status_code == 200:
                    rp.parse(resp.text.splitlines())
                else:
                    rp.parse([])
            except httpx.HTTPError:
                rp.parse([])
            self._robots[base] = rp
        return self._robots[base]

    def check_robots(self, url: str) -> None:
        rp = self._robots_parser(url)
        if not rp.can_fetch(self.user_agent, url):
            # Also try wildcard user-agent semantics
            if not rp.can_fetch("*", url):
                raise RobotsBlockedError(f"robots.txt disallows {url}")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=20))
    def _get(self, url: str) -> httpx.Response:
        host = self._host(url)
        self._wait(host)
        resp = self._client.get(url)
        resp.raise_for_status()
        return resp

    def fetch_bytes(self, url: str, *, check_robots: bool = True) -> tuple[bytes, int]:
        if check_robots:
            self.check_robots(url)
        resp = self._get(url)
        return resp.content, resp.status_code

    def fetch_text(self, url: str, *, check_robots: bool = True) -> tuple[str, int]:
        content, status = self.fetch_bytes(url, check_robots=check_robots)
        return content.decode("utf-8", errors="replace"), status

    def save_raw(
        self,
        source_key: str,
        run_date: str,
        url: str,
        content: bytes,
        http_status: int,
        filename: str | None = None,
    ) -> Path:
        """Save raw bytes idempotently and append manifest.jsonl."""
        dest_dir = raw_dir(source_key, run_date)
        sha = hashlib.sha256(content).hexdigest()
        name = filename or f"{sha[:16]}.bin"
        dest = dest_dir / name

        # Idempotent: same content hash → skip rewrite
        if dest.exists():
            existing = dest.read_bytes()
            if hashlib.sha256(existing).hexdigest() == sha:
                self._append_manifest(
                    source_key,
                    {
                        "url": url,
                        "sha256": sha,
                        "fetched_at": datetime.now(UTC).isoformat(),
                        "http_status": http_status,
                        "path": str(dest.relative_to(dest_dir.parent.parent.parent)),
                        "skipped": True,
                    },
                )
                return dest

        dest.write_bytes(content)
        self._append_manifest(
            source_key,
            {
                "url": url,
                "sha256": sha,
                "fetched_at": datetime.now(UTC).isoformat(),
                "http_status": http_status,
                "path": str(dest.relative_to(dest_dir.parent.parent.parent)),
                "skipped": False,
            },
        )
        return dest

    def fetch_and_save(
        self,
        source_key: str,
        run_date: str,
        url: str,
        filename: str | None = None,
        *,
        check_robots: bool = True,
    ) -> Path:
        content, status = self.fetch_bytes(url, check_robots=check_robots)
        return self.save_raw(source_key, run_date, url, content, status, filename)

    def _append_manifest(self, source_key: str, row: dict[str, object]) -> None:
        mp = manifest_path(source_key)
        with mp.open("a") as f:
            f.write(json.dumps(row) + "\n")
