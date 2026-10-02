#!/usr/bin/env python3
"""WSTU Dataset - Phase 5 SCAFOLD: download.

Planned behavior (not yet implemented):
  1. Read metadata/approved_sources.json ("training" bucket only).
  2. For each source, stream-download ONLY the needed splits/configs via the
     `datasets` library, pinned to the revision sha recorded in
     metadata/verification/hf_verification.json.
  3. Store under data/raw/<dataset_id>/ ; never commit raw corpora (.gitignore).
  4. Write data/raw/<dataset_id>/MANIFEST.json = {source, revision, files, hashes}.
  5. Refuse to run for any source whose registry status != "verified".

This file exists to fix the interface for the next phase; the downloader is
intentionally not fetching data during the discovery/registry phase.
"""
from __future__ import annotations


def main() -> int:
    print("download_datasets: scaffold only — see module docstring for the planned contract.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())