# WSTU Dataset — v0.1

**Dataset repository only.** This repository produces a curated, multilingual, multi-domain
dataset for **WSTU**, a model whose job is to turn a *question/state* into a **structured
decision** (A/B/C/D, YES/NO, TRUE/FALSE, number, class_id, action_id, label) rather than long
prose.

> No model, no training loop, no fine-tuning, no inference server, no API, no deployment lives
> here. `scripts/` only performs dataset processing.

---

## 1. What is the WSTU Dataset?

A filtered, deduplicated, license-audited, provenance-preserving collection of samples shaped
for structured decision-making. Each accepted sample is normalized to:

```json
{
  "id": "wstu_000001",
  "language": "en",
  "domain": "math",
  "task": "multiple_choice",
  "question": "1 + 1 = ?",
  "context": null,
  "choices": ["1", "2", "3", "4"],
  "answer": "B",
  "source_dataset": "openai/gsm8k",
  "source_id": "train/0",
  "license": "mit",
  "difficulty": "medium"
}
```

If the source has no choices, **no fake choices are created** — the record keeps only
`question` + `answer`.

## 2. Current status (honest)

| Phase | Name | Status |
|---|---|---|
| 1 | Discovery | done — 180 candidates, 107 logged queries, 1480 triaged hits |
| 2 | Source verification | done — 175/180 Hugging Face ids machine-verified |
| 3 | Registry + license audit | done — `metadata/dataset_registry.json` |
| 4 | Selection | gated — `metadata/approved_sources.json` |
| 5 | Download | not started |
| 6-9 | Normalize / dedup / validate / balance | scaffolded in `scripts/` |
| 10-12 | Build `data/*.jsonl` + final report | not started |

**Target:** ~700,000 high-quality samples **after** filtering. Raw data is not capped at 700k —
sources in the registry are estimated at 1B+ candidate samples, of which only the WSTU-suited,
licensed, non-duplicate, non-leaking subset will be selected. If only 580k samples clear the
gate, the dataset ships with 580k. Padding with junk to reach exactly 700,000 is forbidden.

## 3. Coverage at a glance

| Metric | Value |
|---|---|
| Datasets discovered / registered | **180** |
| Hugging Face ids verified | **175** |
| Distinct languages referenced | **434** |
| Datasets referencing English | 98 |
| Multilingual datasets (>5 languages) | 40 |
| English-only datasets | 67 |
| Domains | 12 |
| Approved for training (`status=verified`) | **66** |
| `evaluation_only` (benchmark; never trained on) | 33 |
| `legal_review` (license unknown / non-commercial) | 72 |
| `future_candidate` (multimodal, not v0.1) | 6 |
| `unknown` (unresolved provenance) | 3 |

Domain spread (datasets): mathematics 20 · coding 19 · low-resource 18 · multilingual 18 ·
QA 14 · logic 12 · decision 11 · science 11 · Vietnamese 11 · language 8 · multimodal 8 ·
general knowledge 6.

## 4. Where the data comes from

Primary discovery surface: the **Hugging Face Datasets API** (metadata + `search` for new
hits). Official repositories and papers are cross-linked and reachability-checked. Reference
methodology: Microsoft REDSTONE (filtering design only, no raw text taken).

Full list, URLs and per-source notes: [`docs/SOURCES.md`](docs/SOURCES.md).
Research coverage and every query used: [`docs/DATASET_REPORT.md`](docs/DATASET_REPORT.md).

## 5. How data is (and will be) filtered

`RAW → LICENSE FILTER → QUALITY FILTER → NORMALIZE → DEDUP → ANSWER VALIDATION →
LANGUAGE BALANCE → DOMAIN BALANCE → FINAL SELECTION → ~700K`

* **Answers must be usable.** A sample without a verifiable answer/label is rejected.
* **Benchmarks are not training data.** Datasets declared `evaluation_only` (e.g. Belebele,
  MMLU-Pro, BIG-Bench Hard, SWE-bench) are routed to evaluation splits only.
* **No leakage.** Train/test overlap, translated duplicates and same-passage collisions are
  checked before anything enters `train.jsonl`.
* Two independent 0-100 scores per source: **Quality** (provenance/annotation/verifiability,
  never size) and **WSTU fit** (how close the sample shape is to a structured decision).

Details: [`docs/FILTERING.md`](docs/FILTERING.md), [`docs/DATA_QUALITY.md`](docs/DATA_QUALITY.md).

## 6. How licenses are handled

Publicly downloadable **≠** commercially reusable. Licenses are read from the primary source
(Hugging Face card metadata, recorded together with the exact field it came from), then
classified:

* **permissive** → may be trained on (still subject to attribution / share-alike terms),
* **non-commercial / research-only / no-derivatives / unknown / `other`** → `legal_review`,
  excluded from the training pool until a human resolves them.

See [`docs/LICENSES.md`](docs/LICENSES.md) and `metadata/license_stats.json`.

## 7. How provenance is preserved

Every record chains back:
`WSTU sample → source_dataset → source_id → original URL → license (+ revision sha)`.
Machine facts live in `metadata/verification/`, the merged record in
`metadata/dataset_registry.json`, the per-dataset chain in `metadata/provenance.json`.
Nothing is inferred: unverifiable fields are `null` / `unknown`, never fabricated.

## 8. Reproduce

```bash
# 1. discover (search + log every query)              [network]
python3 scripts/discovery/discover_catalogs.py

# 2. verify every source against its primary origin   [network]
python3 scripts/discovery/verify_sources.py

# 3. build the registry + statistics + approval gate  [offline]
python3 scripts/discovery/build_registry.py
```

The three steps above are stdlib-only; `requirements.txt` lists deps for later download /
normalize phases.

## 9. Repository layout

```
metadata/  discovery/ (candidates + query log)   verification/ (evidence)
           dataset_registry.json|.csv  *_stats.json  approved_sources.json  provenance.json
data/      train.jsonl  validation.jsonl  test.jsonl          (built in phase 12)
docs/      SOURCES  FILTERING  LICENSES  DEDUPLICATION  DATA_QUALITY  DATASET_REPORT
scripts/   discovery/ download/ normalize/ dedup/ validate/ build/
```

## 10. License

Repository code and metadata: see [`LICENSE`](LICENSE). **Each dataset keeps its own license**;
the upstream dataset card of every source remains authoritative. Redistributing WSTU Dataset
must respect each source's terms — see [`docs/LICENSES.md`](docs/LICENSES.md). 
