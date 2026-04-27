#!/usr/bin/env python3
"""Run request-driven retrieval and synthesis benchmarks via OpenRouter.

This runner is intentionally self-contained: it uses only the Python standard
library, reads local JSONL datasets, asks models for JSON-only answers, and
writes raw responses plus compact summary reports.
"""

from __future__ import annotations

import argparse
import concurrent.futures as futures
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATASETS = ROOT / "datasets"
RESULTS = ROOT / "results"
RAW = RESULTS / "raw"

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_HEADERS = {
    "HTTP-Referer": "https://github.com/d-alexeev/proptech-news-monitoring",
    "X-Title": "PropTech News Monitoring Request Benchmarks",
}

BENCHMARK_DIRS = {
    "request-synthesis": "request-synthesis",
    "request-article-retrieval": "request-article-retrieval",
}


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open() as fh:
        for line in fh:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def extract_json(text: str) -> dict[str, Any]:
    if not text or not text.strip():
        raise ValueError("empty response")
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", stripped, re.DOTALL)
        if not match:
            raise ValueError(f"no JSON object found in {text[:200]!r}") from None
        parsed = json.loads(match.group(0))
    if not isinstance(parsed, dict):
        raise ValueError("top-level JSON value must be an object")
    return parsed


def normalize_models(raw: str) -> list[str]:
    return [part.strip() for part in raw.split(",") if part.strip()]


def safe_model_name(model: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "__", model)


def call_openrouter(
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
    max_tokens: int,
    timeout: float,
    retries: int,
) -> tuple[str, dict[str, Any], str]:
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
    }
    data = json.dumps(payload).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        **OPENROUTER_HEADERS,
    }
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        req = urllib.request.Request(OPENROUTER_URL, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            choice = body.get("choices", [{}])[0]
            content = (choice.get("message") or {}).get("content") or ""
            finish_reason = choice.get("finish_reason") or ""
            usage = body.get("usage") or {}
            if not content.strip() and attempt < retries:
                time.sleep(1.5 * (attempt + 1))
                continue
            return content, usage, finish_reason
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            last_error = RuntimeError(f"HTTP {exc.code}: {body[:500]}")
        except Exception as exc:  # noqa: BLE001 - CLI should retain remote failure context.
            last_error = exc
        if attempt < retries:
            time.sleep(1.5 * (attempt + 1))
    assert last_error is not None
    raise last_error


def build_synthesis_messages(case: dict[str, Any]) -> list[dict[str, str]]:
    article_lines = []
    for article in case["articles"]:
        article_lines.append(
            "\n".join(
                [
                    f"ARTICLE_ID: {article['article_id']}",
                    f"TITLE: {article['title']}",
                    f"PUBLISHED: {article.get('published') or 'unknown'}",
                    f"URL: {article['normalized_url']}",
                    "FULL_TEXT:",
                    article["body_full_text"],
                ]
            )
        )
    system = (
        "You are evaluating international proptech evidence for Avito Real Estate. "
        "Use only the supplied articles. Return only valid JSON. Do not use markdown."
    )
    article_block = "\n\n---\n\n".join(article_lines)
    user = f"""User request:
{case["user_request"]}

Articles:
{article_block}

Return JSON with exactly these top-level fields:
{{
  "case_id": "{case["id"]}",
  "answer_summary": "short direct answer",
  "theses": [
    {{"statement": "...", "evidence_article_ids": ["art_..."], "strength": "strong|moderate|weak", "reasoning": "..."}}
  ],
  "risks": [
    {{"statement": "...", "evidence_article_ids": ["art_..."], "reasoning": "..."}}
  ],
  "avito_implications": [
    {{"statement": "...", "evidence_article_ids": ["art_..."], "reasoning": "..."}}
  ],
  "caveats": ["..."]
}}
"""
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def build_retrieval_messages(case: dict[str, Any]) -> list[dict[str, str]]:
    article_lines = []
    for article in case["corpus"]:
        article_lines.append(
            "\n".join(
                [
                    f"ARTICLE_ID: {article['article_id']}",
                    f"TITLE: {article['title']}",
                    f"PUBLISHED: {article.get('published') or 'unknown'}",
                    f"URL: {article['normalized_url']}",
                    f"EXCERPT: {article['body_excerpt']}",
                ]
            )
        )
    system = (
        "You are a retrieval evaluator for Avito Real Estate monitoring. "
        "Select article IDs that are relevant to the user request. "
        "Favor recall for direct evidence, but avoid weak generic AI/real-estate matches. "
        "Return only valid JSON. Do not use markdown."
    )
    article_block = "\n\n---\n\n".join(article_lines)
    user = f"""User request:
{case["user_request"]}

Candidate articles:
{article_block}

Return JSON with exactly these top-level fields:
{{
  "case_id": "{case["id"]}",
  "article_ids": ["art_..."],
  "rationale": "brief selection rule"
}}
"""
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def parse_synthesis(parsed: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    required = ["case_id", "answer_summary", "theses", "risks", "avito_implications", "caveats"]
    missing = [field for field in required if field not in parsed]
    if missing:
        raise ValueError(f"missing required fields: {missing}")
    if parsed["case_id"] != case["id"]:
        raise ValueError(f"case_id mismatch: {parsed['case_id']!r}")
    for field in ["theses", "risks", "avito_implications", "caveats"]:
        if not isinstance(parsed[field], list):
            raise ValueError(f"{field} must be a list")
    valid_ids = {article["article_id"] for article in case["articles"]}
    used_ids: set[str] = set()
    for field in ["theses", "risks", "avito_implications"]:
        for item in parsed[field]:
            if not isinstance(item, dict):
                raise ValueError(f"{field} items must be objects")
            ids = item.get("evidence_article_ids")
            if not isinstance(ids, list) or not ids:
                raise ValueError(f"{field} item lacks evidence_article_ids")
            unknown = [article_id for article_id in ids if article_id not in valid_ids]
            if unknown:
                raise ValueError(f"{field} references unknown article IDs: {unknown}")
            used_ids.update(ids)
    return {
        "pred": parsed,
        "used_article_ids": sorted(used_ids),
    }


def parse_retrieval(parsed: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    if parsed.get("case_id") != case["id"]:
        raise ValueError(f"case_id mismatch: {parsed.get('case_id')!r}")
    article_ids = parsed.get("article_ids")
    if not isinstance(article_ids, list):
        raise ValueError("article_ids must be a list")
    valid_ids = {article["article_id"] for article in case["corpus"]}
    cleaned: list[str] = []
    for article_id in article_ids:
        if not isinstance(article_id, str):
            raise ValueError("article_ids must contain strings")
        if article_id not in valid_ids:
            raise ValueError(f"unknown article_id: {article_id}")
        if article_id not in cleaned:
            cleaned.append(article_id)
    return {
        "pred_article_ids": cleaned,
        "pred_rationale": parsed.get("rationale"),
    }


def run_cases(
    api_key: str | None,
    benchmark: str,
    model: str,
    cases: list[dict[str, Any]],
    concurrency: int,
    max_tokens: int,
    timeout: float,
    retries: int,
    dry_run: bool,
) -> list[dict[str, Any]]:
    build_messages = build_synthesis_messages if benchmark == "request-synthesis" else build_retrieval_messages
    parser = parse_synthesis if benchmark == "request-synthesis" else parse_retrieval
    rows: list[dict[str, Any] | None] = [None] * len(cases)

    def work(index: int, case: dict[str, Any]) -> dict[str, Any]:
        started = time.time()
        messages = build_messages(case)
        row: dict[str, Any] = {
            "id": case["id"],
            "model": model,
            "parse_ok": False,
            "dry_run": dry_run,
            "prompt_chars": sum(len(message["content"]) for message in messages),
        }
        try:
            if dry_run:
                if benchmark == "request-synthesis":
                    first_id = case["articles"][0]["article_id"]
                    content = json.dumps(
                        {
                            "case_id": case["id"],
                            "answer_summary": "dry run",
                            "theses": [
                                {
                                    "statement": "dry run",
                                    "evidence_article_ids": [first_id],
                                    "strength": "weak",
                                    "reasoning": "dry run",
                                }
                            ],
                            "risks": [
                                {
                                    "statement": "dry run",
                                    "evidence_article_ids": [first_id],
                                    "reasoning": "dry run",
                                }
                            ],
                            "avito_implications": [
                                {
                                    "statement": "dry run",
                                    "evidence_article_ids": [first_id],
                                    "reasoning": "dry run",
                                }
                            ],
                            "caveats": ["dry run"],
                        }
                    )
                else:
                    content = json.dumps(
                        {
                            "case_id": case["id"],
                            "article_ids": [case["corpus"][0]["article_id"]],
                            "rationale": "dry run",
                        }
                    )
                usage: dict[str, Any] = {}
                finish_reason = "dry_run"
            else:
                assert api_key is not None
                content, usage, finish_reason = call_openrouter(
                    api_key, model, messages, max_tokens=max_tokens, timeout=timeout, retries=retries
                )
            row["raw"] = content
            row["usage"] = usage
            row["finish_reason"] = finish_reason
            parsed = extract_json(content)
            row.update(parser(parsed, case))
            row["parse_ok"] = True
        except Exception as exc:  # noqa: BLE001 - report per-case benchmark failure.
            row["error"] = f"{type(exc).__name__}: {exc}"
        row["latency_s"] = round(time.time() - started, 2)
        return row

    with futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        pending = {executor.submit(work, idx, case): idx for idx, case in enumerate(cases)}
        for done_count, future in enumerate(futures.as_completed(pending), start=1):
            idx = pending[future]
            rows[idx] = future.result()
            if done_count == len(cases) or done_count % 5 == 0:
                print(f"  [{model}] {done_count}/{len(cases)}", flush=True)
    return [row for row in rows if row is not None]


def score_retrieval(rows: list[dict[str, Any]], golden: list[dict[str, Any]]) -> dict[str, Any]:
    by_id = {row["id"]: row for row in golden}
    cases: list[dict[str, Any]] = []
    recalls: list[float] = []
    precisions: list[float] = []
    failures = {"api_or_parse": 0, "critical_miss": 0}
    for row in rows:
        gold = by_id[row["id"]]
        if not row.get("parse_ok") or row.get("error"):
            failures["api_or_parse"] += 1
            cases.append({"id": row["id"], "status": "error", "error": row.get("error")})
            continue
        predicted = set(row["pred_article_ids"])
        must = set(gold.get("must_find", []))
        relevant = must | set(gold.get("nice_to_have", []))
        critical = set(gold.get("critical_miss_ids", []))
        recall = len(predicted & must) / len(must) if must else 1.0
        precision = len(predicted & relevant) / len(predicted) if predicted else 0.0
        critical_missing = sorted(critical - predicted)
        if critical_missing:
            failures["critical_miss"] += 1
        recalls.append(recall)
        precisions.append(precision)
        cases.append(
            {
                "id": row["id"],
                "status": "critical_miss" if critical_missing else "ok",
                "recall": round(recall, 4),
                "precision": round(precision, 4),
                "predicted_count": len(predicted),
                "critical_missing": critical_missing,
            }
        )
    avg_recall = sum(recalls) / len(recalls) if recalls else 0.0
    avg_precision = sum(precisions) / len(precisions) if precisions else 0.0
    return {
        "n_cases_total": len(rows),
        "n_scored": len(recalls),
        "avg_recall": round(avg_recall, 4),
        "avg_precision": round(avg_precision, 4),
        "n_api_or_parse_errors": failures["api_or_parse"],
        "n_critical_miss_cases": failures["critical_miss"],
        "cases": cases,
    }


def score_synthesis(rows: list[dict[str, Any]], golden: list[dict[str, Any]]) -> dict[str, Any]:
    by_id = {row["id"]: row for row in golden}
    cases: list[dict[str, Any]] = []
    thesis_scores: list[float] = []
    risk_scores: list[float] = []
    for row in rows:
        gold = by_id[row["id"]]
        if not row.get("parse_ok") or row.get("error"):
            cases.append({"id": row["id"], "status": "error", "error": row.get("error")})
            continue
        pred = row["pred"]
        thesis_evidence_sets = [set(item["evidence_article_ids"]) for item in pred["theses"]]
        risk_evidence_sets = [set(item["evidence_article_ids"]) for item in pred["risks"]]
        must_theses = [item for item in gold["expected_theses"] if item["priority"] == "must_cover"]
        covered_theses = []
        for item in must_theses:
            support = set(item["supporting_article_ids"])
            if any(support & pred_ids for pred_ids in thesis_evidence_sets):
                covered_theses.append(item["thesis_id"])
        covered_risks = []
        for item in gold["required_risks"]:
            support = set(item["supporting_article_ids"])
            if any(support & pred_ids for pred_ids in risk_evidence_sets):
                covered_risks.append(item["risk_id"])
        thesis_recall = len(covered_theses) / len(must_theses) if must_theses else 1.0
        risk_recall = len(covered_risks) / len(gold["required_risks"]) if gold["required_risks"] else 1.0
        thesis_scores.append(thesis_recall)
        risk_scores.append(risk_recall)
        cases.append(
            {
                "id": row["id"],
                "status": "ok",
                "thesis_recall_by_evidence_overlap": round(thesis_recall, 4),
                "risk_recall_by_evidence_overlap": round(risk_recall, 4),
                "covered_must_thesis_ids": covered_theses,
                "covered_risk_ids": covered_risks,
                "used_article_ids": row.get("used_article_ids", []),
            }
        )
    return {
        "n_cases_total": len(rows),
        "n_scored": len(thesis_scores),
        "avg_thesis_recall_by_evidence_overlap": round(sum(thesis_scores) / len(thesis_scores), 4) if thesis_scores else 0.0,
        "avg_risk_recall_by_evidence_overlap": round(sum(risk_scores) / len(risk_scores), 4) if risk_scores else 0.0,
        "n_api_or_parse_errors": len([case for case in cases if case["status"] == "error"]),
        "cases": cases,
        "scoring_warning": "Synthesis scoring is heuristic and checks schema plus evidence overlap; expert/LLM judge review is still required.",
    }


def write_markdown(report: dict[str, Any], path: Path) -> None:
    lines = [
        f"# {report['meta']['benchmark']} run {report['meta']['timestamp']}",
        "",
        f"Cases: {report['meta']['n_cases']} · Models: {len(report['models'])} · Concurrency: {report['meta']['concurrency']}",
        "",
        "| Model | Scored | Parse/API errors | Primary score | Cost |",
        "|---|---:|---:|---:|---:|",
    ]
    for item in report["models"]:
        scores = item["scores"]
        if report["meta"]["benchmark"] == "request-synthesis":
            primary = scores["avg_thesis_recall_by_evidence_overlap"]
        else:
            primary = scores["avg_recall"]
        lines.append(
            f"| `{item['model']}` | {scores['n_scored']} | {scores['n_api_or_parse_errors']} | "
            f"{primary:.3f} | ${item['total_cost_usd']:.5f} |"
        )
    lines.append("")
    lines.append("Raw responses are stored in the JSONL paths referenced by the JSON report.")
    path.write_text("\n".join(lines) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", required=False, choices=sorted(BENCHMARK_DIRS))
    parser.add_argument("--model", default=None, help="single model, comma-separated models, or all")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--max-tokens", type=int, default=4000)
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--list-models", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    load_env(ROOT.parent / ".env")
    load_env(ROOT / ".env")

    env_models = normalize_models(os.environ.get("LLM_MODEL", ""))
    if args.model and args.model != "all":
        models = normalize_models(args.model)
    else:
        models = env_models

    if args.list_models:
        for model in models:
            print(model)
        if not models:
            print("No models configured in LLM_MODEL or --model.", file=sys.stderr)
            return 2
        return 0

    if not args.benchmark:
        print("FATAL: --benchmark is required unless --list-models is used", file=sys.stderr)
        return 2
    if not models:
        print("FATAL: no models configured. Set LLM_MODEL in .env or pass --model.", file=sys.stderr)
        return 2

    api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not args.dry_run and not api_key:
        print("FATAL: OPENROUTER_API_KEY or OPENAI_API_KEY is required for non-dry-run execution.", file=sys.stderr)
        return 2

    dataset_dir = DATASETS / BENCHMARK_DIRS[args.benchmark]
    cases = load_jsonl(dataset_dir / "inputs.jsonl")
    golden = load_jsonl(dataset_dir / "golden.jsonl")
    if args.limit is not None:
        cases = cases[: args.limit]

    timestamp = dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    RAW.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        "meta": {
            "benchmark": args.benchmark,
            "timestamp": timestamp,
            "n_cases": len(cases),
            "concurrency": args.concurrency,
            "dry_run": args.dry_run,
        },
        "models": [],
    }
    scorer = score_synthesis if args.benchmark == "request-synthesis" else score_retrieval

    print(f"{args.benchmark}: {len(cases)} cases x {len(models)} models; concurrency={args.concurrency}")
    for model in models:
        print(f"\n-> model: {model}")
        started = time.time()
        rows = run_cases(
            api_key=api_key,
            benchmark=args.benchmark,
            model=model,
            cases=cases,
            concurrency=args.concurrency,
            max_tokens=args.max_tokens,
            timeout=args.timeout,
            retries=args.retries,
            dry_run=args.dry_run,
        )
        scores = scorer(rows, golden)
        elapsed = round(time.time() - started, 1)
        raw_path = RAW / f"{args.benchmark}-{safe_model_name(model)}-{timestamp}.jsonl"
        with raw_path.open("w") as fh:
            for row in rows:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        total_cost = sum((row.get("usage") or {}).get("cost") or 0 for row in rows)
        report["models"].append(
            {
                "model": model,
                "elapsed_s": elapsed,
                "total_cost_usd": round(total_cost, 5),
                "raw_path": str(raw_path.relative_to(ROOT)),
                "scores": scores,
            }
        )
        print(
            f"  done in {elapsed}s · scored={scores['n_scored']} "
            f"errors={scores['n_api_or_parse_errors']} cost=${total_cost:.5f}"
        )

    report_path = RESULTS / f"{args.benchmark}-{timestamp}.json"
    markdown_path = RESULTS / f"{args.benchmark}-{timestamp}.md"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    write_markdown(report, markdown_path)
    print(f"\nReport: {report_path.relative_to(ROOT)}")
    print(f"Summary: {markdown_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
