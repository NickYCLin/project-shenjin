#!/usr/bin/env python3
"""Restore exact CC0 texture sources; no account or API key is required."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "art/textures/sources.json"


def download(item):
    path = ROOT / item["path"]
    if path.exists():
        data = path.read_bytes()
    else:
        request = urllib.request.Request(item["url"], headers={
            "User-Agent": "ProjectShenjin/0.2 (open-source art study)"
        })
        with urllib.request.urlopen(request, timeout=90) as response:
            data = response.read()
    if len(data) != item["size"] or hashlib.md5(data).hexdigest() != item["md5"]:
        raise ValueError(f"Source checksum mismatch: {item['path']}")
    sha256 = hashlib.sha256(data).hexdigest()
    if item.get("sha256", sha256) != sha256:
        raise ValueError(f"SHA-256 mismatch: {item['path']}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    item["sha256"] = sha256
    print(f"Verified {item['path']}")


def main():
    manifest = json.loads(MANIFEST.read_text())
    maps = [item for asset in manifest["assets"] for item in asset["maps"].values()]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(download, maps))
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
