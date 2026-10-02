# WSTU Dataset — License Policy & Audit

## 1. Core rule

> **Publicly downloadable is NOT the same as commercially reusable.**

A dataset being open on the internet never, by itself, authorizes training, modification or
redistribution. Every source is audited and classified before it can contribute samples.

## 2. How a license is read

Licenses are taken **only** from the primary source and stored verbatim together with the exact
field they came from (`metadata/verification/hf_verification.json` → `license`,
`license_source` ∈ {`cardData.license`, `tags[license:*]`}). If the primary source declares no
license, the record is `unknown` — it is never inferred from the paper, the repo or a mirror.

## 3. Classification

| class | meaning | commercial_use | training |
|---|---|---|---|
| `permissive` | MIT, Apache-2.0, CC-BY, CC-BY-SA, CC0, ODC-BY, BSD, GPL, AFL-3.0, … | `yes` | allowed (subject to attribution / share-alike) |
| `noncommercial` | CC-BY-NC*, research-only, non-commercial | `no` | blocked → `legal_review` |
| `no_derivatives` | CC-BY-ND*, CC-BY-NC-ND* | `review` | blocked → `legal_review` (derivative works forbidden) |
| `unknown` | no license declared, or a non-standard tag (`other`, bare `cc`) | `unknown` | blocked → `legal_review` |

The exact allow-lists live in `scripts/discovery/taxonomy.json` → `license_policy`. Edit there,
not in the generated registry.

Notes on specific tags:
* **CC-BY-SA / ODbL / GPL** permit commercial use but are share-alike / copyleft — the built
  corpus inherits that obligation, so attribution and share-alike must be propagated.
* **`other`** (Hugging Face's catch-all) is treated as `unknown` → `legal_review`. It frequently
  hides custom research terms.
* **A bare `cc`** tag is ambiguous (no version, no clause) → `unknown` → `legal_review`.
* **ND** licenses are especially incompatible with a *training corpus* because the corpus is a
  derivative work.

## 4. Current audit result

From `metadata/license_stats.json` (156 datasets):

| license key | datasets |
|---|---|
| unknown | 41 |
| mit | 28 |
| apache-2.0 | 27 |
| cc-by-sa-4.0 | 16 |
| cc-by-4.0 | 13 |
| other | 13 |
| cc-by-nc-4.0 | 7 |
| cc | 3 |
| cc-by-sa-3.0 | 3 |
| afl-3.0 | 2 |
| cc-by-nc-3.0, cc-by-nc-sa-2.0, gpl-3.0 | 1 each |

By class: **permissive 90 · unknown 59 · noncommercial 9**.

By outcome: `verified` 56 · `evaluation_only` 28 · `legal_review` 63 · `future_candidate` 6 ·
`unknown` 3.

### Interpretation
* 63 sources sit in `legal_review`. The large majority are **`unknown`** or **`other`**, not
  confirmed non-commercial. They are *not rejected forever* — they are queued for a human pass
  that reads the upstream paper/repo license and either promotes them or rejects them.
* Notable confirmed non-commercial sources: `tiny_aya_thinker` (CC-BY-NC-4.0), `asdiv`,
  `indicparaphrase`, `indicwikibio` (CC-BY-NC-4.0), `afrisenti` (CC-BY-NC-SA-2.0).
* Notable `other`/unknown sources needing manual review: `the_stack`, `starcoderdata` (BigCode
  per-repo licenses), `glue`, `super_glue`, `coqa`, `conll2003`, `code_search_net`, `indic_glue`.

## 5. Translation & synthetic data

* **Translated data** records `original_dataset` and `translation_method`, and human vs machine
  translation are kept distinct (`human_translated` vs `machine_translated`). An English dataset
  translated into 50 languages is **not** counted as 50 independent datasets.
* **Synthetic data** is tagged `data_origin = synthetic` and is never blended silently with
  human-annotated data. Programmatically generated sets (e.g. DeepMind Mathematics, ProofWriter,
  RuleTaker) can be high quality *and* exactly verifiable, but they stay labelled.

## 6. Repository license vs source licenses

`LICENSE` (MIT) covers **only** this repository's scripts, metadata and documentation. It does
**not** re-license any upstream content. Redistributing `data/*.jsonl` requires satisfying every
included source's terms simultaneously (attribution, share-alike, no-derivatives). Sources in
`legal_review` are excluded from the training pool precisely because those terms are unconfirmed.

## 7. Adding a new source

1. Add it to `metadata/discovery/cand_*.json`.
2. Run `verify_sources.py` to capture the primary-source license (with `license_source`).
3. Run `build_registry.py`; the policy in `taxonomy.json` decides `status`.
4. A source only becomes `verified` if provenance is known **and** the license class is
   `permissive`.