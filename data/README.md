# WSTU Dataset — data/

Final artifacts are built in phase 12 and are **not yet materialized**:

* `train.jsonl`
* `validation.jsonl`
* `test.jsonl`

Policy: raw downloads live under `data/raw/` (git-ignored, never committed). Only the filtered,
deduplicated, validated final splits are committed — and only after they pass the acceptance
gate in `docs/FILTERING.md`. `evaluation_only` sources never contribute rows to `train.jsonl`.