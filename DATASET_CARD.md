# WSTU Dataset v0.1 — Dataset Card

## Dataset description

**Summary.** WSTU Dataset is a curated, multilingual, multi-domain collection of
question/state → structured-decision samples intended for training and evaluating a model
that answers with *choices, booleans, numbers, labels and action ids* rather than free text.

**Curated by.** The WSTU dataset team.
**Language(s).** 433 distinct language codes are referenced across candidate sources; the
final build targets balanced coverage across several core languages plus a deliberately
retained long tail of low-resource languages (see `metadata/language_stats.json`).
**Domains.** mathematics, reasoning, science, general_knowledge, qa, language, coding, logic,
decision, multilingual, vietnamese, low_resource, multimodal(future), safety.
**License.** Mixed. Each contributing dataset retains its own license; the upstream dataset
card is authoritative. Repository-level artifacts are covered by `LICENSE`.

## Structure

### Data fields (normalized target)

| field | type | notes |
|---|---|---|
| `id` | string | `wstu_<%06d>` |
| `language` | string | BCP-47-ish code |
| `domain` | string | WSTU domain taxonomy |
| `task` | string | WSTU task taxonomy |
| `question` | string\|null | |
| `context` | string\|null | passage/state when the source provides one |
| `choices` | array\|null | only if the source really has choices |
| `answer` | string\|number\|bool | never synthesized |
| `reasoning` | string\|null | only when the source provides a rationale |
| `source_dataset` | string | registry id |
| `source_id` | string | original row/split id |
| `license` | string | normalized license key |
| `difficulty` | string\|null | when annotated |

### Splits

`data/train.jsonl`, `data/validation.jsonl`, `data/test.jsonl`.
Benchmarks declared `evaluation_only` are kept out of `train.jsonl` entirely and are exposed
only through evaluation splits. **Per-source test-set rules are never broken to hit a target count.**

### Data volume (target, not yet materialized)

~700,000 samples after filtering (target). The registry currently estimates 1B+ raw candidate
samples; no raw corpus is committed to this repository.

## Collection process

* **Discovery.** Domain-by-domain queries against the Hugging Face Datasets API, fanned out to
  paper → authors → GitHub → related/translated/successor datasets. Every query is logged in
  `metadata/discovery/discovery_log.json`.
* **Verification.** Each candidate is checked against its primary source; license, languages,
  task categories and the immutable revision `sha` are recorded verbatim in
  `metadata/verification/hf_verification.json`. Declared URLs are reachability-checked.
* **Collection / normalization.** Later phases (download → normalize → dedup → validate).
* **Annotation.** Not re-annotated by us. Original annotation provenance is preserved and
  tagged: `human_annotated`, `human_translated`, `machine_translated`, `mixed`, `synthetic`,
  `raw_crawl`.
* **Synthetic data.** Tagged `data_origin = synthetic` and never blended silently with
  human-annotated data.

## Uses

**Intended.** Training/evaluating structured-decision, multiple-choice, boolean, numeric,
classification and state→action behavior; multilingual and cross-lingual decision making.

**Out of scope.** Natural-language generation quality; safety certification; any use that
violates an upstream `non-commercial` / `no-derivatives` / research-only term.

## Known limitations

* Text-first: multimodal sources are flagged `future_candidate` and excluded from v0.1.
* Machine-translated subsets exist and are tagged; they can lower native-language naturalness.
* Some sources remain `legal_review` (license `unknown` / `other`); these are **not** in the
  training pool.
* Benchmark contamination is an active risk; mitigated by `evaluation_only` routing,
  translated-duplicate detection and train/test overlap checks.
* Language counts reflect *dataset* coverage, not *sample* balance — rebalancing happens in the
  final selection phase.

## Provenance & licensing

See `metadata/provenance.json`, `docs/LICENSES.md`, `docs/SOURCES.md`.
Chain: `WSTU sample → source_dataset → source_id → original URL → license → upstream revision`.

## Citation

Cite WSTU Dataset **and** the individual source datasets used by the final build (their
`paper_url` values are recorded in `metadata/dataset_registry.json`).