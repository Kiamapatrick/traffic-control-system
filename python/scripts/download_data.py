#!/usr/bin/env python
"""Download NYC Taxi data for ML training."""

import sys
from pathlib import Path
import urllib.request
import gzip
import shutil

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from traffic_control.utils.config import settings


def download_nyc_taxi(year: int = 2023, month: int = 1, output_dir: Path = None):
    """Download NYC Yellow Taxi data for a given month."""
    if output_dir is None:
        output_dir = Path(settings.sumo_home).parent / "data" / "raw"

    output_dir.mkdir(parents=True, exist_ok=True)

    url = f"https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_{year}-{month:02d}.parquet"
    output_file = output_dir / f"yellow_tripdata_{year}-{month:02d}.parquet"

    if output_file.exists():
        print(f"File already exists: {output_file}")
        return output_file

    print(f"Downloading from {url}...")
    print(f"Saving to {output_file}...")

    try:
        urllib.request.urlretrieve(url, output_file)
        print(f"Downloaded {output_file.stat().st_size / 1e6:.1f} MB")
        return output_file
    except Exception as e:
        print(f"Download failed: {e}")
        if output_file.exists():
            output_file.unlink()
        raise


def download_sumo():
    """Instructions for SUMO installation."""
    print("SUMO Installation:")
    print("  Ubuntu/Debian: sudo apt-get install sumo sumo-tools sumo-doc")
    print("  macOS: brew install sumo")
    print("  Windows: Download from https://sumo.dlr.de/docs/Downloads.php")
    print("")
    print("Set SUMO_HOME environment variable:")
    print("  export SUMO_HOME=/usr/share/sumo")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Download data for traffic control system")
    parser.add_argument("--nyc-year", type=int, default=2023, help="Year for NYC taxi data")
    parser.add_argument("--nyc-month", type=int, default=1, help="Month for NYC taxi data")
    parser.add_argument("--sumo", action="store_true", help="Show SUMO installation instructions")

    args = parser.parse_args()

    if args.sumo:
        download_sumo()
    else:
        download_nyc_taxi(args.nyc_year, args.nyc_month)