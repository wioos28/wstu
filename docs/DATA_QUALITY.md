# WSTU Dataset — Data Quality

## 1. Two scores, two questions

Every source in the registry carries two independent 0–100 scores so that *provenance* and
*suitability* never get conflated.

### Quality score (provenance · annotation · verifiability — never size)

| component | max |
|---|---|
| Provenance machine-verified against the primary source | 20 |
| License declared by the primary source | 10 |
| Annotation rigor (human_annotated 25 · human_translated 20 · mixed 12 · synthetic 12 · machine_translated 10 · raw_crawl 5) | 25 |
| Peer-reviewed paper linked | 15 |
| Named publishing organization | 10 |
| Answer verifiability (deterministic answer space confirmed) | 20 |
| Curation known (size/description recorded) | 10 |

A 10k-sample hand-annotated dataset can legitimately outscore a 10M-sample crawl.

### WSTU fit score (how close is the sample shape to a structured decision)

The base is the maximum over the source's WSTU task taxonomy:

* state/query + tools + call (tool_use, function_calling): **94**
* preferences, intents, multiple-choice: **88–90**
* NLI / boolean / yes-no / paraphrase: **84–89**
* numeric / discrete reasoning, math word problems, symbolic math: **82–84**
* reasoning chains, proofs, science/analytical/logic: **76–84**
* code generation / engineering / software tasks: **70–78**
* extractive/short/conversational QA: **68–72**
* NER / sequence labeling / language ID: **74–86**
* instruction-following / summarization / generation: **48–60**
* machine translation / raw language modeling: **22–30**
* pure evaluation harnesses: **40–50**

Adjustments: `human_*` +5 · `synthetic` −10 · `raw_crawl` −8 · `unknown`/non-commercial license −12.

The exact tables live in `scripts/discovery/taxonomy.json` (`task_fit_base`, `feature_map`,
`format_map`). Score mechanics are stored on every record (`quality_breakdown`,
`fit_breakdown`) so any number can be re-derived.

## 2. Score distribution (registry, v0.1)

* `verified` training candidates cluster at quality 90–100 and fit 75–95:
  e.g. `ai2_arc`, `aqua_rat`, `commonsenseqa`, `helpsteer*`, `hh_rlhf`, `logiqa2`, `massive`,
  `mathqa`, `medmcqa`, `medqa`, `mmlu`, `qasc`, `scienceqa`, `strategyqa`,
  `nusax_senti` — all fit ≥ 90 with quality 95–100.
* Fit ≤ 60 is reserved for resources that are *coverage*, not *training shape*:
  raw code corpora (`the_stack`, `starcoderdata`), translation sets (`flores*`, `mafand`,
  `samanantar`, `nusax_mt`), monolingual crawls (`indiccorp_v2`).

## 3. Answer validation targets

* Multiple-choice → answer must equal a choice letter/index.
* Boolean → answer ∈ {YES, NO, TRUE, FALSE}.
* Numeric → parse and compare against the reference numeric value.
* Classification/NLI → label must be in the source's declared label set.
* Pairwise preference → a `chosen` response must exist.
* Tool use → the call must parse against the declared tool schema.

## 4. Noise policy

Row-level noise (markup, boilerplate, truncation, empty fields, identifier language mismatch)
fails the acceptance gate and the row is rejected — it is not repaired, because repaired data
would no longer be attributable to its source.

## 5. What is *not* scored here

* Translation quality (separate human/MT tagging, not a penalty scale).
* Difficulty calibration (recorded where annotated, normalized later).
* Model-based judgments of "usefulness" (would be circular for a training corpus).