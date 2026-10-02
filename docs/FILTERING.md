# WSTU Dataset — Filtering Pipeline

## 0. Principle

> The goal is **not the largest dataset**. It is a clean, multilingual, multi-domain dataset
> with clear provenance that is suitable for WSTU and good enough to be the foundation for a
> decision/reasoning model.

Two consequences that shape every stage:

1. **Nothing is added just to hit a number.** If only 580k samples pass the gates, the build
   ships 580k. Padding with low-quality data to reach 700,000 is forbidden.
2. **Unverifiable = excluded.** A missing license, a missing answer, an unresolved source or an
   unknown language is not guessed. It becomes `unknown` / `legal_review` and stays out of the
   training pool.

## 1. Stage order

```
RAW
  ↓  LICENSE FILTER      keep only license_class = permissive, and route evaluation_only aside
  ↓  QUALITY FILTER      drop corrupt / empty / unusable rows, keep provenance
  ↓  NORMALIZATION       map every row to the WSTU schema (question/context/choices/answer/...)
  ↓  DEDUPLICATION       exact → normalized → near → cross-dataset → semantic
  ↓  ANSWER VALIDATION   answer must exist, be well-formed and match the declared answer space
  ↓  LANGUAGE BALANCE    protect the long tail; do not let English swamp the corpus
  ↓  DOMAIN BALANCE      keep mathematics/reasoning/science/knowledge/QA/language/coding/logic/decision/multilingual
  ↓  FINAL SELECTION     per-source caps, dedup-aware, leakage-aware
  ↓  ~700K samples       data/train.jsonl + validation.jsonl + test.jsonl
```

## 2. Stage detail

### 2.1 License filter
Operates on `metadata/dataset_registry.json`. Only `status = verified` sources enter the
training pool. `evaluation_only`, `legal_review`, `future_candidate` and `unknown` are excluded
from `train.jsonl` (the first may populate evaluation splits). See `docs/LICENSES.md`.

### 2.2 Quality filter
Row-level rejection when any of these hold: empty question; empty/invalid answer; answer not in
the declared answer space; malformed choices (duplicate options, no correct option); text that
is mostly markup/boilerplate; truncated context; language not identifiable when the source
claims a specific language.

### 2.3 Normalization
Target schema (see README §1). Rules:
* **Never synthesize choices.** A dataset without choices yields a `choices = null` record.
* Keep the original `source_dataset` + `source_id` on every row (provenance must survive filtering).
* Preserve `data_origin` (`human_annotated` / `human_translated` / `machine_translated` /
  `mixed` / `synthetic` / `raw_crawl`) and, for translated data, the `original_dataset` +
  `translation_method`.
* Preserve `data_role`; never promote a test/benchmark split into training.

### 2.4 Deduplication
Full detail in `docs/DEDUPLICATION.md`. Runs exact → normalized → near-duplicate →
cross-dataset → semantic, and separately detects **translation duplicates** so a translated
copy is not counted as new data.

### 2.5 Answer validation
Deterministic where possible: multiple-choice answers must match a choice index/letter; boolean
answers must be in {YES, NO, TRUE, FALSE}; numeric answers are parsed and compared to the
reference; open labels must be in the source's declared label set.

### 2.6 Language balance
Target: no single language above a configured ceiling (working target: English ≤ ~55% of the
corpus). Low-resource languages keep **all** their high-quality samples even when the count is
small, because coverage — not volume — is the point. Language tags come from the verified
source metadata, not from guessing.

### 2.7 Domain balance
Reference split (not a hard quota): mathematics, reasoning, science, general knowledge, QA,
language, coding, logic, decision, multilingual, Vietnamese, low-resource. Quality wins over
forced equality; a domain with less good data simply contributes less.

### 2.8 Final selection
Per-source caps stop any one dataset from dominating. Selection is dedup-aware (a row already
represented by a kept duplicate is skipped) and leakage-aware.

## 3. Leakage controls

* `evaluation_only` datasets never enter `train.jsonl`.
* Train/test overlap checks run against the evaluation splits of the same source.
* Translated-duplicate detection prevents the same question appearing in several languages and
  being counted as independent data.
* Benchmark contamination checks flag rows whose text matches a known benchmark item.

## 4. Acceptance gate (a sample is kept only if ALL hold)

source known · provenance recorded · license compatible · question usable · answer usable ·
no corruption · not a duplicate · no leakage · language identified · domain identified.

If any check fails → **REJECT**.

## 5. Current state

Stages 1–4 are implemented as **registry-level** decisions (`metadata/approved_sources.json`).
Row-level stages 5–12 are the next implementation phase; their scripts live under
`scripts/download`, `scripts/normalize`, `scripts/dedup`, `scripts/validate`, `scripts/build`.