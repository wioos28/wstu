#!/usr/bin/env python3
"""WSTU Dataset - Phase 1: CATALOG DISCOVERY (search + log).

Runs the domain-by-domain discovery queries against the Hugging Face Datasets API and
writes a machine-readable search log. The log is the evidence for the README/REPORT
"Research coverage / queries used" section, and it surfaces datasets the seed list missed.

It does NOT approve anything: results are raw hits to be triaged into metadata/discovery/cand_*.json.

Usage:
    python3 scripts/discovery/discover_catalogs.py                 # run the built-in query set
    python3 scripts/discovery/discover_catalogs.py --query "sorbian mcq" --limit 20
    python3 scripts/discovery/discover_catalogs.py --offline       # reuse cached log only
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LOG_PATH = REPO_ROOT / "metadata" / "discovery" / "discovery_log.json"
USER_AGENT = "wstu-dataset-discovery/0.1 (+https://github.com/wioos28/wstu)"

# Built-in discovery query set, grouped by WSTU domain. Kept here (not in output files)
# so that the reproduction command is stable and every query is auditable.
QUERIES: dict[str, list[str]] = {
    "multilingual": ["aya", "aya_collection", "global-mmlu", "mmmlu", "belebele",
                     "xnli", "flores", "massive", "xquad", "mlqa", "tydiqa", "paws-x"],
    "mathematics": ["gsm8k", "math word problem", "svamp", "asdiv", "mathqa",
                    "aqua rat", "hendrycks math", "competition math", "numglue",
                    "mathinstruct", "openmathinstruct", "metamathqa"],
    "science": ["arc science", "sciq", "qasc", "openbookqa", "scienceqa",
                "medqa", "medmcqa", "pubmedqa", "bioasq"],
    "general_knowledge": ["mmlu", "mmlu-pro", "commonsenseqa", "hellaswag",
                          "truthfulqa", "triviaqa", "boolq", "bigbench", "bbh",
                          "natural questions"],
    "qa": ["squad", "hotpotqa", "drop", "coqa", "quac", "race", "multirc",
           "qangaroo", "newsqa"],
    "logic": ["logiqa", "logiqa2", "folio", "proofwriter", "ruletaker",
              "reclor", "strategyqa", "musr", "ar lsat"],
    "coding": ["humaneval", "mbpp", "apps code", "code contests", "codesearchnet",
               "swe-bench", "ds-1000", "livecodebench", "the stack", "starcoderdata"],
    "language": ["superglue", "conll2003", "universal dependencies",
                 "language identification"],
    "vietnamese": ["vietnamese", "vmlu", "viquad", "vinli", "phomt", "vlsp"],
    "low_resource": ["masakhane", "afriqa", "afrimmlu", "afrisenti", "afrimgsm",
                     "ai4bharat", "indic", "nusax", "seacrowd",
                     "maori", "inuktitut", "tigrinya"],
    "decision": ["agent trajectory", "tool use function calling", "preference dataset",
                 "rlhf hh", "helpsteer", "ultrafeedback", "xlam", "gaia benchmark",
                 "summarize feedback"],
    "multimodal": ["mmmu", "mathvista", "docvqa", "chartqa", "textvqa"],
}


def query_hf(search: str, limit: int = 15) -> list[dict]:
    url = ("https://huggingface.co/api/datasets?"
           + urllib.parse.urlencode({"search": search, "limit": limit,
                                     "sort": "downloads", "direction": -1}))
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT,
                                               "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return [{"id": d.get("id"), "downloads": d.get("downloads"),
                 "likes": d.get("likes")} for d in data]
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, json.JSONDecodeError):
        return []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="WSTU catalog discovery + logging")
    parser.add_argument("--query", action="append", default=None,
                        help="extra single query (repeatable)")
    parser.add_argument("--limit", type=int, default=15)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args(argv)

    log = {"generated_by": "scripts/discovery/discover_catalogs.py",
           "catalog": "Hugging Face Datasets API (/api/datasets?search=...)",
           "queries": {}}
    if LOG_PATH.exists():
        try:
            log = json.loads(LOG_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    log["queries"] = log.get("queries", {})

    if args.offline:
        total = sum(len(v.get("results", [])) for v in log["queries"].values())
        print(f"[discover] offline: {len(log['queries'])} cached queries, {total} cached results")
        return 0

    plan: list[tuple[str, str]] = []
    for group, queries in QUERIES.items():
        plan.extend((group, q) for q in queries)
    if args.query:
        plan.extend(("custom", q) for q in args.query)

    log["checked_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    for i, (group, q) in enumerate(plan, 1):
        results = query_hf(q, args.limit)
        log["queries"][f"{group}::{q}"] = {
            "group": group, "query": q, "result_count": len(results), "results": results}
        print(f"  [{i}/{len(plan)}] {group}::{q} -> {len(results)} hits")
        time.sleep(0.1)

    LOG_PATH.write_text(json.dumps(log, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    total = sum(v["result_count"] for v in log["queries"].values())
    print(f"[discover] wrote {LOG_PATH.relative_to(REPO_ROOT)} "
          f"({len(log['queries'])} queries, {total} raw hits)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())