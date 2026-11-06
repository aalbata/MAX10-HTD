"""Download and unpack the public benchmark archives that MAX10-HTD is built from.

The third-party designs are not redistributed with the dataset.  This script
downloads every archive from its original location, checks its size and
SHA-256 digest against dataset/metadata/source_archives.csv, and unpacks it
under <build>/raw/<source>/x/<archive stem>/.

Usage:
  python -m scripts.sources.fetch [--sources trusthub,trit,ghost,hayashi] [--record]

With --record, archives that are not yet listed in the manifest are added to
it with their size and digest; this is used once, when a source is added.
Without it, a missing or mismatching archive is an error.
"""
from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path

from ..common import config
from ..common.util import sha256_file

MANIFEST = config.METADATA_DIR / "source_archives.csv"
FIELDS = ["source", "archive", "url", "bytes", "sha256", "retrieved", "license", "reference"]
AGENT = {"User-Agent": "MAX10-HTD-fetch/1.0"}

TRUSTHUB_CATALOG = "https://trust-hub.org/assets/json/benchmarks-trojan-chip.json"
GHOST_REPO = "NMSU-PEARL/GHOST_benchmarks"
GHOST_COMMIT = "078cec60f163552ea85881ee3f37d5581ccf5c61"   # main on 2026-10-14
HAYASHI_RECORD = "11035341"

LICENSES = {
    "trusthub": "no license stated; copyright Trust-Hub; not redistributed",
    "trit": "no license stated; copyright Trust-Hub; not redistributed",
    "ghost": "BSD-3-Clause (original work); upstream hosts Apache-2.0, MIT or BSD-3-Clause",
    "hayashi": "CC-BY-4.0",
}
REFERENCES = {
    "trusthub": "salmani2013design; shakya2017benchmarking",
    "trit": "cruz2018automated",
    "ghost": "faruque2025unleashing",
    "hayashi": "hayashi2024hardware; hayashi2024zenodo",
}


def _get(url: str, dest: Path, tries: int = 4) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=AGENT), timeout=120) as r, \
                    open(tmp, "wb") as fh:
                shutil.copyfileobj(r, fh, 1 << 20)
            tmp.replace(dest)
            return
        except Exception:
            if attempt == tries - 1:
                raise
            time.sleep(5 * (attempt + 1))


def _json(url: str):
    with urllib.request.urlopen(urllib.request.Request(url, headers=AGENT), timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))


def candidates(source: str, raw: Path) -> list[dict]:
    """Archives offered by a source: name and download address."""
    if source in ("trusthub", "trit"):
        cat = raw / "trusthub" / "archives" / "benchmarks-trojan-chip.json"
        if not cat.exists():
            _get(TRUSTHUB_CATALOG, cat)
        entries = json.loads(cat.read_text(encoding="utf-8"))
        out = [{"archive": "benchmarks-trojan-chip.json", "url": TRUSTHUB_CATALOG}] if source == "trusthub" else []
        for e in entries:
            is_trit = e["name"].startswith("TRIT-")
            if is_trit != (source == "trit") or len(e["links"]) != 1:
                continue
            link = e["links"][0]
            out.append({"archive": link.rsplit("/", 1)[-1], "url": "https://trust-hub.org" + link})
        return out
    if source == "ghost":
        return [{"archive": f"GHOST_benchmarks-{GHOST_COMMIT[:12]}.zip",
                 "url": f"https://codeload.github.com/{GHOST_REPO}/zip/{GHOST_COMMIT}"}]
    if source == "hayashi":
        rec = _json(f"https://zenodo.org/api/records/{HAYASHI_RECORD}")
        return [{"archive": f["key"], "url": f["links"]["self"]} for f in rec["files"]]
    raise KeyError(source)


def read_manifest() -> dict:
    if not MANIFEST.exists():
        return {}
    with open(MANIFEST, encoding="utf-8", newline="") as fh:
        return {(r["source"], r["archive"]): r for r in csv.DictReader(fh)}


def write_manifest(rows: dict) -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, lineterminator="\n")
        w.writeheader()
        for key in sorted(rows):
            w.writerow(rows[key])


def safe_members(archive: Path) -> bool:
    """True when no member of the archive has an absolute path or a parent reference."""
    out = subprocess.run([config.archiver(), "l", "-slt", "-ba", str(archive)], capture_output=True,
                         text=True, errors="replace")
    if out.returncode != 0:
        return False
    for line in out.stdout.splitlines():
        if line.startswith("Path = "):
            p = line[7:].replace("\\", "/")
            if p.startswith("/") or ":" in p or any(part == ".." for part in p.split("/")):
                return False
    return True


def unpack(archive: Path, dest: Path) -> None:
    """Extract into dest; a marker file records a completed extraction."""
    done = dest / ".unpacked"
    if done.exists():
        return
    if not safe_members(archive):
        raise RuntimeError(f"unsafe or unreadable archive: {archive}")
    shutil.rmtree(dest, ignore_errors=True)
    dest.mkdir(parents=True)
    rc = subprocess.run([config.archiver(), "x", "-y", f"-o{dest}", str(archive)], capture_output=True,
                        text=True, errors="replace").returncode
    if rc != 0:
        raise RuntimeError(f"extraction failed: {archive}")
    done.write_text(sha256_file(archive) + "\n", encoding="utf-8")


def fetch(source: str, record: bool, manifest: dict) -> None:
    raw = config.BUILD / "raw"
    for c in candidates(source, raw):
        dest = raw / source / "archives" / c["archive"]
        key = (source, c["archive"])
        if not dest.exists():
            _get(c["url"], dest)
        size, digest = dest.stat().st_size, sha256_file(dest)
        if key in manifest:
            m = manifest[key]
            if int(m["bytes"]) != size or m["sha256"] != digest:
                raise RuntimeError(f"{c['archive']}: size or digest differs from the manifest")
        elif record:
            manifest[key] = {"source": source, "archive": c["archive"], "url": c["url"], "bytes": size,
                             "sha256": digest, "retrieved": time.strftime("%Y-%m-%d"),
                             "license": LICENSES[source], "reference": REFERENCES[source]}
        else:
            raise RuntimeError(f"{c['archive']} is not in the manifest; rerun with --record")
        if dest.suffix.lower() in (".zip", ".rar", ".7z", ".gz", ".tgz"):
            unpack(dest, raw / source / "x" / dest.name.rsplit(".", 1)[0])
        print(f"{source}: {c['archive']} {size} bytes", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sources", default="trusthub,trit,ghost,hayashi")
    ap.add_argument("--record", action="store_true")
    args = ap.parse_args()
    manifest = read_manifest()
    try:
        for s in args.sources.split(","):
            fetch(s, args.record, manifest)
    finally:
        if args.record:
            write_manifest(manifest)


if __name__ == "__main__":
    main()
