#!/usr/bin/env python3
"""Download helper for the openly-accessible datasets in this catalogue.

Datasets needing registration or manual acceptance of terms are listed but not
fetched -- run with --list to see acquisition instructions for those.

Verify licence terms at the source before using or redistributing anything.
"""

from __future__ import annotations

import argparse
import sys
import urllib.request
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).parent


@dataclass(frozen=True)
class Dataset:
    key: str
    name: str
    folder: str
    licence: str
    url: str | None = None
    landing_page: str | None = None
    manual_steps: list[str] = field(default_factory=list)

    @property
    def target_dir(self) -> Path:
        return ROOT / self.folder

    @property
    def automatic(self) -> bool:
        return self.url is not None


DATASETS: dict[str, Dataset] = {
    d.key: d
    for d in [
        Dataset(
            key="cmapss",
            name="NASA C-MAPSS Turbofan Engine Degradation",
            folder="Engine_PHM",
            licence="US Government work - verify at the NASA page",
            url="https://phm-datasets.s3.amazonaws.com/NASA/"
            "6.+Turbofan+Engine+Degradation+Simulation+Data+Set.zip",
            landing_page="https://www.nasa.gov/intelligent-systems-division/"
            "discovery-and-systems-health/pcoe/pcoe-data-set-repository/",
        ),
        Dataset(
            key="ims",
            name="IMS / NASA Bearing Dataset",
            folder="Bearing",
            licence="https://www.usa.gov/government-works",
            url="https://phm-datasets.s3.amazonaws.com/NASA/4.+Bearings.zip",
            landing_page="https://catalog.data.gov/dataset/ims-bearings",
        ),
        Dataset(
            key="cwru",
            name="CWRU Bearing Data Center",
            folder="Bearing",
            licence="Check the site before redistribution",
            landing_page="https://engineering.case.edu/bearingdatacenter",
            manual_steps=[
                "Open the landing page and browse to the download section.",
                "Select the drive-end / fan-end records at 12 kHz (and 48 kHz if wanted).",
                "Download the .mat files into Datasets/Bearing/cwru/.",
            ],
        ),
        Dataset(
            key="paderborn",
            name="Paderborn (KAt-DataCenter) Bearing Dataset",
            folder="Bearing",
            licence="Check the site before redistribution",
            landing_page="https://mb.uni-paderborn.de/kat/forschung/"
            "kat-datacenter/bearing-datacenter",
            manual_steps=[
                "Open the landing page and accept the data-use terms.",
                "Download the artificial and real-damage archives.",
                "Extract into Datasets/Bearing/paderborn/.",
            ],
        ),
        Dataset(
            key="xjtu",
            name="XJTU-SY Bearing Run-to-Failure",
            folder="Bearing",
            licence="Check the repository",
            landing_page="https://biaowang.tech/xjtu-sy-bearing-datasets/",
            manual_steps=[
                "Follow the download links on the landing page.",
                "Extract into Datasets/Bearing/xjtu_sy/.",
            ],
        ),
        Dataset(
            key="alfa",
            name="ALFA UAV Fault and Anomaly Detection",
            folder="UAV_Telemetry",
            licence="Check the repository",
            landing_page="https://theairlab.org/alfa-dataset",
            manual_steps=[
                "Download the processed and/or raw archives from the project page.",
                "Extract into Datasets/UAV_Telemetry/alfa/.",
                "Cite: Keipour, Mousaei & Scherer (2021), IJRR 40(2-3).",
            ],
        ),
        Dataset(
            key="mimii",
            name="MIMII Industrial Machine Sound",
            folder="Vibration",
            licence="CC BY-SA 4.0 (ShareAlike obligations apply)",
            landing_page="https://zenodo.org/records/3384388",
            manual_steps=[
                "Download the per-machine archives from Zenodo.",
                "Extract into Datasets/Vibration/mimii/.",
                "Note: CC BY-SA requires attribution AND share-alike on derivatives.",
            ],
        ),
        Dataset(
            key="skab",
            name="SKAB - Skoltech Anomaly Benchmark",
            folder="Vibration",
            licence="Check the repository",
            landing_page="https://github.com/waico/SKAB",
            manual_steps=[
                "git clone https://github.com/waico/SKAB "
                "Datasets/Vibration/skab",
            ],
        ),
    ]
}


def _progress(done: int, block: int, total: int) -> None:
    if total <= 0:
        return
    pct = min(100.0, done * block * 100.0 / total)
    mb = done * block / 1_048_576
    print(f"\r  {pct:5.1f}%  ({mb:.1f} MB)", end="", flush=True)


def fetch(ds: Dataset, extract: bool) -> int:
    if not ds.automatic:
        print(f"'{ds.key}' requires manual download. See --list for steps.")
        return 1

    ds.target_dir.mkdir(parents=True, exist_ok=True)
    filename = ds.url.rsplit("/", 1)[-1].replace("+", "_")
    dest = ds.target_dir / filename

    if dest.exists():
        print(f"Already present: {dest}")
    else:
        print(f"{ds.name}\n  licence: {ds.licence}\n  -> {dest}")
        try:
            urllib.request.urlretrieve(ds.url, dest, _progress)
            print()
        except Exception as exc:
            print(f"\nDownload failed: {exc}")
            print(f"Try manually: {ds.url}")
            return 1

    if extract and dest.suffix == ".zip":
        out = ds.target_dir / dest.stem
        print(f"  extracting -> {out}")
        try:
            with zipfile.ZipFile(dest) as zf:
                zf.extractall(out)
        except Exception as exc:
            print(f"  extraction failed: {exc}")
            return 1

    print("Done.")
    return 0


def show_list() -> None:
    print("\nDatasets in this catalogue\n" + "=" * 70)
    for ds in DATASETS.values():
        mode = "automatic" if ds.automatic else "MANUAL"
        print(f"\n[{ds.key}]  {ds.name}")
        print(f"  folder  : Datasets/{ds.folder}/")
        print(f"  licence : {ds.licence}")
        print(f"  fetch   : {mode}")
        if ds.landing_page:
            print(f"  source  : {ds.landing_page}")
        for i, step in enumerate(ds.manual_steps, 1):
            print(f"     {i}. {step}")
    print(
        "\n"
        + "=" * 70
        + "\nVerify licence terms at the source before use or redistribution.\n"
        "Cite every dataset used in any publication or presentation.\n"
    )


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--list", action="store_true", help="list datasets and instructions")
    p.add_argument("--dataset", help="key of the dataset to download")
    p.add_argument("--all", action="store_true", help="download all automatic datasets")
    p.add_argument("--no-extract", action="store_true", help="skip zip extraction")
    args = p.parse_args()

    if args.list or not (args.dataset or args.all):
        show_list()
        return 0

    extract = not args.no_extract

    if args.all:
        return max(
            (fetch(d, extract) for d in DATASETS.values() if d.automatic), default=0
        )

    ds = DATASETS.get(args.dataset)
    if ds is None:
        print(f"Unknown dataset '{args.dataset}'. Known: {', '.join(DATASETS)}")
        return 1
    return fetch(ds, extract)


if __name__ == "__main__":
    sys.exit(main())
