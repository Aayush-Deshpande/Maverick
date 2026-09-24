#!/usr/bin/env python3
"""Download every openly accessible dataset in this catalogue -- no login required.

Built for a slow, per-connection-throttled link: each file is split into byte-range
segments fetched over many parallel connections, in priority order (tier A first).
Resumable and idempotent -- re-running skips finished files and finished segments.
Every completed file is recorded in MANIFEST.json (source URL, bytes, SHA-256, licence).

    python Datasets/download_all.py                 # tiers A, B, C in order
    python Datasets/download_all.py --tiers A       # only the high-value small sets
    python Datasets/download_all.py --only cmapss,cwru
    python Datasets/download_all.py --list

Tier A  small, directly relevant (engine faults, C-MAPSS, CWRU core, CAN IDS, battery, UAV faults)
Tier B  larger proxies (IMS, FEMTO, Paderborn, MIMII, remaining CWRU/ALFA, randomized battery)
Tier C  N-CMAPSS (15.8 GB)

Licences differ and some are non-commercial (see --list). Verify terms at the source
before redistributing anything.
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime as dt
import hashlib
import json
import re
import shutil
import subprocess
import sys
import threading
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "MANIFEST.json"
LOG = ROOT / "download_log.txt"
UNRAR = Path(r"C:\Program Files\WinRAR\UnRAR.exe")
SEGMENT = 2 * 1024 * 1024
_lock = threading.Lock()
# Hosts that block parallel range requests ("unusual traffic" 403): one plain connection each.
POLITE_HOSTS = {"zenodo.org": threading.Semaphore(1)}


def _polite(url: str) -> threading.Semaphore | None:
    host = re.sub(r"^https?://([^/]+).*$", r"\1", url)
    return POLITE_HOSTS.get(host)

S3 = "https://phm-datasets.s3.amazonaws.com/NASA/"
ZEN = "https://zenodo.org/api/records/"
US_GOV = "US Government work (public domain in the US)"


@dataclass(frozen=True)
class Item:
    group: str
    tier: str
    dest: str
    url: str
    licence: str
    size: int | None = None
    extract: bool = True


def log(msg: str) -> None:
    line = f"[{dt.datetime.now():%H:%M:%S}] {msg}"
    with _lock:
        print(line, flush=True)
        with LOG.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")


def _get(url: str, tries: int = 3) -> str:
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=90) as r:
                return r.read().decode("utf-8", "replace")
        except Exception:  # noqa: BLE001
            if attempt == tries - 1:
                raise
    return ""


# ---------------------------------------------------------------- catalogue --

def static_items() -> list[Item]:
    alfa = [("processed.zip", 24095870, 272_000_000, "A"), ("README.txt", 24098639, None, "A"),
            ("telemetry.zip", 24098393, 210_700_000, "B"), ("dataflash.zip", 24096047, 541_300_000, "B"),
            ("raw.zip", 24095969, 721_400_000, "B")]
    nc = "CC-BY-NC-SA-4.0 (non-commercial)"
    return [
        Item("cmapss", "A", "Engine_PHM/cmapss/CMAPSS.zip",
             S3 + "6.+Turbofan+Engine+Degradation+Simulation+Data+Set.zip", US_GOV),
        Item("marine", "A", "Piston_Engine/marine_engine_fault/Marine_Engine_Fault_Data_v1.zip",
             ZEN + "19857425/files/Marine_Engine_Fault_Data_v1.zip/content", "CC-BY-4.0"),
        Item("battery", "A", "Battery_Electrical/nasa_battery/Battery_Data_Set.zip",
             S3 + "5.+Battery+Data+Set.zip", US_GOV),
        Item("road", "A", "CAN_ECU/road/road.zip", ZEN + "10462796/files/road.zip/content", "CC-BY-4.0"),
        *[Item("alfa", t, f"UAV_Telemetry/alfa/{n}", f"https://ndownloader.figshare.com/files/{fid}",
               "CC-BY-4.0") for n, fid, _, t in alfa],
        Item("ims", "B", "Bearing/ims/IMS_Bearings.zip", S3 + "4.+Bearings.zip", US_GOV),
        Item("femto", "B", "Bearing/femto/FEMTO_Bearing.zip", S3 + "10.+FEMTO+Bearing.zip",
             "PHM 2012 challenge data -- cite Nectoux et al. 2012"),
        Item("battery", "B", "Battery_Electrical/nasa_randomized_battery/Randomized_Battery_Usage.zip",
             S3 + "11.+Randomized+Battery+Usage+Data+Set.zip", US_GOV),
        Item("mimii", "B", "Vibration/mimii_dg/bearing.zip", ZEN + "6529888/files/bearing.zip/content", "CC-BY-4.0"),
        Item("mimii", "B", "Vibration/mimii_dg/gearbox.zip", ZEN + "6529888/files/gearbox.zip/content", "CC-BY-4.0"),
        Item("mimii", "B", "Vibration/mimii_due/dev_data_gearbox.zip",
             ZEN + "4740355/files/dev_data_gearbox.zip/content", nc),
        Item("mimii", "B", "Vibration/mimii_due/eval_data_gearbox_train.zip",
             ZEN + "4740355/files/eval_data_gearbox_train.zip/content", nc),
        Item("ncmapss", "C", "Engine_PHM/ncmapss/N-CMAPSS.zip",
             S3 + "17.+Turbofan+Engine+Degradation+Simulation+Data+Set+2.zip", US_GOV),
    ]


PADERBORN = ("K001 K002 K003 K004 K005 K006 KA01 KA03 KA05 KA06 KA07 KA08 KA09 KI01 KI03 KI05 KI07 KI08 "
             "KA04 KA15 KA16 KA22 KA30 KI04 KI14 KI16 KI17 KI18 KI21 KB23 KB24 KB27").split()


def paderborn_items() -> list[Item]:
    return [Item("paderborn", "B", f"Bearing/paderborn/{b}.rar",
                 f"https://groups.uni-paderborn.de/kat/BearingDataCenter/{b}.rar",
                 "Paderborn KAt-DataCenter -- cite Lessmeier et al. 2016") for b in PADERBORN]


CWRU_PAGES = {"normal-baseline-data": "A", "12k-drive-end-bearing-fault-data": "A",
              "48k-drive-end-bearing-fault-data": "B", "12k-fan-end-bearing-fault-data": "B"}


def cwru_items() -> list[Item]:
    items = []
    for page, tier in CWRU_PAGES.items():
        try:
            html = _get(f"https://engineering.case.edu/bearingdatacenter/{page}")
        except Exception as exc:  # noqa: BLE001
            log(f"cwru: could not list {page} ({exc}) -- re-run later to pick it up")
            continue
        for url in sorted(set(re.findall(r'href="(https://engineering\.case\.edu/[^"]+\.mat)"', html))):
            items.append(Item("cwru", tier, f"Bearing/cwru/{page}/{url.rsplit('/', 1)[1]}", url,
                              "CWRU Bearing Data Center -- cite the site", extract=False))
    return items


def mendeley_items(group: str, dataset: str, version: int, folder: str) -> list[Item]:
    try:
        files = json.loads(_get(f"https://data.mendeley.com/public-api/datasets/{dataset}/files"
                                f"?folder_id=root&version={version}"))
    except Exception as exc:  # noqa: BLE001
        log(f"{group}: could not list Mendeley {dataset}: {exc}")
        return []
    return [Item(group, "A", f"{folder}/{f['filename']}", f["content_details"]["download_url"], "CC-BY-4.0",
                 f["content_details"]["size"]) for f in files]


GIT_REPOS = {
    "skab": ("https://github.com/waico/SKAB", "Anomaly_Benchmarks/skab", "GPL-3.0 -- check repo"),
    "syncan": ("https://github.com/etas/SynCAN", "CAN_ECU/syncan", "check repo"),
}


def catalogue() -> list[Item]:
    return (static_items() + cwru_items() + paderborn_items()
            + mendeley_items("default3500", "k22zxz29kr", 1, "Piston_Engine/3500_default")
            + mendeley_items("journal", "3fcrrdjjvk", 4, "Piston_Engine/engine_journal_bearings"))


# ------------------------------------------------------------------ helpers --

def probe(url: str) -> tuple[int | None, bool]:
    """(content length, supports byte ranges) after redirects."""
    out = subprocess.run(["curl", "-sIL", "-r", "0-0", "-A", "Mozilla/5.0", "--max-time", "60", url],
                         capture_output=True, text=True).stdout
    blocks = [b for b in re.split(r"\r?\n\r?\n", out) if b.strip()]
    last = blocks[-1] if blocks else ""
    ranged = " 206" in last.splitlines()[0] if last else False
    m = re.search(r"(?im)^content-range:\s*bytes\s+\d+-\d+/(\d+)", last)
    if m:
        return int(m.group(1)), ranged
    m = re.search(r"(?im)^content-length:\s*(\d+)", last)
    return (int(m.group(1)) if m else None), ranged


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def _marker(path: Path) -> Path:
    return path.with_name(path.name + ".ok")


def _manifest_update(entry: dict) -> None:
    with _lock:
        data = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
        data[entry["path"]] = entry
        MANIFEST.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _curl(url: str, out: Path, rng: str | None = None) -> int:
    cmd = ["curl", "-L", "-sS", "-f", "--retry", "10", "--retry-delay", "5", "--retry-all-errors",
           "--connect-timeout", "30", "-A", "Mozilla/5.0", "-o", str(out)]
    if rng:
        cmd += ["-r", rng]
    else:
        cmd += ["-C", "-"]
    return subprocess.run(cmd + [url]).returncode


def _extract(path: Path) -> None:
    out = path.with_suffix("")
    try:
        if path.suffix.lower() == ".zip":
            with zipfile.ZipFile(path) as zf:
                zf.extractall(out)
        elif path.suffix.lower() == ".rar" and UNRAR.exists():
            out.mkdir(exist_ok=True)
            subprocess.run([str(UNRAR), "x", "-o+", "-inul", str(path), str(out) + "\\"], check=True)
        else:
            return
        log(f"XTR  {path.resolve().relative_to(ROOT)}")
    except Exception as exc:  # noqa: BLE001
        log(f"XFAIL {path.name}: {exc}")


def extract_nested(base: Path = ROOT, depth: int = 3) -> None:
    """NASA's S3 archives wrap inner zips/rars inside the outer zip. Unpack them in place,
    next to themselves, up to `depth` levels. Skips archives this script downloaded directly
    (those are handled by _extract) and anything already unpacked."""
    for _ in range(depth):
        found = False
        for arc in list(base.rglob("*.zip")) + list(base.rglob("*.rar")):
            if _marker(arc).exists() or arc.with_suffix("").exists() or ".part" in arc.name:
                continue
            found = True
            _extract(arc)
        if not found:
            return


def _finish(it: Item, path: Path) -> None:
    size = path.stat().st_size
    digest = _sha256(path)
    if it.extract:
        _extract(path)
    _manifest_update({"path": it.dest, "url": it.url, "licence": it.licence, "bytes": size, "sha256": digest,
                      "downloaded": dt.datetime.now().isoformat(timespec="seconds")})
    _marker(path).write_text(digest)
    log(f"OK   {it.dest}  {size / 1e6:,.1f} MB")


# ------------------------------------------------------------ segmented run --

class Job:
    def __init__(self, it: Item, size: int | None, ranged: bool):
        self.it, self.size, self.path = it, size, ROOT / it.dest
        self.segmented = bool(ranged and size and size > SEGMENT) and _polite(it.url) is None
        self.nseg = -(-size // SEGMENT) if self.segmented else 1
        self.remaining = self.nseg
        self.failed = False

    def part(self, i: int) -> Path:
        return self.path.with_name(f"{self.path.name}.part{i:05d}")

    def tasks(self):
        for i in range(self.nseg):
            yield self, i


def run_segment(job: Job, i: int) -> None:
    job.path.parent.mkdir(parents=True, exist_ok=True)
    if job.segmented:
        start = i * SEGMENT
        end = min(job.size, start + SEGMENT) - 1
        part, want = job.part(i), end - start + 1
        for _ in range(4):
            if part.exists() and part.stat().st_size == want:
                break
            _curl(job.it.url, part, f"{start}-{end}")
        ok = part.exists() and part.stat().st_size == want
    else:
        gate = _polite(job.it.url)
        if gate:
            gate.acquire()
        try:
            rc = _curl(job.it.url, job.path)
        finally:
            if gate:
                gate.release()
        ok = rc in (0, 33) and job.path.exists() and (not job.size or job.path.stat().st_size == job.size)
    with _lock:
        if not ok:
            job.failed = True
        job.remaining -= 1
        last = job.remaining == 0
    if not last:
        return
    if job.failed:
        log(f"FAIL {job.it.dest} -- re-run to resume")
        return
    if job.segmented:
        with job.path.open("wb") as out:
            for k in range(job.nseg):
                with job.part(k).open("rb") as src:
                    shutil.copyfileobj(src, out, 1 << 22)
        for k in range(job.nseg):
            job.part(k).unlink()
        if job.path.stat().st_size != job.size:
            log(f"FAIL {job.it.dest} size mismatch after join")
            return
    _finish(job.it, job.path)


def clone(key: str) -> None:
    url, dest, licence = GIT_REPOS[key]
    path = ROOT / dest
    if (path / ".git").exists():
        return
    log(f"GIT  {url}")
    if subprocess.run(["git", "clone", "--depth", "1", "-q", url, str(path)]).returncode == 0:
        _manifest_update({"path": dest, "url": url, "licence": licence, "bytes": None, "sha256": None,
                          "downloaded": dt.datetime.now().isoformat(timespec="seconds")})
        log(f"OK   {dest}")
    else:
        log(f"FAIL {dest}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", help="comma-separated group keys")
    ap.add_argument("--tiers", default="ABC")
    ap.add_argument("--connections", type=int, default=96)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--extract-nested", action="store_true", help="unpack archives nested inside downloads")
    args = ap.parse_args()

    if args.extract_nested:
        extract_nested()
        return 0

    items = [i for i in catalogue() if i.tier in args.tiers]
    if args.only:
        items = [i for i in items if i.group in set(args.only.split(","))]
    items = [i for i in items if not _marker(ROOT / i.dest).exists()]
    if args.list:
        for i in items:
            print(f"{i.tier} {i.group:12s} {i.dest:72s} {i.licence}")
        print(f"{len(items)} files pending")
        return 0

    log(f"PLAN {len(items)} pending files, tiers {args.tiers}")
    with cf.ThreadPoolExecutor(max_workers=16) as pool:
        probes = list(pool.map(lambda it: probe(it.url), items))
    jobs = [Job(it, size or it.size, ranged) for it, (size, ranged) in zip(items, probes)]
    total = sum(j.size or 0 for j in jobs)
    free = shutil.disk_usage(ROOT).free
    log(f"START {len(jobs)} files, {total / 1e9:,.2f} GB, {free / 1e9:,.0f} GB free, "
        f"{args.connections} connections")
    if total * 2.2 > free:
        log("ABORT: not enough free space for download + extraction")
        return 1

    jobs.sort(key=lambda j: (j.it.tier, j.size or 0))
    with cf.ThreadPoolExecutor(max_workers=args.connections) as pool:
        repo_futs = [pool.submit(clone, k) for k in GIT_REPOS if not args.only or k in args.only]
        futs = [pool.submit(run_segment, job, i) for job in jobs for _, i in job.tasks()]
        for f in cf.as_completed(futs + repo_futs):
            f.result()
    log("DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
