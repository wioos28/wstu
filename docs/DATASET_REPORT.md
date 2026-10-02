# WSTU Dataset v0.1 — Discovery + Registry Report

**Phase:** discovery → verification → registry → license audit (row-level download/normalize/
dedup/validate/build phases are not started).

## 1. Headline numbers

| metric | value |
|---|---|
| Total datasets discovered | **180** |
| Total datasets verified (HF primary source) | **175** (5 non-HF on purpose) |
| Total datasets approved for training (`verified`) | **66** |
| Total datasets in evaluation pool (`evaluation_only`) | **33** |
| Total requiring legal review | **72** |
| Rejected outright | 0 (nothing has reached rejection criteria yet) |
| Unresolved provenance (`unknown`) | 3 |
| Future candidates (multimodal, not v0.1) | 6 |
| Queries executed (logged) | 107 |
| Raw search hits triaged | 1480 |
| Raw samples discovered (bucket-midpoint estimate) | **~1.07 billion** |
| …of which in the approved training pool | ~556M |
| …of which in the evaluation pool | **~673k** |
| …of which parked in legal_review | ~518M |
| Final samples after filtering | pending (target **~700k**, ships fewer if fewer pass the gate) |
| Distinct languages referenced | **434** |
| WSTU domains covered | 12 |

## 2. Distribution

**By status.** verified 56 · evaluation_only 28 · legal_review 63 · future_candidate 6 · unknown 3.
**By license class.** permissive 105 · unknown 66 · noncommercial 9.

**Wave-2 delta.** A logged 107-query / 1480-hit pass over the HF catalogs added 24 datasets
(`cand_wave2*.json`): SWE-bench family (full/live/multilingual/smith-py), deduped Stack cuts,
cleaned UltraFeedback, parsed xLAM, MMLU eval ports (no-train/redux/Greek), FLORES-101,
AGIEval MCQ slices (AQuA/Gaokao/LogiQA), MedQA HF mirror, OpenBookQA es/ca, Sangraha,
IndicVoices, IITB-IndicMonoDoc, CoQA-Gen2MC, BigBIO PubMedQA, TyDiQA-GoldP — each with explicit
lineage back to its parent candidate.
Top keys: unknown 41 · MIT 28 · Apache-2.0 27 · CC-BY-SA-4.0 16 · CC-BY-4.0 13 · other 13 ·
CC-BY-NC-4.0 7 · cc 3 · CC-BY-SA-3.0 3 · AFL-3.0 2.

**By data role.** training 103 · evaluation_only 45 · mixed 1 · unknown 7.
**By origin.** human_annotated 101 · mixed 18 · synthetic 15 · human_translated 9 ·
machine_translated 7 · raw_crawl 3 · unknown 3.

**By domain (datasets).** mathematics 20 · coding 19 · low_resource 18 · multilingual 18 ·
QA 14 · logic 12 · decision 11 · science 11 · Vietnamese 11 · language 8 · multimodal 8 ·
general knowledge 6.

**Languages.** English appears in 98 sources; 40 sources cover >5 languages; 67 are
English-only. The long tail is real: Vietnamese 18, Yoruba 19, Hausa 16, Igbo 14,
Amharic 13, Swahili 20 — on top of Indic (hi 19, bn 16, te 13), Indonesian and African
benchmark families.

## 3. Training vs evaluation separation

`evaluation_only` routing is load-bearing: Belebele, Global-MMLU, MMMLU, XQuAD, MLQA,
FLORES, MMLU-Pro, TruthfulQA, MATH-500, HumanEval(+), MBPP+, BIG-Bench/BBH, SWE-bench,
DS-1000, LiveCodeBench, GAIA, AR-LSAT, MMMU, MathVista, and the multilingual MT-bench rows
can populate evaluation splits but **never** `train.jsonl` — even when their license is
permissive.

## 4. Research coverage

Catalogs: Hugging Face Datasets API (metadata + search, automated in this pass) · Hugging Face
dataset cards (raw README, prose evidence) · GitHub (official repos, reachability-checked) ·
Papers With Code (card links) · arXiv (citation links) · ACL Anthology (citation links) ·
Kaggle / Google Dataset Search / Zenodo / OpenML / UCI / Dataverse / Figshare (catalogued as
planned-expansion; not yet automated) · Microsoft REDSTONE (methodology review only).

Domains searched: multilingual QA/reasoning/classification/translation · math word/symbolic/
competition · science (incl. biomedical) · general knowledge · reading comprehension ·
logic (deductive/NLI/first-order/counterfactual/agentic) · code (generation/debugging/SWE/
agent) · linguistics (GLUE/NLI/POS/NER/parsing/language-ID) · Vietnamese (QA/NLI/MCQ/
translation/sentiment) · low-resource African/South-/Southeast-Asian/Pacific ·
decision (preference/ranking/tool-use/agent) · multimodal (recorded as future candidates).

Queries: every domain query executed is logged in `metadata/discovery/discovery_log.json`;
the built-in set lives in `scripts/discovery/discover_catalogs.py`.

We do **not** claim the world has been exhaustively searched — only the exact coverage above.

## 5. Gaps and next actions

1. **License unknowns (59 datasets).** The `legal_review` queue is dominated by `unknown`/`other`
   card licenses (BigCode sets, GLUE family, IBM QA, `cc`-tagged ports). Next: a human pass over
   paper/repo terms to promote or reject each.
2. **Low-resource depth beyond Masakhane/AI4Bharat/IndoNLP** (Pacific, Indigenous, Central-Asian)
   is thin — explicit expansion queries are planned.
3. **Decision/action** is the smallest mature pool relative to WSTU's core shape; agent-game and
   RL-trajectory sources are the next discovery wave.
4. **Row-level phases** (download → normalize → dedup → validate → balance → build) follow next;
   directors under `scripts/` are scaffolded with interface READMEs.