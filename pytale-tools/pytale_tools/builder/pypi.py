"""Async PyPI wheel downloader with local file caching.

Downloads wheels from the PyPI JSON API, selects pure-Python builds (py3-none-any),
verifies SHA256, and caches by wheel filename. Uses a worker pool (asyncio.Queue)
for concurrency control.
"""

import asyncio
import hashlib
from pathlib import Path

import httpx
from pytale_tools.builder.req_parser import Requirement


class WheelNotFoundError(Exception):
    pass


class WheelDownloadError(Exception):
    pass


_PYPI_BASE = "https://pypi.org/pypi"
_PURE_PYTHON_TAGS = {"py3-none-any", "py2.py3-none-any"}


def _is_pure_python(filename: str) -> bool:
    stem = filename.removesuffix(".whl")
    parts = stem.rsplit("-", 3)
    if len(parts) < 4:
        return False
    tag = f"{parts[-3]}-{parts[-2]}-{parts[-1]}"
    return tag in _PURE_PYTHON_TAGS


def _select_wheel(urls: list[dict], name: str, version: str) -> dict:
    wheels = [u for u in urls if u.get("packagetype") == "bdist_wheel"]
    if not wheels:
        raise WheelNotFoundError(
            f"No wheel available for {name}=={version} (only sdist). "
            f"A pre-built wheel is required."
        )

    for w in wheels:
        if _is_pure_python(w["filename"]):
            return w

    raise WheelNotFoundError(
        f"No pure-Python wheel found for {name}=={version}. "
        f"Only platform-specific wheels are available, which are not supported."
    )


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


async def _download_one(
    client: httpx.AsyncClient, req: Requirement, cache_dir: Path
) -> Path:
    url = f"{_PYPI_BASE}/{req.name}/{req.version}/json"
    resp = await client.get(url)

    if resp.status_code == 404:
        raise WheelNotFoundError(f"Package {req.name}=={req.version} not found on PyPI")
    resp.raise_for_status()

    data = resp.json()
    entry = _select_wheel(data["urls"], req.name, req.version)

    filename = entry["filename"]
    expected_sha = entry["digests"]["sha256"]
    cached = cache_dir / filename

    if cached.exists() and _sha256_file(cached) == expected_sha:
        print(f"  Cached: {filename}")
        return cached

    print(f"  Downloading: {filename}")
    partial = cache_dir / (filename + ".partial")

    async with client.stream("GET", entry["url"]) as stream:
        stream.raise_for_status()
        h = hashlib.sha256()
        with open(partial, "wb") as f:
            async for chunk in stream.aiter_bytes(8192):
                f.write(chunk)
                h.update(chunk)

    actual_sha = h.hexdigest()
    if actual_sha != expected_sha:
        partial.unlink(missing_ok=True)
        raise WheelDownloadError(
            f"SHA256 mismatch for {filename}: "
            f"expected {expected_sha}, got {actual_sha}"
        )

    partial.rename(cached)
    return cached


async def _worker(
    queue: asyncio.Queue[Requirement],
    client: httpx.AsyncClient,
    cache_dir: Path,
    results: dict[str, Path],
) -> None:
    while True:
        req = await queue.get()
        try:
            path = await _download_one(client, req, cache_dir)
            results[req.name] = path
        finally:
            queue.task_done()


async def download_wheels(
    requirements: list[Requirement],
    cache_dir: Path,
    *,
    max_workers: int = 10,
) -> list[Path]:
    if not requirements:
        return []

    cache_dir.mkdir(parents=True, exist_ok=True)
    results: dict[str, Path] = {}

    timeout = httpx.Timeout(connect=30.0, read=120.0, write=30.0, pool=30.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        queue: asyncio.Queue[Requirement] = asyncio.Queue()
        for req in requirements:
            queue.put_nowait(req)

        n_workers = min(max_workers, len(requirements))
        workers = [
            asyncio.create_task(_worker(queue, client, cache_dir, results))
            for _ in range(n_workers)
        ]

        await queue.join()

        for w in workers:
            w.cancel()

    return [results[req.name] for req in requirements]


def download_wheels_sync(
    requirements: list[Requirement],
    cache_dir: Path,
    *,
    max_workers: int = 10,
) -> list[Path]:
    return asyncio.run(
        download_wheels(requirements, cache_dir, max_workers=max_workers)
    )
