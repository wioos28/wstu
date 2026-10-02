# WSTU Dataset — Deduplication

## 1. Why this matters for WSTU

Duplicate-heavy training silently inflates scores and wastes capacity: the same question seen
ten times teaches the model to memorize, not to reason. WSTU needs each sample to carry
*independent* decision signal, so deduplication runs across five levels — never just
`set(question)`.

## 2. Five levels

| level | what it catches | method |
|---|---|---|
| 1. exact duplicate | byte-identical rows | hash of (normalized question, choices, answer) |
| 2. normalized duplicate | same question, different surface | case-fold + whitespace collapse + punctuation strip + Unicode NFKC before hashing |
| 3. near duplicate | same source passage, reworded question | text similarity (edit/token-overlap threshold per domain) |
| 4. cross-dataset duplicate | the same problem packaged by two datasets (e.g. `qwedsacf/competition_math` vs `EleutherAI/hendrycks_math`) | cluster on normalized problem text + identical answers |
| 5. semantic duplicate | paraphrases with the same answer | embedding similarity above a conservative threshold, answer must match |

## 3. Translation duplicates (special case)

A translated copy is **not** a new sample. Rules:

* Every translated row records `original_language`, `translation_method`,
  `original_dataset`, `translation_source`.
* Human-translated and machine-translated rows are kept distinct in metadata.
* A question appearing in N languages counts once toward coverage, not N times toward volume.
* Known translation families are pre-flagged in the registry (`duplicate_risk = high` +
  `related_candidates`), e.g. GSM8K → `Mathoctopus/...Parallel`, AfrimGSM, GSM8K_zh;
  MMLU → Global-MMLU, MMMLU, m_mmlu, AfriMMLU; HumanEval → HumanEval-XL / HumanEvalPack;
  MBPP → multilingual_mbpp; ARC → uhura-arc-easy.

## 4. Leakage control (overlaps with filtering)

* **train/test overlap**: rows matching a known test item of the same or a related dataset are excluded from `train.jsonl`.
* **benchmark contamination**: any row matching an `evaluation_only` benchmark item is quarantined to evaluation splits.
* **same-source-passage collisions**: paraphrased siblings derived from one passage are collapsed to one kept row.
* **answer-pattern leakage**: rows whose answer can be solved from formatting artefacts
  (e.g. option-length bias) are flagged during quality filtering.

## 5. Order of operations

Dedup runs **after normalization** (so duplicates hidden in different formats still match) and
**before language/domain balancing** (so the balance is computed on unique samples, not on
inflated counts).

## 6. Current state

Duplicate risk is currently **flagged, not yet removed**: the registry carries
`duplicate_risk` (`high` where source lineage is confirmed, `unverified` otherwise) and
`related_candidates` pairs in `metadata/approved_sources.json` documents the overlap map. Row-level
deduplication code runs in the next phase under `scripts/dedup/`.