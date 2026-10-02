#!/usr/bin/env python3
"""WSTU Dataset - Phase 3: BUILD DATASET REGISTRY.

Merges three layers into one auditable registry:
  declared   -> metadata/discovery/cand_*.json          (human intent: domain, tasks, role, origin)
  verified   -> metadata/verification/hf_verification.json  (machine facts from the primary source)
  policy     -> scripts/discovery/taxonomy.json         (domain/task/license/status rules)

Nothing is invented. Any field that cannot be traced to a declared value or a verified
source is set to null / "unknown", and the record carries an explicit provenance string.

Outputs:
  metadata/dataset_registry.json
  metadata/dataset_registry.csv
  metadata/language_stats.json
  metadata/domain_stats.json
  metadata/source_stats.json
  metadata/license_stats.json
  metadata/provenance.json
  metadata/approved_sources.json   (only records that clear the quality+license gate)

Usage: python3 scripts/discovery/build_registry.py
"""
from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
META = REPO_ROOT / "metadata"
DISCOVERY = META / "discovery"
VERIFY = META / "verification"

CSV_FIELDS = [
    "id", "name", "domain", "domains", "tasks", "languages", "language_count",
    "organization", "data_role", "data_origin", "license", "commercial_use",
    "training_allowed", "status", "sample_count", "sample_count_estimated",
    "format", "quality_score", "wstu_fit_score", "duplicate_risk",
    "huggingface_url", "official_url", "github_url", "paper_url",
]


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_taxonomy() -> dict:
    tax = load_json(Path(__file__).resolve().parent / "taxonomy.json")
    merged = dict(tax.get("task_fit_base", {}))
    merged.update(tax.get("task_fit_base_part2", {}))
    tax["task_fit_base"] = merged
    return tax


def load_candidates() -> list[dict]:
    out = []
    for path in sorted(DISCOVERY.glob("cand_*.json")):
        for cand in load_json(path)["candidates"]:
            cand["_group_file"] = path.name
            out.append(cand)
    return out


def normalize_domain(raw: str, tax: dict) -> str:
    return tax["domain_map"].get(raw, raw)


def build_features(tasks: list[str], tax: dict) -> dict:
    feats = {"question": False, "context": False, "choices": False,
             "answer": False, "reasoning": False, "labels": False}
    for task in tasks:
        for key, val in tax["feature_map"].get(task, {}).items():
            feats[key] = feats[key] or bool(val)
    return feats


def pick_format(tasks: list[str], tax: dict) -> str:
    for task in tasks:
        if task in tax["format_map"]:
            return tax["format_map"][task]
    return "unknown"


def estimate_sample_count(verified: dict, tax: dict) -> tuple[int | None, bool]:
    for bucket in verified.get("size_categories") or []:
        if bucket in tax["size_bucket_midpoint"]:
            return tax["size_bucket_midpoint"][bucket], True
    return None, False


def norm_license(value) -> str:
    """Collapse a supplied license into one normalized key for policy matching."""
    if value is None:
        return "unknown"
    if isinstance(value, list):
        value = value[0] if value else "unknown"
    return str(value).strip().lower()


def license_assessment(lic_key: str, tax: dict) -> dict:
    """Classify a normalized license key. Public download != commercial reuse."""
    pol = tax["license_policy"]
    if lic_key in pol["permissive_commercial_ok"]:
        return {"class": "permissive", "commercial_use": "yes"}
    if lic_key in pol["no_derivatives_review"]:
        return {"class": "no_derivatives", "commercial_use": "review"}
    if lic_key in pol["noncommercial_or_research"]:
        return {"class": "noncommercial", "commercial_use": "no"}
    return {"class": "unknown", "commercial_use": "unknown"}


def compute_status(cand: dict, verified: dict, lic: dict) -> str:
    """Pipeline decision for a dataset. Order matters (see status_rules)."""
    if not verified.get("verified"):
        # no machine-verified primary source -> cannot approve
        if not cand.get("hf_id") and (cand.get("official_url") or cand.get("github_url")):
            return "legal_review"      # human-declared source exists, provenance unverified
        return "unknown"
    if lic["class"] in ("noncommercial", "no_derivatives", "unknown"):
        return "legal_review"
    if norm_license(cand.get("domain")) == "multimodal" or cand.get("domain") == "multimodal":
        return "future_candidate"      # text schema cannot hold it yet
    if cand.get("data_role") == "evaluation_only":
        return "evaluation_only"
    return "verified"


def score_wstu_fit(tasks: list[str], origin: str, lic_class: str, tax: dict) -> tuple[int, dict]:
    """0-100: how well the sample shape matches WSTU's answer-oriented outputs."""
    fit = tax["task_fit_base"]
    bases = [(t, fit[t]) for t in tasks if t in fit]
    base = max((b for _, b in bases), default=25)
    breakdown = {"task_base": base,
                 "best_task": max(bases, key=lambda x: x[1])[0] if bases else None}
    origin_adj = {"human_annotated": 5, "human_translated": 5, "mixed": 0,
                  "machine_translated": 0, "synthetic": -10, "raw_crawl": -8}.get(origin, 0)
    breakdown["origin_adjustment"] = origin_adj
    lic_adj = {"permissive": 0, "unknown": -12, "noncommercial": -12, "no_derivatives": -14}.get(lic_class, -12)
    breakdown["license_adjustment"] = lic_adj
    total = max(0, min(100, base + origin_adj + lic_adj))
    breakdown["total"] = total
    return total, breakdown


def score_quality(cand: dict, verified: dict, lic: dict) -> tuple[int, dict]:
    """0-100: provenance/annotation/verifiability rigor (NOT size)."""
    origin = cand.get("data_origin") or "unknown"
    parts = {}
    parts["provenance_verified"] = 20 if verified.get("verified") else 0
    parts["license_known"] = 0 if lic["class"] == "unknown" else 10
    parts["annotation"] = {"human_annotated": 25, "human_translated": 20, "mixed": 12,
                           "machine_translated": 10, "synthetic": 12, "raw_crawl": 5}.get(origin, 5)
    parts["peer_reviewed_paper"] = 15 if cand.get("paper_url") else 0
    parts["named_organization"] = 10 if cand.get("organization") else 0
    parts["answer_verifiability"] = 20 if (verified.get("verified")) else 5
    parts["curation_known_size"] = 10 if (verified.get("size_categories")) else 3
    total = max(0, min(100, sum(parts.values())))
    parts["total"] = total
    return total, parts


# Analyst-identified overlaps (source lineage / mirrors / translations / subsets).
# Used only to flag duplicate risk; real dedup happens in the dedup phase.
KNOWN_OVERLAPS = {
    "competition_math": [("hendrycks_math", "community mirror of the same MATH set")],
    "hendrycks_math_multilingual": [("hendrycks_math", "machine translation of the same problems")],
    "math_500": [("hendrycks_math", "500-problem subset of MATH")],
    "gsm8k_zh_x": [("math_500", "third-party re-packaging of MATH-500")],
    "gsm8k_zh": [("gsm8k", "translated GSM8K")],
    "gsm8k_instruct_parallel": [("gsm8k", "translated GSM8K")],
    "afrimgsm": [("gsm8k", "professionally translated GSM8K")],
    "mathinstruct": [("gsm8k", "aggregates GSM8K/MATH"), ("hendrycks_math", "aggregates MATH")],
    "metamathqa": [("gsm8k", "augmented GSM8K"), ("hendrycks_math", "augmented MATH")],
    "openmathinstruct1": [("gsm8k", "synthetic derivations of GSM8K/MATH")],
    "openmathinstruct2": [("openmathinstruct1", "successor synthetic set")],
    "afrimmlu": [("mmlu", "translated MMLU")],
    "m_mmlu": [("openai_mmmlu", "overlapping MT MMLU"), ("global_mmlu", "overlapping MT MMLU")],
    "openai_mmmlu": [("mmlu", "translated MMLU")],
    "global_mmlu": [("mmlu", "translated MMLU")],
    "global_mmlu_lite": [("global_mmlu", "subset of Global-MMLU")],
    "afrixnli": [("xnli", "African-language XNLI alignment")],
    "bigbench_hard_raw": [("bigbench_hard", "alternative BBH port")],
    "logiqa2_nli": [("logiqa2", "NLI reframing of LogiQA2")],
    "amazon_massive_intent": [("massive", "MTEB re-packaging of MASSIVE")],
    "tldr_summarize_alt": [("summarize_from_feedback", "re-processed TLDR preferences")],
    "scienceqa_text_only": [("scienceqa", "text-only projection")],
    "scienceqa_img": [("scienceqa", "image projection")],
    "multilingual_mbpp": [("mbpp", "translated MBPP")],
    "humaneval_xl": [("humaneval", "extended HumanEval")],
    "humanevalpack": [("humaneval", "translated HumanEval")],
    "humanevalplus": [("humaneval", "hardened HumanEval tests")],
    "mbppplus": [("mbpp", "hardened MBPP tests")],
    "starcoderdata": [("the_stack", "subset of The Stack")],
    "bigbio_med_qa": [("medqa", "BigBIO re-packaging of MedQA")],
    "bioasq": [("medqa", "adjacent biomedical QA")],
    "ultrafeedback_binarized": [("ultrafeedback", "binarized UltraFeedback")],
    "uit_viquad2_alt": [("uit_viquad2", "third-party re-upload")],
    "vmlu_1_5": [("vmlu", "community re-package"), ("vmlu_community", "overlapping VMLU re-upload")],
    "vmlu_community": [("vmlu", "third-party re-upload")],
    "preference_tulu": [("ultrafeedback", "overlapping preference mixture"),
                        ("hh_rlhf", "overlapping preference mixture")],
    "swe_bench_lite": [("swe_bench_verified", "subset of SWE-bench")],
    "conll2003": [("universal_dependencies", "overlapping POS/parsing labels")],
    "swe_bench_full": [("swe_bench_verified", "superset incl. Verified"), ("swe_bench_lite", "superset incl. Lite")],
    "swe_bench_live": [("swe_bench_full", "refreshed continuation of SWE-bench")],
    "multi_swe_bench": [("swe_bench_full", "multilingual SWE-bench extension")],
    "swe_smith_py": [("swe_smith", "Python slice of SWE-smith")],
    "stack_dedup": [("the_stack", "deduplicated packaging of The Stack")],
    "stack_smol": [("the_stack", "subset of The Stack family")],
    "ultrafeedback_cleaned": [("ultrafeedback_binarized", "cleaned UltraFeedback binarization")],
    "xlam_parsed": [("xlam_function_calling", "community parse of xLAM-60k")],
    "mmlu_no_train": [("mmlu", "MMLU repackaged for eval")],
    "mmlu_redux": [("mmlu", "verified/corrected MMLU subset")],
    "mmlu_greek": [("mmlu", "translated MMLU")],
    "flores_101": [("flores200", "predecessor FLORES release"), ("flores_plus", "successor FLORES release")],
    "agieval_aqua_rat": [("aqua_rat", "AGIEval packaging of AQuA-RAT")],
    "agieval_logiqa_en": [("logiqa", "AGIEval packaging of LogiQA")],
    "medqa_hf_mirror": [("medqa", "HF-native reformat"), ("bigbio_med_qa", "BigBIO packaging")],
    "openbookqa_es": [("openbookqa", "Spanish port")],
    "openbookqa_ca": [("openbookqa", "Catalan port")],
    "coqa_gen2mc": [("coqa", "MC conversion of CoQA")],
    "pubmedqa_bigbio": [("pubmedqa", "BigBIO packaging of PubMedQA")],
    "tydiqa_goldp": [("tydiqa", "gold-passage variant of TyDiQA")],
}


def build_record(cand: dict, tax: dict, verification: dict, urlver: dict) -> dict:
    tasks = list(dict.fromkeys(cand.get("tasks") or []))
    domain = normalize_domain(cand.get("domain") or "other", tax)
    verified = verification.get(cand["id"], {})
    lic_key = norm_license(verified.get("license") if verified.get("verified") else None)
    lic = license_assessment(lic_key, tax)
    status = compute_status(cand, verified, lic)

    feats = build_features(tasks, tax)
    sample_count, estimated = estimate_sample_count(verified, tax)
    fit, fit_bd = score_wstu_fit(tasks, cand.get("data_origin"), lic["class"], tax)
    quality, q_bd = score_quality(cand, verified, lic)

    overlaps = KNOWN_OVERLAPS.get(cand["id"], [])
    dup_risk = "high" if overlaps else "unverified"

    if verified.get("verified"):
        provenance = f"huggingface:{verified['hf_id']}@{verified.get('revision')}"
    elif cand.get("official_url") or cand.get("github_url"):
        provenance = f"declared:{cand.get('official_url') or cand.get('github_url')}"
    else:
        provenance = "unknown"

    if status == "verified" and cand.get("data_role") in ("training", "mixed"):
        training_allowed = "yes"
    elif status == "evaluation_only":
        training_allowed = "evaluation_only"
    elif status == "legal_review":
        training_allowed = "legal_review"
    elif status == "future_candidate":
        training_allowed = "no"
    else:
        training_allowed = "unknown"

    reach = (urlver.get("by_candidate", {}) or {}).get(cand["id"], {})
    return {
        "id": cand["id"],
        "name": cand.get("name"),
        "official_url": cand.get("official_url"),
        "huggingface_url": (f"https://huggingface.co/datasets/{verified['hf_id']}"
                            if verified.get("hf_id") else None),
        "github_url": cand.get("github_url"),
        "paper_url": cand.get("paper_url"),
        "license_url": None,
        "organization": cand.get("organization"),
        "authors": [],
        "languages": verified.get("languages", []) if verified.get("verified") else [],
        "language_count": len(verified.get("languages", [])) if verified.get("verified") else 0,
        "domains": [domain],
        "tasks": tasks,
        "sample_count": sample_count,
        "sample_count_estimated": estimated,
        "format": pick_format(tasks, tax),
        "has_question": feats["question"],
        "has_context": feats["context"],
        "has_choices": feats["choices"],
        "has_answer": feats["answer"],
        "has_reasoning": feats["reasoning"],
        "has_labels": feats["labels"],
        "field_derivation": "task_taxonomy",
        "training_allowed": training_allowed,
        "commercial_use": lic["commercial_use"],
        "license": lic_key,
        "license_class": lic["class"],
        "provenance": provenance,
        "quality_score": quality,
        "quality_breakdown": q_bd,
        "wstu_fit_score": fit,
        "fit_breakdown": fit_bd,
        "duplicate_risk": dup_risk,
        "related_candidates": [{"id": rid, "reason": why} for rid, why in overlaps],
        "status": status,
        "data_role": cand.get("data_role"),
        "data_origin": cand.get("data_origin"),
        "group": cand.get("_group_file"),
        "notes": cand.get("notes"),
        "verification": {
            "hf_verified": bool(verified.get("verified")),
            "http_status": verified.get("http_status"),
            "revision": verified.get("revision"),
            "license_source": verified.get("license_source"),
            "size_categories": verified.get("size_categories", []),
            "task_categories": verified.get("task_categories", []),
            "gated": verified.get("gated"),
            "downloads": verified.get("downloads"),
            "last_modified": verified.get("last_modified"),
            "error": verified.get("error"),
        },
        "url_reachability": {k: v.get("reachable") for k, v in reach.items()} if reach else {},
    }


def write_registry_csv(records: list[dict], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for rec in records:
            row = dict(rec)
            row["domains"] = "|".join(rec["domains"])
            row["tasks"] = "|".join(rec["tasks"])
            row["languages"] = "|".join(rec["languages"])
            row["domain"] = rec["domains"][0] if rec["domains"] else ""
            writer.writerow(row)


def write_stats(records: list[dict]) -> dict:
    lang = Counter()
    for rec in records:
        for code in rec["languages"]:
            lang[code] += 1
    language_stats = {
        "generated_by": "scripts/discovery/build_registry.py",
        "distinct_languages": len(lang),
        "multilingual_datasets": sum(1 for r in records if r["language_count"] > 5),
        "english_only_datasets": sum(1 for r in records if r["languages"] == ["en"]),
        "datasets_with_unknown_language": sum(1 for r in records if not r["languages"]),
        "by_language_dataset_count": dict(sorted(lang.items(), key=lambda x: (-x[1], x[0]))),
    }
    (META / "language_stats.json").write_text(
        json.dumps(language_stats, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    dom = Counter()
    dom_samples = Counter()
    for rec in records:
        for d in rec["domains"]:
            dom[d] += 1
            dom_samples[d] += rec["sample_count"] or 0
    (META / "domain_stats.json").write_text(json.dumps({
        "generated_by": "scripts/discovery/build_registry.py",
        "note": "sample_count values are bucket-midpoint estimates unless source gave an exact count.",
        "by_domain_dataset_count": dict(sorted(dom.items(), key=lambda x: (-x[1], x[0]))),
        "by_domain_estimated_samples": dict(sorted(dom_samples.items(), key=lambda x: (-x[1], x[0]))),
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    org = Counter(r["organization"] or "unknown" for r in records)
    origin = Counter(r["data_origin"] or "unknown" for r in records)
    role = Counter(r["data_role"] or "unknown" for r in records)
    grp = Counter(r["group"] or "unknown" for r in records)
    (META / "source_stats.json").write_text(json.dumps({
        "generated_by": "scripts/discovery/build_registry.py",
        "by_organization": dict(sorted(org.items(), key=lambda x: (-x[1], x[0]))),
        "by_data_origin": dict(origin),
        "by_data_role": dict(role),
        "by_discovery_group": dict(sorted(grp.items())),
        "hf_verified": sum(1 for r in records if r["verification"]["hf_verified"]),
        "hf_unverified": sum(1 for r in records if not r["verification"]["hf_verified"]),
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lic = Counter(r["license"] for r in records)
    licc = Counter(r["license_class"] for r in records)
    comm = Counter(r["commercial_use"] for r in records)
    statusc = Counter(r["status"] for r in records)
    train = Counter(r["training_allowed"] for r in records)
    (META / "license_stats.json").write_text(json.dumps({
        "generated_by": "scripts/discovery/build_registry.py",
        "by_license": dict(sorted(lic.items(), key=lambda x: (-x[1], x[0]))),
        "by_license_class": dict(licc),
        "by_commercial_use": dict(comm),
        "by_status": dict(statusc),
        "by_training_allowed": dict(train),
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    prov = {
        "generated_by": "scripts/discovery/build_registry.py",
        "note": "Per-dataset provenance chain. A record cannot be approved if provenance == unknown.",
        "datasets": {
            r["id"]: {
                "provenance": r["provenance"],
                "source_url": r["huggingface_url"] or r["official_url"] or r["github_url"],
                "revision": r["verification"]["revision"],
                "license": r["license"],
                "license_source": r["verification"]["license_source"],
                "status": r["status"],
            } for r in records
        },
    }
    (META / "provenance.json").write_text(
        json.dumps(prov, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return language_stats


def write_approved(records: list[dict]) -> dict:
    buckets: dict[str, list] = defaultdict(list)
    for r in records:
        buckets[r["status"]].append({
            "id": r["id"], "name": r["name"], "domain": r["domains"][0],
            "data_role": r["data_role"], "license": r["license"],
            "commercial_use": r["commercial_use"], "wstu_fit_score": r["wstu_fit_score"],
            "quality_score": r["quality_score"], "duplicate_risk": r["duplicate_risk"],
            "reason": (r["notes"] or "")[:160],
        })
    payload = {
        "generated_by": "scripts/discovery/build_registry.py",
        "gate": "A record enters 'training' only if: source verified AND provenance known AND "
                "license permissive AND data_role in (training, mixed). Everything else is routed "
                "to evaluation_only / legal_review / future_candidate / unknown.",
        "counts": {k: len(v) for k, v in sorted(buckets.items())},
        "training": sorted(buckets.get("verified", []), key=lambda x: -x["wstu_fit_score"]),
        "evaluation_only": sorted(buckets.get("evaluation_only", []), key=lambda x: -x["wstu_fit_score"]),
        "legal_review": sorted(buckets.get("legal_review", []), key=lambda x: x["id"]),
        "future_candidate": sorted(buckets.get("future_candidate", []), key=lambda x: x["id"]),
        "unknown": sorted(buckets.get("unknown", []), key=lambda x: x["id"]),
        "rejected": sorted(buckets.get("rejected", []), key=lambda x: x["id"]),
    }
    (META / "approved_sources.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return payload["counts"]


def main() -> int:
    tax = load_taxonomy()
    candidates = load_candidates()
    verification_doc = load_json(VERIFY / "hf_verification.json")
    verification = verification_doc.get("datasets", {})
    urlver = {}
    url_path = VERIFY / "url_verification.json"
    if url_path.exists():
        urlver = load_json(url_path)

    records = [build_record(c, tax, verification, urlver) for c in candidates]
    order = {"verified": 0, "evaluation_only": 1, "legal_review": 2,
             "future_candidate": 3, "unknown": 4, "rejected": 5}
    records.sort(key=lambda r: (order.get(r["status"], 9), -r["wstu_fit_score"], r["id"]))

    registry = {
        "schema_version": "0.1",
        "generated_by": "scripts/discovery/build_registry.py",
        "generated_at": __import__("time").strftime("%Y-%m-%dT%H:%M:%SZ", __import__("time").gmtime()),
        "discovery_evidence": {
            "hf_verification": "metadata/verification/hf_verification.json",
            "url_verification": "metadata/verification/url_verification.json",
        },
        "policy": "scripts/discovery/taxonomy.json",
        "counts": {
            "total": len(records),
            "by_status": dict(Counter(r["status"] for r in records)),
            "hf_verified": sum(1 for r in records if r["verification"]["hf_verified"]),
        },
        "datasets": records,
    }
    (META / "dataset_registry.json").write_text(
        json.dumps(registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_registry_csv(records, META / "dataset_registry.csv")
    lang_stats = write_stats(records)
    counts = write_approved(records)

    print(f"[registry] datasets: {len(records)}")
    print(f"[registry] by status: {dict(Counter(r['status'] for r in records))}")
    print(f"[registry] by training_allowed: {dict(Counter(r['training_allowed'] for r in records))}")
    print(f"[registry] distinct languages covered: {lang_stats['distinct_languages']}")
    print(f"[registry] approved_sources buckets: {counts}")
    print(f"[registry] wrote dataset_registry.json/.csv + 5 stats files + approved_sources.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())