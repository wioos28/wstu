# WSTU Dataset — scripts

Dataset-processing code only. No model code, no training code, no servers.

| stage | directory | status |
|---|---|---|
| 1. Discover | `discovery/discover_catalogs.py` | working — logs every query to `metadata/discovery/discovery_log.json` |
| 2. Verify | `discovery/verify_sources.py` | working — evidence to `metadata/verification/` |
| 3. Register | `discovery/build_registry.py`, `discovery/render_sources.py` | working — registry + stats + `docs/SOURCES.md` |
| 4. Select | `metadata/approved_sources.json` | gate defined; row-level selection follows download |
| 5. Download | `download/` | scaffold — reads `approved_sources.json`, pins HF revision, streams |
| 6. Normalize | `normalize/` | scaffold — maps rows to the WSTU schema, keeps provenance |
| 7. Dedup | `dedup/` | scaffold — five levels + translation-duplicate map |
| 8. Validate | `validate/` | scaffold — acceptance gate, leakage checks |
| 9. Balance | `build/` | scaffold — language/domain quotas |
| 10. Build | `build/` | scaffold — emits `data/train.jsonl`, `validation.jsonl`, `test.jsonl` |

Ordering guarantee: nothing in `download/` runs unless the source is `status=verified` in the
registry; nothing in `build/` reads an `evaluation_only` row into `train.jsonl`.