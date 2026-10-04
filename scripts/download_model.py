#!/usr/bin/env python3
"""Download the public, revision-pinned Q2_0 checkpoint and verify its checksum."""
import argparse
import hashlib
import json
from pathlib import Path
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    checksum = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(8 * 1024 * 1024):
            checksum.update(chunk)
    return checksum.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    args = parser.parse_args()
    meta = json.loads((ROOT / "model.json").read_text())
    directory = args.directory.expanduser().resolve()
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / meta["file"]
    if target.exists():
        if target.stat().st_size != meta["size"] or digest(target) != meta["sha256"]:
            raise RuntimeError("Existing model has a different size or checksum; it was preserved")
        print(target)
        return
    partial = target.with_suffix(".part")
    if partial.exists():
        raise RuntimeError(f"Partial download already exists at {partial}; preserve or remove it before retrying")
    url = f"https://huggingface.co/{meta['repository']}/resolve/{meta['revision']}/{meta['file']}"
    done = 0
    checksum = hashlib.sha256()
    start = tick = time.monotonic()
    with urllib.request.urlopen(url, timeout=45) as response, partial.open("xb") as output:
        while chunk := response.read(8 * 1024 * 1024):
            output.write(chunk)
            checksum.update(chunk)
            done += len(chunk)
            if time.monotonic() - tick >= 20:
                print(f"{done / 1e9:.2f}/{meta['size'] / 1e9:.2f} GB", flush=True)
                tick = time.monotonic()
    if done != meta["size"] or checksum.hexdigest() != meta["sha256"]:
        raise RuntimeError("Download size/checksum mismatch; partial file was retained")
    partial.rename(target)
    print(f"Verified {target} in {time.monotonic() - start:.1f}s")


if __name__ == "__main__":
    main()
