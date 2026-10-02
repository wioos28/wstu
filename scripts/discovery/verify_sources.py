#!/usr/bin/env python3
"""WSTU Dataset - Phase 1/2: SOURCE VERIFICATION.

Verifies every discovery candidate against its *primary* source before anything is
registered as usable. This module NEVER invents metadata: an unverifiable field is
recorded as null / "unknown", never guessed.

What it verifies:
  1. Hugging Face datasets -> https://huggingface.co/api/datasets/<id>
     extracts: license, languages, size_categories, task_categories, sha (revision),
               gated flag, downloads.
  2. Every declared URL (official_url / github_url / paper_url / license_url / reference url)
     -> HTTP reachability probe with recorded status code.

Output (evidence layer, never edited by hand):
  metadata/verification/hf_verification.json
  metadata/verification/url_verification.json

Usage:
    python3 scripts/discovery/verify_sources.py                 # verify all candidates
    python3 scripts/discovery/verify_sources.py --only aya_dataset gsm8k
    python3 scripts/discovery/verify_sources.py --offline       # rebuild from cache only
"""
from __future__ import annotations

import argparse
import json
import socket
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DISCOVERY_DIR = REPO_ROOT / "metadata" / "discovery"
VERIFY_DIR = REPO_ROOT / "metadata" / "verification"

HF_API = "https://huggingface.co/api/datasets/{dataset_id}"
USER_AGENT = "wstu-dataset-discovery/0.1 (+https://github.com/wioos28/wstu)"
TIMEOUT = 25
RETRIES = 2


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _request(url: str, method: str = "GET") -> tuple[int | None, str | None]:
    """Probe a URL. Returns (http_status, error). status None means transport failure."""
    req = urllib.request.Request(url, method=method, headers={"User-Agent": USER_AGENT})
    last_err = None
    for attempt in range(RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                return resp.status, None
        except urllib.error.HTTPError as exc:
            return exc.code, f"HTTPError {exc.code}"
        except (urllib.error.URLError, socket.timeout, TimeoutError, OSError) as exc:
            last_err = f"{type(exc).__name__}: {exc}"
            if attempt < RETRIES:
                time.sleep(1.5 * (attempt + 1))
    return None, last_err


def _get_json(url: str) -> tuple[int | None, dict | None, str | None]:
    req = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8")), None
    except urllib.error.HTTPError as exc:
        return exc.code, None, f"HTTPError {exc.code}"
    except (urllib.error.URLError, socket.timeout, TimeoutError, OSError,
            json.JSONDecodeError) as exc:
        return None, None, f"{type(exc).__name__}: {exc}"


def _as_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value]
    return [str(value)]


def load_candidates() -> list[dict]:
    """Merge every metadata/discovery/cand_*.json into one candidate list."""
    candidates: list[dict] = []
    seen: set[str] = set()
    for path in sorted(DISCOVERY_DIR.glob("cand_*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for cand in data.get("candidates", []):
            cid = cand["id"]
            if cid in seen:
                raise ValueError(f"duplicate candidate id {cid!r} (in {path.name})")
            seen.add(cid)
            cand["_group_file"] = path.name
            candidates.append(cand)
    return candidates


def load_reference_resources() -> list[dict]:
    path = DISCOVERY_DIR / "source_catalog.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("reference_resources", [])


def verify_hf(cand: dict) -> dict:
    """Verify one Hugging Face dataset id against the HF API."""
    hf_id = cand.get("hf_id")
    record = {
        "id": cand["id"],
        "hf_id": hf_id,
        "verified": False,
        "http_status": None,
        "error": None,
        "license": None,
        "license_source": None,
        "languages": [],
        "size_categories": [],
        "task_categories": [],
        "revision": None,
        "gated": None,
        "private": None,
        "downloads": None,
        "last_modified": None,
        "card_tags": [],
        "checked_at": _now(),
        "api_url": None,
    }
    if not hf_id:
        record["error"] = "no hf_id declared (non-HF candidate)"
        return record

    api_url = HF_API.format(dataset_id=hf_id)
    record["api_url"] = api_url
    status, payload, err = _get_json(api_url)
    record["http_status"] = status
    if payload is None:
        record["error"] = err or "no payload"
        return record

    card = payload.get("cardData") or {}
    tags = _as_list(payload.get("tags"))
    # license may live in cardData.license or in the tag list ("license:mit").
    license_value = card.get("license")
    source = "cardData.license" if license_value else None
    if not license_value:
        for tag in tags:
            if tag.startswith("license:"):
                license_value = tag.split(":", 1)[1]
                source = "tags[license:*]"
                break
    if not license_value:
        license_value = "unknown"

    record.update({
        "verified": True,
        "license": license_value if isinstance(license_value, str) else _as_list(license_value),
        "license_source": source,
        "languages": _as_list(card.get("language")) or [
            t.split(":", 1)[1] for t in tags if t.startswith("language:")
        ],
        "size_categories": _as_list(card.get("size_categories")),
        "task_categories": _as_list(card.get("task_categories")) or [
            t.split(":", 1)[1] for t in tags if t.startswith("task_categories:")
        ],
        "revision": payload.get("sha"),
        "gated": payload.get("gated"),
        "private": payload.get("private"),
        "downloads": payload.get("downloads"),
        "last_modified": payload.get("lastModified"),
        "card_tags": tags,
    })
    return record


def verify_urls(candidates: list[dict], references: list[dict]) -> dict:
    """Probe every declared URL for reachability. Records status; never fabricates."""
    url_fields = ("official_url", "github_url", "paper_url", "license_url")
    records: dict[str, dict] = {}

    def probe(url) -> dict:
        if not url or url == "null":
            return {"declared": False}
        if url in records:
            return records[url]
        status, err = _request(url, method="GET")
        entry = {
            "declared": True,
            "http_status": status,
            "reachable": bool(status is not None and 200 <= status < 400),
            "error": err,
            "checked_at": _now(),
        }
        records[url] = entry
        return entry

    by_candidate = {
        cand["id"]: {f: probe(cand.get(f)) for f in url_fields}
        for cand in candidates
    }
    by_reference = {ref["id"]: probe(ref.get("url")) for ref in references}
    return {"by_candidate": by_candidate, "by_reference": by_reference}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="WSTU dataset source verification")
    parser.add_argument("--only", nargs="*", default=None, help="verify only these candidate ids")
    parser.add_argument("--offline", action="store_true", help="do not hit the network; reuse cache")
    parser.add_argument("--sleep", type=float, default=0.0, help="delay between HF API calls")
    args = parser.parse_args(argv)

    VERIFY_DIR.mkdir(parents=True, exist_ok=True)
    hf_cache_path = VERIFY_DIR / "hf_verification.json"
    url_path = VERIFY_DIR / "url_verification.json"

    candidates = load_candidates()
    references = load_reference_resources()
    if args.only:
        wanted = set(args.only)
        candidates = [c for c in candidates if c["id"] in wanted]
        if not candidates:
            print(f"[error] --only matched no candidate ids: {sorted(wanted)}", file=sys.stderr)
            return 2

    cache: dict = {}
    if hf_cache_path.exists():
        cache = json.loads(hf_cache_path.read_text(encoding="utf-8"))
    results: dict[str, dict] = dict(cache.get("datasets", {}))

    print(f"[verify] {len(candidates)} candidates ({len(references)} reference resources)")
    for i, cand in enumerate(candidates, 1):
        cid = cand["id"]
        if args.offline:
            if cid not in results:
                print(f"  [{i}/{len(candidates)}] {cid}: no cache entry (offline)")
            continue
        results[cid] = verify_hf(cand)
        rec = results[cid]
        state = "OK" if rec["verified"] else "FAIL"
        print(f"  [{i}/{len(candidates)}] {cid}: {state} "
              f"license={rec['license']} langs={len(rec['languages'])} status={rec['http_status']}")
        if args.sleep:
            time.sleep(args.sleep)

    hf_cache_path.write_text(json.dumps({
        "generated_by": "scripts/discovery/verify_sources.py",
        "checked_at": _now(),
        "note": "Machine verification evidence for Hugging Face datasets. Fields are copied "
                "verbatim from the Hugging Face API; nothing is inferred or invented.",
        "datasets": results,
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[verify] wrote {hf_cache_path.relative_to(REPO_ROOT)} ({len(results)} datasets)")

    if not args.offline:
        url_results = verify_urls(candidates, references)
        url_path.write_text(json.dumps({
            "generated_by": "scripts/discovery/verify_sources.py",
            "checked_at": _now(),
            "note": "Reachability evidence for every declared URL. A URL that is not reachable "
                    "is treated as unverified and must not be used as an official link.",
            **url_results,
        }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        reachable = sum(1 for c in url_results["by_candidate"].values()
                        for e in c.values() if e.get("reachable"))
        print(f"[verify] wrote {url_path.relative_to(REPO_ROOT)} ({reachable} reachable declared URLs)")

    ok = sum(1 for r in results.values() if r["verified"])
    failed = sorted(cid for cid, r in results.items() if not r["verified"] and r.get("hf_id"))
    print(f"[verify] HF verified: {ok}/{len(results)}")
    if failed:
        print(f"[verify] NOT verified (needs id fix or manual check): {failed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())