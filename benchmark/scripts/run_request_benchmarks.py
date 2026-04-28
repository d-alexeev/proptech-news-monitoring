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
import hashlib
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
    "request-article-synthesis": "request-article-synthesis",
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


def build_article_synthesis_messages(case: dict[str, Any]) -> list[dict[str, str]]:
    article_lines = []
    for article in case["articles"]:
        article_lines.append(
            "\n".join(
                [
                    f"ARTICLE_ID: {article['article_id']}",
                    f"TITLE: {article['title']}",
                    f"PUBLISHED: {article.get('published') or 'unknown'}",
                    f"URL: {article['normalized_url']}",
                    "EXCERPT:",
                    article["body_excerpt"],
                    "FULL_TEXT:",
                    article["body_full_text"],
                ]
            )
        )
    system = (
        "You write request-specific per-article summaries for Avito Real Estate. "
        "Use only the supplied articles. Return exactly one summary for every article. "
        "Label irrelevant or distractor articles explicitly instead of forcing them into evidence. "
        "Return only valid JSON. Do not use markdown."
    )
    article_block = "\n\n---\n\n".join(article_lines)
    user = f"""User request:
{case["user_request"]}

Articles:
{article_block}

Return JSON with exactly these top-level fields:
{{
  "case_id": "{case["id"]}",
  "article_summaries": [
    {{
      "article_id": "art_...",
      "relevance": "high|medium|low|irrelevant",
      "support_type": "direct_evidence|analogue|risk|background|distractor",
      "request_specific_summary": "what this article contributes to the Avito ND request",
      "theses": [
        {{"statement": "...", "supports": "confirms|weakens|nuances|risk|background", "evidence": "short grounded evidence note"}}
      ],
      "avito_implication": "concrete implication, or why there is no useful implication",
      "caveats": ["..."]
    }}
  ]
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


def parse_article_synthesis(parsed: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    if parsed.get("case_id") != case["id"]:
        raise ValueError(f"case_id mismatch: {parsed.get('case_id')!r}")
    summaries = parsed.get("article_summaries")
    if not isinstance(summaries, list):
        raise ValueError("article_summaries must be a list")
    valid_ids = {article["article_id"] for article in case["articles"]}
    seen: set[str] = set()
    valid_relevance = {"high", "medium", "low", "irrelevant"}
    valid_support = {"direct_evidence", "analogue", "risk", "background", "distractor"}
    valid_thesis_support = {"confirms", "weakens", "nuances", "risk", "background"}
    for item in summaries:
        if not isinstance(item, dict):
            raise ValueError("article_summaries items must be objects")
        article_id = item.get("article_id")
        if article_id not in valid_ids:
            raise ValueError(f"unknown article_id: {article_id!r}")
        if article_id in seen:
            raise ValueError(f"duplicate article_id: {article_id}")
        seen.add(article_id)
        if item.get("relevance") not in valid_relevance:
            raise ValueError(f"invalid relevance for {article_id}: {item.get('relevance')!r}")
        if item.get("support_type") not in valid_support:
            raise ValueError(f"invalid support_type for {article_id}: {item.get('support_type')!r}")
        for field in ["request_specific_summary", "avito_implication"]:
            if not isinstance(item.get(field), str) or not item[field].strip():
                raise ValueError(f"{field} is required for {article_id}")
        if not isinstance(item.get("caveats"), list):
            raise ValueError(f"caveats must be a list for {article_id}")
        theses = item.get("theses")
        if not isinstance(theses, list):
            raise ValueError(f"theses must be a list for {article_id}")
        for thesis in theses:
            if not isinstance(thesis, dict):
                raise ValueError(f"theses items must be objects for {article_id}")
            if thesis.get("supports") not in valid_thesis_support:
                raise ValueError(f"invalid thesis supports for {article_id}: {thesis.get('supports')!r}")
            for field in ["statement", "evidence"]:
                if not isinstance(thesis.get(field), str) or not thesis[field].strip():
                    raise ValueError(f"thesis.{field} is required for {article_id}")
    missing = sorted(valid_ids - seen)
    if missing:
        raise ValueError(f"missing article_summaries for: {missing}")
    return {
        "pred": parsed,
        "pred_article_summary_count": len(summaries),
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
    builders = {
        "request-synthesis": build_synthesis_messages,
        "request-article-retrieval": build_retrieval_messages,
        "request-article-synthesis": build_article_synthesis_messages,
    }
    parsers = {
        "request-synthesis": parse_synthesis,
        "request-article-retrieval": parse_retrieval,
        "request-article-synthesis": parse_article_synthesis,
    }
    build_messages = builders[benchmark]
    parser = parsers[benchmark]
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
                elif benchmark == "request-article-retrieval":
                    content = json.dumps(
                        {
                            "case_id": case["id"],
                            "article_ids": [case["corpus"][0]["article_id"]],
                            "rationale": "dry run",
                        }
                    )
                else:
                    content = json.dumps(
                        {
                            "case_id": case["id"],
                            "article_summaries": [
                                {
                                    "article_id": article["article_id"],
                                    "relevance": "low",
                                    "support_type": "background",
                                    "request_specific_summary": "dry run",
                                    "theses": [],
                                    "avito_implication": "dry run",
                                    "caveats": ["dry run"],
                                }
                                for article in case["articles"]
                            ],
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


def score_article_synthesis_schema(rows: list[dict[str, Any]], golden: list[dict[str, Any]]) -> dict[str, Any]:
    gold_by_id = {row["id"]: row for row in golden}
    cases: list[dict[str, Any]] = []
    relevance_correct = 0
    relevance_total = 0
    must_points_covered = 0
    must_points_total = 0
    high_relevance_distractors = 0
    forbidden_claim_hits: list[dict[str, str]] = []
    scored = 0
    for row in rows:
        if not row.get("parse_ok") or row.get("error"):
            cases.append({"id": row["id"], "status": "error", "error": row.get("error")})
            continue
        gold = gold_by_id[row["id"]]
        gold_labels = {item["article_id"]: item for item in gold["article_labels"]}
        pred_labels = {item["article_id"]: item for item in row["pred"]["article_summaries"]}
        case_must_total = 0
        case_must_covered = 0
        case_relevance_correct = 0
        article_results = []
        for article_id, gold_item in gold_labels.items():
            pred_item = pred_labels[article_id]
            relevance_total += 1
            relevance_match = pred_item["relevance"] == gold_item["relevance"]
            if relevance_match:
                relevance_correct += 1
                case_relevance_correct += 1
            pred_text = article_prediction_text(pred_item)
            covered_points = []
            for point in gold_item.get("must_cover_points", []):
                must_points_total += 1
                case_must_total += 1
                if text_overlap(point["statement"], pred_text) >= 0.22:
                    must_points_covered += 1
                    case_must_covered += 1
                    covered_points.append(point["point_id"])
            if gold_item["article_role"] == "distractor" and pred_item["relevance"] == "high":
                high_relevance_distractors += 1
            article_forbidden_hits = []
            for claim in gold_item.get("must_not_claim", []):
                if normalized_contains_or_overlap(claim, pred_text):
                    hit = {"case_id": row["id"], "article_id": article_id, "claim": claim}
                    forbidden_claim_hits.append(hit)
                    article_forbidden_hits.append(claim)
            article_results.append(
                {
                    "article_id": article_id,
                    "gold_relevance": gold_item["relevance"],
                    "pred_relevance": pred_item["relevance"],
                    "relevance_match": relevance_match,
                    "covered_must_point_ids": covered_points,
                    "must_point_count": len(gold_item.get("must_cover_points", [])),
                    "forbidden_claim_hits": article_forbidden_hits,
                }
            )
        scored += 1
        cases.append(
            {
                "id": row["id"],
                "status": "ok",
                "article_summary_count": row.get("pred_article_summary_count"),
                "relevance_accuracy": round(case_relevance_correct / len(gold_labels), 4) if gold_labels else 0.0,
                "must_point_recall": round(case_must_covered / case_must_total, 4) if case_must_total else 1.0,
                "articles": article_results,
            }
        )
    relevance_accuracy = relevance_correct / relevance_total if relevance_total else 0.0
    must_point_recall = must_points_covered / must_points_total if must_points_total else 0.0
    return {
        "n_cases_total": len(rows),
        "n_scored": scored,
        "schema_valid_rate": round(scored / len(rows), 4) if rows else 0.0,
        "article_relevance_accuracy": round(relevance_accuracy, 4),
        "must_point_recall": round(must_point_recall, 4),
        "high_relevance_distractors": high_relevance_distractors,
        "forbidden_claim_hit_count": len(forbidden_claim_hits),
        "forbidden_claim_hits": forbidden_claim_hits,
        "n_api_or_parse_errors": len(rows) - scored,
        "cases": cases,
        "scoring_warning": "Article synthesis scoring is deterministic v1; semantic quality still requires expert or LLM judge review.",
    }


def article_prediction_text(item: dict[str, Any]) -> str:
    parts = [
        item.get("request_specific_summary", ""),
        item.get("avito_implication", ""),
        " ".join(item.get("caveats", [])),
    ]
    for thesis in item.get("theses", []):
        parts.extend([thesis.get("statement", ""), thesis.get("evidence", "")])
    return " ".join(parts)


def tokenize(text: str) -> set[str]:
    stop = {
        "the", "and", "for", "that", "with", "this", "from", "into", "can", "not",
        "или", "для", "что", "это", "как", "and", "are", "but", "should", "article",
    }
    return {token for token in re.findall(r"[A-Za-zА-Яа-я0-9]+", text.lower()) if len(token) > 3 and token not in stop}


def text_overlap(expected: str, actual: str) -> float:
    expected_tokens = tokenize(expected)
    if not expected_tokens:
        return 0.0
    return len(expected_tokens & tokenize(actual)) / len(expected_tokens)


def normalized_contains_or_overlap(claim: str, actual: str) -> bool:
    normalized_claim = " ".join(re.findall(r"[A-Za-zА-Яа-я0-9]+", claim.lower()))
    normalized_actual = " ".join(re.findall(r"[A-Za-zА-Яа-я0-9]+", actual.lower()))
    return normalized_claim in normalized_actual or text_overlap(claim, actual) >= 0.72


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
        elif report["meta"]["benchmark"] == "request-article-synthesis":
            primary = scores["must_point_recall"]
        else:
            primary = scores["avg_recall"]
        lines.append(
            f"| `{item['model']}` | {scores['n_scored']} | {scores['n_api_or_parse_errors']} | "
            f"{primary:.3f} | ${item['total_cost_usd']:.5f} |"
        )
    lines.append("")
    lines.append("Raw responses are stored in the JSONL paths referenced by the JSON report.")
    path.write_text("\n".join(lines) + "\n")


def resolve_existing_path(path_text: str, base_dir: Path = ROOT) -> Path:
    path = Path(path_text)
    candidates = [path] if path.is_absolute() else [Path.cwd() / path, base_dir / path]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"path not found: {path_text}")


def resolve_report_child_path(path_text: str, report_path: Path) -> Path:
    path = Path(path_text)
    candidates = [path] if path.is_absolute() else [ROOT / path, report_path.parent / path]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"referenced raw file not found: {path_text}")


def load_judge_source_candidates(source_report_path: Path) -> dict[str, Any]:
    report = json.loads(source_report_path.read_text())
    meta = report.get("meta") or {}
    benchmark = meta.get("benchmark")
    if benchmark not in {"request-synthesis", "request-article-synthesis"}:
        raise ValueError(f"judge source benchmark is not supported: {benchmark!r}")
    candidates: list[dict[str, Any]] = []
    status_counts: dict[str, int] = {}
    for model_item in report.get("models", []):
        raw_path_text = model_item.get("raw_path")
        if not raw_path_text:
            raise ValueError(f"model item lacks raw_path: {model_item.get('model')!r}")
        raw_path = resolve_report_child_path(raw_path_text, source_report_path)
        rows = load_jsonl(raw_path)
        for row in rows:
            candidate = normalize_judge_candidate(benchmark, row)
            candidate.update(
                {
                    "benchmark": benchmark,
                    "candidate_model": model_item.get("model") or row.get("model"),
                    "source_report": str(source_report_path.relative_to(Path.cwd()))
                    if source_report_path.is_relative_to(Path.cwd())
                    else str(source_report_path),
                    "source_raw_path": str(raw_path.relative_to(Path.cwd()))
                    if raw_path.is_relative_to(Path.cwd())
                    else str(raw_path),
                    "source_run_id": meta.get("timestamp"),
                    "deterministic_scores": model_item.get("scores"),
                }
            )
            candidates.append(candidate)
            status = candidate["candidate_status"]
            status_counts[status] = status_counts.get(status, 0) + 1
    return {
        "benchmark": benchmark,
        "source_report": str(source_report_path),
        "source_run_id": meta.get("timestamp"),
        "n_candidates": len(candidates),
        "status_counts": status_counts,
        "candidates": candidates,
    }


def normalize_judge_candidate(benchmark: str, row: dict[str, Any]) -> dict[str, Any]:
    candidate: dict[str, Any] = {
        "case_id": row.get("id"),
        "parse_ok": bool(row.get("parse_ok")),
        "error": row.get("error"),
        "candidate_status": "judgeable",
        "candidate_output": row.get("pred"),
    }
    if row.get("parse_ok") and not row.get("error"):
        return candidate
    raw_text = row.get("raw") or ""
    error_text = row.get("error") or ""
    if benchmark == "request-article-synthesis" and "invalid thesis supports" in error_text and "analogue" in error_text:
        try:
            parsed = extract_json(raw_text)
        except Exception:  # noqa: BLE001 - candidate remains blocked but original error is retained.
            candidate["candidate_status"] = "candidate_schema_error_blocked"
            return candidate
        if parsed.get("case_id") == row.get("id") and isinstance(parsed.get("article_summaries"), list):
            candidate["candidate_status"] = "candidate_schema_error_judgeable"
            candidate["candidate_output"] = parsed
            candidate["schema_issue"] = "thesis.supports=analogue"
            return candidate
    if raw_text.strip():
        candidate["candidate_status"] = "candidate_schema_error_blocked"
    else:
        candidate["candidate_status"] = "candidate_parse_error"
    candidate["candidate_output"] = None
    return candidate


def print_judge_source_summary(summary: dict[str, Any]) -> None:
    print(
        f"judge source: {summary['benchmark']} report={summary['source_report']} "
        f"candidates={summary['n_candidates']}"
    )
    for status, count in sorted(summary["status_counts"].items()):
        print(f"  {status}: {count}")
    for candidate in summary["candidates"]:
        print(
            f"  - {candidate['candidate_model']} / {candidate['case_id']}: "
            f"{candidate['candidate_status']}"
        )


def run_judge_source_mode(args: argparse.Namespace, models: list[str]) -> int:
    try:
        source_report_path = resolve_existing_path(args.judge_source_report)
        summary = load_judge_source_candidates(source_report_path)
        if args.benchmark and args.benchmark != summary["benchmark"]:
            print(
                f"FATAL: --benchmark {args.benchmark!r} does not match source report "
                f"benchmark {summary['benchmark']!r}",
                file=sys.stderr,
            )
            return 2
        if not args.dry_run:
            print_judge_source_summary(summary)
            print("Judge execution is not implemented in this milestone; use --dry-run for prompt reporting.")
            return 0
        judge_models = models or ["dry/judge"]
        report_path, markdown_path = write_judge_prompt_dry_run(summary, judge_models, args.judge_context_mode)
        print_judge_source_summary(summary)
        print(f"Judge prompt dry-run report: {report_path.relative_to(ROOT)}")
        print(f"Judge prompt dry-run summary: {markdown_path.relative_to(ROOT)}")
        return 0
    except Exception as exc:  # noqa: BLE001 - CLI should report source artifact issues clearly.
        print(f"FATAL: {exc}", file=sys.stderr)
        return 2


def run_judge_calibration_dry_run(args: argparse.Namespace) -> int:
    if not args.benchmark:
        print("FATAL: --benchmark is required for --judge-calibration-dry-run", file=sys.stderr)
        return 2
    if args.benchmark not in {"request-synthesis", "request-article-synthesis"}:
        print(f"FATAL: benchmark does not support judge calibration: {args.benchmark}", file=sys.stderr)
        return 2
    try:
        report_path, markdown_path = write_judge_calibration_dry_run(args.benchmark)
        print(f"Judge calibration dry-run report: {report_path.relative_to(ROOT)}")
        print(f"Judge calibration dry-run summary: {markdown_path.relative_to(ROOT)}")
        return 0
    except Exception as exc:  # noqa: BLE001 - CLI should report calibration artifact issues clearly.
        print(f"FATAL: {exc}", file=sys.stderr)
        return 2


def write_judge_calibration_dry_run(benchmark: str) -> tuple[Path, Path]:
    dataset_dir = DATASETS / BENCHMARK_DIRS[benchmark]
    schema = json.loads((dataset_dir / "judge_schema.json").read_text())
    calibration = json.loads((dataset_dir / "judge_calibration.json").read_text())
    inputs = load_jsonl(dataset_dir / "inputs.jsonl")
    valid_article_ids = {article["article_id"] for case in inputs for article in case["articles"]}
    timestamp = dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    RESULTS.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    agreements = 0
    for example in calibration["examples"]:
        judge_output = calibration_example_to_judge_output(example, calibration, schema)
        parsed = parse_judge_output(judge_output, schema, valid_article_ids, calibration["case_id"])
        expected = example["expected_result"]
        actual = parsed["judge"]["final_recommendation"]
        expected_recommendation = "pass" if expected == "pass" else "fail"
        agreement = actual == expected_recommendation
        if agreement:
            agreements += 1
        rows.append(
            {
                "calibration_id": example["calibration_id"],
                "expected_result": expected,
                "actual_recommendation": actual,
                "agreement": agreement,
                "overall_score": parsed["overall_score"],
                "expected_failure_modes": example.get("expected_failure_modes", []),
            }
        )
    report = {
        "meta": {
            "type": "llm_judge_calibration_dry_run",
            "benchmark": benchmark,
            "timestamp": timestamp,
            "case_id": calibration["case_id"],
            "schema_version": schema["schema_version"],
            "calibration_schema_version": calibration["schema_version"],
            "dry_run": True,
        },
        "agreement_rate": round(agreements / len(rows), 4) if rows else 0.0,
        "examples": rows,
    }
    report_path = RESULTS / f"llm-judge-calibration-dry-run-{benchmark}-{timestamp}.json"
    markdown_path = RESULTS / f"llm-judge-calibration-dry-run-{benchmark}-{timestamp}.md"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    write_judge_calibration_dry_run_markdown(report, markdown_path)
    return report_path, markdown_path


def calibration_example_to_judge_output(
    example: dict[str, Any],
    calibration: dict[str, Any],
    schema: dict[str, Any],
) -> dict[str, Any]:
    scores = example["expected_dimension_scores"]
    overall_score = sum(item["score"] for item in scores) / len(scores) if scores else 0.0
    final_recommendation = "pass" if example["expected_result"] == "pass" else "fail"
    output: dict[str, Any] = {
        "benchmark_id": calibration["benchmark_id"],
        "case_id": calibration["case_id"],
        "candidate_model": f"calibration/{example['calibration_id']}",
        "judge_model": "dry/calibration-judge",
        "judge_context_mode": "hybrid",
        "source_report": "benchmark/datasets/calibration",
        "source_raw_path": "benchmark/datasets/calibration",
        "source_run_id": example["calibration_id"],
        "judge_schema_version": schema["schema_version"],
        "judge_prompt_hash": "sha256:calibration",
        "self_judged": False,
        "candidate_status": example["candidate_status"],
        "dimension_scores": [
            {
                "dimension": item["dimension"],
                "score": item["score"],
                "confidence": "medium",
                "rationale": item["rationale"],
                "cited_article_ids": example["referenced_article_ids"],
                "disagreement_flags": example.get("expected_failure_modes", []),
            }
            for item in scores
        ],
        "blocking_failures": [],
        "overall_score": round(overall_score, 4),
        "final_recommendation": final_recommendation,
        "summary": example["purpose"],
    }
    if "per_article_reviews" in schema["required_output_fields"]:
        output["per_article_reviews"] = [
            {
                "article_id": article_id,
                "relevance_score": 3,
                "coverage_score": 3,
                "overstatement_risk": "medium" if example["expected_result"] == "fail" else "low",
                "rationale": f"Calibration article review for {example['calibration_id']}.",
            }
            for article_id in example["referenced_article_ids"]
        ]
    return output

def write_judge_calibration_dry_run_markdown(report: dict[str, Any], path: Path) -> None:
    lines = [
        f"# LLM judge calibration dry run {report['meta']['timestamp']}",
        "",
        f"Benchmark: `{report['meta']['benchmark']}`",
        f"Case: `{report['meta']['case_id']}`",
        f"Agreement rate: {report['agreement_rate']:.3f}",
        "",
        "| Calibration example | Expected | Actual | Agreement | Score |",
        "|---|---|---|---:|---:|",
    ]
    for item in report["examples"]:
        lines.append(
            f"| `{item['calibration_id']}` | `{item['expected_result']}` | "
            f"`{item['actual_recommendation']}` | {str(item['agreement']).lower()} | "
            f"{item['overall_score']:.3f} |"
        )
    path.write_text("\n".join(lines) + "\n")


def write_judge_prompt_dry_run(
    source_summary: dict[str, Any],
    judge_models: list[str],
    context_mode: str,
) -> tuple[Path, Path]:
    benchmark = source_summary["benchmark"]
    dataset_dir = DATASETS / BENCHMARK_DIRS[benchmark]
    inputs = {row["id"]: row for row in load_jsonl(dataset_dir / "inputs.jsonl")}
    golden = {row["id"]: row for row in load_jsonl(dataset_dir / "golden.jsonl")}
    schema = json.loads((dataset_dir / "judge_schema.json").read_text())
    prompt_spec = json.loads((dataset_dir / "judge_prompt_spec.json").read_text())
    timestamp = dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    RESULTS.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        "meta": {
            "type": "llm_judge_prompt_dry_run",
            "benchmark": benchmark,
            "timestamp": timestamp,
            "source_report": source_summary["source_report"],
            "source_run_id": source_summary["source_run_id"],
            "judge_context_mode": context_mode,
            "judge_models": judge_models,
            "dry_run": True,
        },
        "candidates": [],
    }
    for judge_model in judge_models:
        for candidate in source_summary["candidates"]:
            item = {
                "case_id": candidate["case_id"],
                "candidate_model": candidate["candidate_model"],
                "judge_model": judge_model,
                "candidate_status": candidate["candidate_status"],
                "source_raw_path": candidate["source_raw_path"],
                "deterministic_scores": candidate.get("deterministic_scores"),
                "self_judged": candidate["candidate_model"] == judge_model,
            }
            if candidate["candidate_status"] in {"judgeable", "candidate_schema_error_judgeable"}:
                messages = build_judge_messages(
                    benchmark=benchmark,
                    candidate=candidate,
                    case=inputs[candidate["case_id"]],
                    gold=golden[candidate["case_id"]],
                    schema=schema,
                    prompt_spec=prompt_spec,
                    judge_model=judge_model,
                    context_mode=context_mode,
                )
                prompt_json = json.dumps(messages, ensure_ascii=False, sort_keys=True)
                item["judge_prompt_hash"] = "sha256:" + hashlib.sha256(prompt_json.encode("utf-8")).hexdigest()
                item["prompt_chars"] = sum(len(message["content"]) for message in messages)
                item["prompt_message_count"] = len(messages)
            else:
                item["judge_prompt_hash"] = None
                item["prompt_chars"] = 0
                item["prompt_message_count"] = 0
            report["candidates"].append(item)
    report_path = RESULTS / f"llm-judge-prompt-dry-run-{benchmark}-{timestamp}.json"
    markdown_path = RESULTS / f"llm-judge-prompt-dry-run-{benchmark}-{timestamp}.md"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    write_judge_prompt_dry_run_markdown(report, markdown_path)
    return report_path, markdown_path


def build_judge_messages(
    benchmark: str,
    candidate: dict[str, Any],
    case: dict[str, Any],
    gold: dict[str, Any],
    schema: dict[str, Any],
    prompt_spec: dict[str, Any],
    judge_model: str,
    context_mode: str,
) -> list[dict[str, str]]:
    if context_mode not in prompt_spec["supported_context_modes"]:
        raise ValueError(f"unsupported judge_context_mode: {context_mode}")
    system = "\n".join([prompt_spec["system_prompt"]["role"], *prompt_spec["system_prompt"]["rules"]])
    context = build_judge_context(benchmark, case, gold, prompt_spec, context_mode)
    payload = {
        "benchmark_id": benchmark,
        "case_id": candidate["case_id"],
        "candidate_model": candidate["candidate_model"],
        "judge_model": judge_model,
        "judge_context_mode": context_mode,
        "source_report": candidate["source_report"],
        "source_raw_path": candidate["source_raw_path"],
        "source_run_id": candidate["source_run_id"],
        "judge_schema_version": schema["schema_version"],
        "self_judged": candidate["candidate_model"] == judge_model,
        "candidate_status": candidate["candidate_status"],
        "schema_issue": candidate.get("schema_issue"),
        "judge_schema": {
            "dimensions": schema["dimensions"],
            "required_output_fields": schema["required_output_fields"],
            "dimension_score_required_fields": schema["dimension_score_required_fields"],
            "final_recommendation_values": schema["final_recommendation_values"],
            "blocking_failure_values": schema["blocking_failure_values"],
            "aggregation": schema["aggregation"],
        },
        "context": context,
        "candidate_output": candidate["candidate_output"],
    }
    user = "Return JSON only for this judge task:\n" + json.dumps(payload, ensure_ascii=False, indent=2)
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def build_judge_context(
    benchmark: str,
    case: dict[str, Any],
    gold: dict[str, Any],
    prompt_spec: dict[str, Any],
    context_mode: str,
) -> dict[str, Any]:
    articles = [
        {
            "article_id": article["article_id"],
            "title": article["title"],
            "body_excerpt": article["body_excerpt"],
            "body_full_text": article.get("body_full_text", ""),
        }
        for article in case["articles"]
    ]
    context: dict[str, Any] = {
        "user_request": case["user_request"],
        "articles": articles,
        "context_mode_rules": prompt_spec["context_modes"][context_mode],
    }
    if context_mode == "full_golden":
        context["golden"] = gold
    elif context_mode == "hybrid":
        context["hybrid_theme_source"] = prompt_spec["context_modes"]["hybrid"].get("hybrid_theme_source", {})
        if benchmark == "request-synthesis":
            context["forbidden_claims"] = gold.get("forbidden_claims", [])
        else:
            context["article_roles"] = [
                {
                    "article_id": item["article_id"],
                    "relevance": item["relevance"],
                    "article_role": item["article_role"],
                    "support_type": item["support_type"],
                    "must_not_claim": item.get("must_not_claim", []),
                }
                for item in gold.get("article_labels", [])
            ]
    return context


def write_judge_prompt_dry_run_markdown(report: dict[str, Any], path: Path) -> None:
    lines = [
        f"# LLM judge prompt dry run {report['meta']['timestamp']}",
        "",
        f"Benchmark: `{report['meta']['benchmark']}`",
        f"Context mode: `{report['meta']['judge_context_mode']}`",
        f"Source report: `{report['meta']['source_report']}`",
        "",
        "| Candidate model | Judge model | Status | Prompt chars | Prompt hash |",
        "|---|---|---|---:|---|",
    ]
    for item in report["candidates"]:
        lines.append(
            f"| `{item['candidate_model']}` | `{item['judge_model']}` | "
            f"`{item['candidate_status']}` | {item['prompt_chars']} | "
            f"`{item['judge_prompt_hash'] or ''}` |"
        )
    path.write_text("\n".join(lines) + "\n")


def parse_judge_output(
    parsed: dict[str, Any],
    schema: dict[str, Any],
    valid_article_ids: set[str],
    expected_case_id: str,
) -> dict[str, Any]:
    required = schema["required_output_fields"]
    missing = [field for field in required if field not in parsed]
    if missing:
        raise ValueError(f"judge output missing required fields: {missing}")
    if parsed["benchmark_id"] != schema["benchmark_id"]:
        raise ValueError(f"judge benchmark_id mismatch: {parsed['benchmark_id']!r}")
    if parsed["case_id"] != expected_case_id:
        raise ValueError(f"judge case_id mismatch: {parsed['case_id']!r}")
    if parsed["judge_schema_version"] != schema["schema_version"]:
        raise ValueError(f"judge schema version mismatch: {parsed['judge_schema_version']!r}")
    if parsed["candidate_status"] not in schema["candidate_status_values"]:
        raise ValueError(f"invalid candidate_status: {parsed['candidate_status']!r}")
    if parsed["final_recommendation"] not in schema["final_recommendation_values"]:
        raise ValueError(f"invalid final_recommendation: {parsed['final_recommendation']!r}")
    if not isinstance(parsed["self_judged"], bool):
        raise ValueError("self_judged must be boolean")
    if not isinstance(parsed["blocking_failures"], list):
        raise ValueError("blocking_failures must be a list")
    for failure in parsed["blocking_failures"]:
        if failure not in schema["blocking_failure_values"]:
            raise ValueError(f"invalid blocking failure: {failure!r}")
    if parsed["candidate_status"] in {"candidate_parse_error", "candidate_schema_error_blocked"}:
        if parsed["dimension_scores"]:
            raise ValueError("blocked or parse-error candidates must not include semantic dimension_scores")
        return {"judge": parsed, "overall_score": None}
    validate_judge_dimension_scores(parsed, schema, valid_article_ids)
    if "per_article_reviews" in schema["required_output_fields"]:
        validate_judge_per_article_reviews(parsed, schema, valid_article_ids)
    score = parsed["overall_score"]
    if not isinstance(score, (int, float)) or not 0 <= score <= 4:
        raise ValueError(f"overall_score out of range: {score!r}")
    return {"judge": parsed, "overall_score": float(score)}


def validate_judge_dimension_scores(
    parsed: dict[str, Any],
    schema: dict[str, Any],
    valid_article_ids: set[str],
) -> None:
    scores = parsed["dimension_scores"]
    if not isinstance(scores, list):
        raise ValueError("dimension_scores must be a list")
    expected_dimensions = {item["id"] for item in schema["dimensions"]}
    seen: set[str] = set()
    required = schema["dimension_score_required_fields"]
    for item in scores:
        if not isinstance(item, dict):
            raise ValueError("dimension_scores items must be objects")
        missing = [field for field in required if field not in item]
        if missing:
            raise ValueError(f"dimension score missing fields: {missing}")
        dimension = item["dimension"]
        if dimension not in expected_dimensions:
            raise ValueError(f"unknown judge dimension: {dimension!r}")
        if dimension in seen:
            raise ValueError(f"duplicate judge dimension: {dimension}")
        seen.add(dimension)
        score = item["score"]
        if not isinstance(score, (int, float)) or not 0 <= score <= 4:
            raise ValueError(f"judge dimension score out of range for {dimension}: {score!r}")
        if item["confidence"] not in schema["confidence_values"]:
            raise ValueError(f"invalid confidence for {dimension}: {item['confidence']!r}")
        if not isinstance(item["rationale"], str) or not item["rationale"].strip():
            raise ValueError(f"missing rationale for {dimension}")
        cited = item["cited_article_ids"]
        if not isinstance(cited, list):
            raise ValueError(f"cited_article_ids must be a list for {dimension}")
        unknown = [article_id for article_id in cited if article_id not in valid_article_ids]
        if unknown:
            raise ValueError(f"unknown cited article IDs for {dimension}: {unknown}")
        if not isinstance(item["disagreement_flags"], list):
            raise ValueError(f"disagreement_flags must be a list for {dimension}")
    missing_dimensions = sorted(expected_dimensions - seen)
    if missing_dimensions:
        raise ValueError(f"missing judge dimensions: {missing_dimensions}")


def validate_judge_per_article_reviews(
    parsed: dict[str, Any],
    schema: dict[str, Any],
    valid_article_ids: set[str],
) -> None:
    reviews = parsed["per_article_reviews"]
    if not isinstance(reviews, list):
        raise ValueError("per_article_reviews must be a list")
    required = schema["per_article_review_required_fields"]
    for item in reviews:
        if not isinstance(item, dict):
            raise ValueError("per_article_reviews items must be objects")
        missing = [field for field in required if field not in item]
        if missing:
            raise ValueError(f"per-article review missing fields: {missing}")
        if item["article_id"] not in valid_article_ids:
            raise ValueError(f"unknown per-article review article_id: {item['article_id']!r}")
        for field in ["relevance_score", "coverage_score"]:
            score = item[field]
            if not isinstance(score, (int, float)) or not 0 <= score <= 4:
                raise ValueError(f"{field} out of range for {item['article_id']}: {score!r}")
        if item["overstatement_risk"] not in {"low", "medium", "high"}:
            raise ValueError(f"invalid overstatement_risk for {item['article_id']}: {item['overstatement_risk']!r}")
        if not isinstance(item["rationale"], str) or not item["rationale"].strip():
            raise ValueError(f"missing per-article rationale for {item['article_id']}")


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
    parser.add_argument("--judge-source-report", default=None, help="load an existing benchmark report for future LLM judge evaluation")
    parser.add_argument("--judge-context-mode", default="hybrid", choices=["full_golden", "hybrid", "reduced_rubric"])
    parser.add_argument("--judge-calibration-dry-run", action="store_true")
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

    if args.judge_source_report:
        return run_judge_source_mode(args, models)

    if args.judge_calibration_dry_run:
        return run_judge_calibration_dry_run(args)

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
    scorers = {
        "request-synthesis": score_synthesis,
        "request-article-retrieval": score_retrieval,
        "request-article-synthesis": score_article_synthesis_schema,
    }
    scorer = scorers[args.benchmark]

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
