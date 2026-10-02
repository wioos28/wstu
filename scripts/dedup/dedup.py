#!/usr/bin/env python3
"""WSTU Dataset - Phase 7 SCAFFOLD: deduplication.

Planned five levels (see docs/DEDUPLICATION.md):
  1. exact hash of (normalized question, choices, answer)
  2. normalized hash (case/whitespace/punctuation/Unicode-NFKC)
  3. near-duplicate similarity per domain threshold
  4. cross-dataset clustering (registry "related_candidates" map seeds the clusters)
  5. semantic similarity with answer-must-match
plus: translation-duplicate collapsing (same item, N languages counts once).

Scaffold only — implementation follows the normalize phase.
"""
from __future__ import annotations


def main() -> int:
    print("dedup: scaffold only — see module docstring for the planned contract.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())