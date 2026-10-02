#!/usr/bin/env python3
"""WSTU Dataset - Phase 6 SCAFFOLD: normalize to the WSTU schema.

Planned behavior (not yet implemented):
  1. Read data/raw/<dataset_id>/ + per-source mapping configs under scripts/normalize/maps/.
  2. Emit one normalized JSONL per source with fields:
     question, context, choices (ONLY if the source truly has choices),
     answer, reasoning (only if source-provided), source_dataset, source_id,
     license, difficulty, language, domain, task, data_origin, translation metadata.
  3. Preserve provenance on every row; reject rows missing question+answer.
  4. Format-specific rules come from metadata/dataset_registry.json ("format").

Scaffold only — implementation follows the download phase.
"""
from __future__ import annotations


def main() -> int:
    print("normalize_wstu: scaffold only — see module docstring for the planned contract.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())