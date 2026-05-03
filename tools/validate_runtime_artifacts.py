#!/usr/bin/env python3
"""
Offline validation for runtime source adapters and compact artifacts.

This is intentionally not a full schema engine. It checks the contracts needed
for runner review: adapter resolution, required artifact fields, lightweight
field types, and the full-text boundary for mode fixtures.
"""
from __future__ import annotations

import argparse
import datetime as dt
import pathlib
import sys
from collections.abc import Iterable
from typing import Any

import yaml


ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE_GROUPS = (
    pathlib.Path("config/runtime/source-groups/daily_core.yaml"),
    pathlib.Path("config/runtime/source-groups/weekly_context.yaml"),
)
SOURCE_MAP = pathlib.Path("cowork/adapters/source_map.md")
STATE_SCHEMA = pathlib.Path("config/runtime/state_schemas.yaml")
CHANGE_REQUEST_SCHEMA = pathlib.Path("config/runtime/change_request_schema.yaml")
VALID_ARTIFACTS = pathlib.Path("config/runtime/state-fixtures/valid_artifacts.yaml")
SAMPLE_CHANGE_REQUEST = pathlib.Path(
    "config/runtime/change-request-fixtures/sample_change_request.yaml"
)
MODE_FIXTURES = pathlib.Path("config/runtime/mode-fixtures")
RUNNER_INTEGRATION_MAP = MODE_FIXTURES / "runner_integration_map.yaml"
REQUIRED_ARTIFACTS = (
    "raw_candidate",
    "shortlisted_item",
    "enriched_item",
    "run_manifest",
    "change_request",
)
ENRICHMENT_MODE_IDS = {"scrape_and_enrich"}
FORBIDDEN_FULL_TEXT_KEYS = {
    "body",
    "full_text",
    "article_body",
    "article_file",
    "body_text",
    "body_word_count",
    "extracted_text",
}
UNSAFE_ENRICHMENT_KEYS = {
    "forbidden_fetch_urls",
    "raw_candidates_not_shortlisted",
}
UNSAFE_ENRICHMENT_KEY_PARTS = (
    "non_shortlisted",
    "not_shortlisted",
)
CHANGE_REQUEST_SIGNAL_KEYS = {
    "change_request",
    "change_request_output_path",
}
EXPECTED_PRIMARY_TOOL_PATH_BY_STRATEGY = {
    "rss": "HTTP/RSS fetcher",
    "html_scrape": "HTTP/RSS fetcher",
    "itunes_api": "HTTP/RSS fetcher",
    "chrome_scrape": "Browser fallback",
    "blocked": "No fetch / manual intake policy",
}
EXPECTED_INVOCATION_KIND_BY_STRATEGY = {
    "rss": "rss",
    "html_scrape": "http",
    "itunes_api": "http",
    "chrome_scrape": "browser",
}
EXPECTED_URL_FIELD_BY_STRATEGY = {
    "rss": "rss_feed",
    "html_scrape": "landing_urls",
    "itunes_api": "itunes_api_url",
    "chrome_scrape": "landing_urls",
}


def load_yaml(path: pathlib.Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def parse_source_map(root: pathlib.Path) -> dict[str, str]:
    path = root / SOURCE_MAP
    adapters: dict[str, str] = {}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line.startswith("|") or "---" in line:
            continue
        cells = [cell.strip().strip("`") for cell in line.strip("|").split("|")]
        if len(cells) < 2 or cells[0] == "source_id":
            continue
        source_id, adapter = cells[0], cells[1]
        if source_id:
            adapters[source_id] = adapter
    return adapters


def configured_source_ids(root: pathlib.Path) -> list[tuple[str, pathlib.Path]]:
    source_ids: list[tuple[str, pathlib.Path]] = []
    for relative_path in SOURCE_GROUPS:
        data = load_yaml(root / relative_path)
        for source in data.get("sources", []):
            source_id = source.get("id")
            if source_id:
                source_ids.append((source_id, relative_path))
    return source_ids


def configured_sources_by_group(root: pathlib.Path) -> dict[tuple[str, str], dict[str, Any]]:
    configured: dict[tuple[str, str], dict[str, Any]] = {}
    for relative_path in SOURCE_GROUPS:
        data = load_yaml(root / relative_path)
        group_id = data.get("group_id")
        for source in data.get("sources", []):
            source_id = source.get("id")
            if group_id and source_id:
                configured[(group_id, source_id)] = source
    return configured


def check_adapters(root: pathlib.Path = ROOT) -> list[str]:
    errors: list[str] = []
    adapters = parse_source_map(root)
    for source_id, group_path in configured_source_ids(root):
        adapter = adapters.get(source_id)
        if adapter is None:
            errors.append(f"{group_path}: source_id {source_id!r} is missing from {SOURCE_MAP}")
            continue
        if not adapter:
            errors.append(f"{SOURCE_MAP}: source_id {source_id!r} has an empty adapter")
            continue
        if adapter != "none" and not (root / adapter).exists():
            errors.append(
                f"{SOURCE_MAP}: source_id {source_id!r} maps to missing adapter {adapter!r}"
            )
    return errors


def merged_artifact_schema(root: pathlib.Path = ROOT) -> dict[str, Any]:
    schema = load_yaml(root / STATE_SCHEMA)
    artifacts = dict(schema.get("artifacts", {}))
    change_request = load_yaml(root / CHANGE_REQUEST_SCHEMA)
    artifacts["change_request"] = {"required_fields": change_request.get("required_fields", [])}
    return {"artifacts": artifacts}


def validate_artifact_fixture(
    schema: dict[str, Any],
    fixture: dict[str, Any],
    artifact_names: Iterable[str],
    label: str,
) -> list[str]:
    errors: list[str] = []
    artifacts = fixture.get("artifacts", fixture)
    for artifact_name in artifact_names:
        artifact_schema = schema.get("artifacts", {}).get(artifact_name)
        artifact_value = artifacts.get(artifact_name)
        if artifact_schema is None:
            errors.append(f"{label}: schema for {artifact_name!r} is missing")
            continue
        if not isinstance(artifact_value, dict):
            errors.append(f"{label}: artifact {artifact_name!r} must be a map")
            continue
        for field in artifact_schema.get("required_fields", []):
            name = field.get("name")
            type_name = field.get("type", "any")
            if name not in artifact_value:
                errors.append(f"{label}: {artifact_name}.{name} is required")
                continue
            errors.extend(
                validate_field_type(
                    artifact_value[name],
                    type_name,
                    f"{label}: {artifact_name}.{name}",
                )
            )
    return errors


def validate_field_type(value: Any, type_name: str, label: str) -> list[str]:
    if type_name.startswith("enum["):
        allowed = type_name.removeprefix("enum[").removesuffix("]").split(",")
        if value not in allowed:
            return [f"{label} must be one of {allowed}, got {value!r}"]
        return []
    if type_name == "string":
        return [] if isinstance(value, str) and value != "" else [f"{label} must be string"]
    if type_name == "string_or_null":
        return [] if value is None or isinstance(value, str) else [f"{label} must be string_or_null"]
    if type_name == "integer":
        return [] if isinstance(value, int) and not isinstance(value, bool) else [f"{label} must be integer"]
    if type_name == "float":
        return [] if isinstance(value, (int, float)) and not isinstance(value, bool) else [f"{label} must be float"]
    if type_name == "map":
        return [] if isinstance(value, dict) else [f"{label} must be map"]
    if type_name == "date":
        return [] if is_date(value) else [f"{label} must be date"]
    if type_name == "datetime":
        return [] if is_datetime(value) else [f"{label} must be datetime"]
    if type_name.startswith("list["):
        if not isinstance(value, list):
            return [f"{label} must be list"]
        subtype = type_name.removeprefix("list[").removesuffix("]")
        return validate_list_items(value, subtype, label)
    return []


def validate_list_items(values: list[Any], subtype: str, label: str) -> list[str]:
    errors: list[str] = []
    for index, item in enumerate(values):
        item_label = f"{label}[{index}]"
        if subtype == "string" and not isinstance(item, str):
            errors.append(f"{item_label} must be string")
        elif subtype == "map" and not isinstance(item, dict):
            errors.append(f"{item_label} must be map")
    return errors


def is_date(value: Any) -> bool:
    if isinstance(value, dt.date) and not isinstance(value, dt.datetime):
        return True
    if not isinstance(value, str):
        return False
    try:
        dt.date.fromisoformat(value)
    except ValueError:
        return False
    return True


def is_datetime(value: Any) -> bool:
    if isinstance(value, dt.datetime):
        return True
    if not isinstance(value, str):
        return False
    try:
        dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def check_fixtures(root: pathlib.Path = ROOT) -> list[str]:
    schema = merged_artifact_schema(root)
    errors = validate_artifact_fixture(
        schema,
        load_yaml(root / VALID_ARTIFACTS),
        REQUIRED_ARTIFACTS,
        str(VALID_ARTIFACTS),
    )
    errors.extend(
        validate_artifact_fixture(
            schema,
            {"change_request": load_yaml(root / SAMPLE_CHANGE_REQUEST)},
            ["change_request"],
            str(SAMPLE_CHANGE_REQUEST),
        )
    )
    errors.extend(check_mode_fixture_change_requests(schema, root))
    return errors


def find_full_text_violations(data: Any, path: pathlib.Path) -> list[str]:
    mode_id = data.get("mode_id") if isinstance(data, dict) else None
    if mode_id in ENRICHMENT_MODE_IDS:
        return find_enrichment_full_text_violations(data, path)
    return [
        f"{path}: {location} uses forbidden full-text key {key!r}"
        for location, key, value in walk_forbidden_keys(data)
        if is_forbidden_full_text_value(key, value)
    ]


def find_enrichment_full_text_violations(data: Any, path: pathlib.Path) -> list[str]:
    errors: list[str] = []
    for location, section in walk_unsafe_enrichment_sections(data):
        for body_location, key, value in walk_forbidden_keys(section, location):
            if is_forbidden_full_text_value(key, value):
                errors.append(
                    f"{path}: {body_location} uses forbidden full-text key {key!r} "
                    f"inside non-shortlisted/forbidden-fetch section {location}"
                )
    return errors


def walk_unsafe_enrichment_sections(
    data: Any,
    location: str = "$",
) -> Iterable[tuple[str, Any]]:
    if isinstance(data, dict):
        if is_unsafe_enrichment_section(data):
            yield location, data
        for key, value in data.items():
            child_location = f"{location}.{key}"
            if is_unsafe_enrichment_key(key):
                yield child_location, value
            yield from walk_unsafe_enrichment_sections(value, child_location)
    elif isinstance(data, list):
        for index, value in enumerate(data):
            yield from walk_unsafe_enrichment_sections(value, f"{location}[{index}]")


def is_unsafe_enrichment_key(key: str) -> bool:
    return key in UNSAFE_ENRICHMENT_KEYS or any(part in key for part in UNSAFE_ENRICHMENT_KEY_PARTS)


def is_unsafe_enrichment_section(data: dict[str, Any]) -> bool:
    triage_decision = data.get("triage_decision")
    if triage_decision is not None and triage_decision != "shortlist":
        return True
    return any(is_unsafe_enrichment_key(key) for key in data)


def walk_forbidden_keys(data: Any, location: str = "$") -> Iterable[tuple[str, str, Any]]:
    if isinstance(data, dict):
        for key, value in data.items():
            child_location = f"{location}.{key}"
            if key in FORBIDDEN_FULL_TEXT_KEYS:
                yield child_location, key, value
            yield from walk_forbidden_keys(value, child_location)
    elif isinstance(data, list):
        for index, value in enumerate(data):
            yield from walk_forbidden_keys(value, f"{location}[{index}]")


def is_forbidden_full_text_value(key: str, value: Any) -> bool:
    if key == "body":
        return value not in (None, "")
    return value is not None


def check_full_text_boundary(root: pathlib.Path = ROOT) -> list[str]:
    errors: list[str] = []
    for path in sorted((root / MODE_FIXTURES).glob("*.yaml")):
        data = load_yaml(path)
        errors.extend(find_full_text_violations(data, path.relative_to(root)))
    return errors


def check_runner_integration(root: pathlib.Path = ROOT) -> list[str]:
    errors: list[str] = []
    path = root / RUNNER_INTEGRATION_MAP
    if not path.exists():
        return [f"{RUNNER_INTEGRATION_MAP}: runner integration map is missing"]
    data = load_yaml(path)
    rows = data.get("sources")
    if not isinstance(rows, list):
        return [f"{RUNNER_INTEGRATION_MAP}: sources must be a list"]

    configured = configured_sources_by_group(root)
    expected_keys = set(configured)
    seen_keys: set[tuple[str, str]] = set()
    adapters = parse_source_map(root) if (root / SOURCE_MAP).exists() else {}

    for index, row in enumerate(rows):
        row_label = f"{RUNNER_INTEGRATION_MAP}: sources[{index}]"
        if not isinstance(row, dict):
            errors.append(f"{row_label} must be a map")
            continue

        group_id = row.get("group_id")
        source_id = row.get("source_id")
        key = (group_id, source_id)
        label = f"{row_label} {group_id}/{source_id}"
        if key in seen_keys:
            errors.append(f"{label}: duplicate runner integration row")
        seen_keys.add(key)
        if key not in expected_keys:
            errors.append(f"{label}: source is not configured in daily_core or weekly_context")
            continue

        configured_source = configured[key]
        fetch_strategy = configured_source.get("fetch_strategy")
        if row.get("fetch_strategy") != fetch_strategy:
            errors.append(
                f"{label}: fetch_strategy must match source group "
                f"{fetch_strategy!r}, got {row.get('fetch_strategy')!r}"
            )

        errors.extend(validate_runner_primary_tool(row, fetch_strategy, label))
        errors.extend(validate_runner_invocation(row, configured_source, fetch_strategy, label))
        errors.extend(validate_runner_adapter(row, adapters, source_id, label))
        errors.extend(validate_runner_fixture_reference(root, row, label))
        if not isinstance(row.get("live_residual_risk"), str) or not row.get("live_residual_risk"):
            errors.append(f"{label}: live_residual_risk must document remaining live-fetch risk")

    for missing_group, missing_source in sorted(expected_keys - seen_keys):
        errors.append(
            f"{RUNNER_INTEGRATION_MAP}: missing source {missing_group}/{missing_source}"
        )
    return errors


def validate_runner_primary_tool(
    row: dict[str, Any],
    fetch_strategy: str,
    label: str,
) -> list[str]:
    primary_tool_path = row.get("primary_tool_path")
    expected = EXPECTED_PRIMARY_TOOL_PATH_BY_STRATEGY.get(fetch_strategy)
    if not isinstance(primary_tool_path, str) or not primary_tool_path:
        return [f"{label}: primary_tool_path must be exactly one non-empty string"]
    if expected is None:
        return [f"{label}: unsupported fetch_strategy {fetch_strategy!r}"]
    if primary_tool_path != expected:
        return [f"{label}: primary_tool_path must be {expected!r}, got {primary_tool_path!r}"]
    return []


def validate_runner_invocation(
    row: dict[str, Any],
    configured_source: dict[str, Any],
    fetch_strategy: str,
    label: str,
) -> list[str]:
    errors: list[str] = []
    if fetch_strategy == "blocked":
        if row.get("invocation_kind") is not None or row.get("invocation_url_field") is not None:
            errors.append(f"{label}: blocked/manual source must not define fetch invocation")
        manual_policy = row.get("manual_policy")
        if manual_policy != configured_source.get("blocked_mode"):
            errors.append(
                f"{label}: manual_policy must match blocked_mode "
                f"{configured_source.get('blocked_mode')!r}"
            )
        return errors

    expected_kind = EXPECTED_INVOCATION_KIND_BY_STRATEGY.get(fetch_strategy)
    expected_url_field = EXPECTED_URL_FIELD_BY_STRATEGY.get(fetch_strategy)
    if row.get("invocation_kind") != expected_kind:
        errors.append(
            f"{label}: invocation_kind must be {expected_kind!r}, "
            f"got {row.get('invocation_kind')!r}"
        )
    if row.get("invocation_url_field") != expected_url_field:
        errors.append(
            f"{label}: invocation_url_field must be {expected_url_field!r}, "
            f"got {row.get('invocation_url_field')!r}"
        )
    if expected_url_field and expected_url_field not in configured_source:
        errors.append(f"{label}: configured source is missing {expected_url_field!r}")
    if row.get("manual_policy") is not None:
        errors.append(f"{label}: non-blocked source manual_policy must be null")
    return errors


def validate_runner_adapter(
    row: dict[str, Any],
    adapters: dict[str, str],
    source_id: str,
    label: str,
) -> list[str]:
    if not adapters:
        return []
    expected_adapter = adapters.get(source_id)
    if row.get("adapter") != expected_adapter:
        return [
            f"{label}: adapter must match source_map.md {expected_adapter!r}, "
            f"got {row.get('adapter')!r}"
        ]
    return []


def validate_runner_fixture_reference(
    root: pathlib.Path,
    row: dict[str, Any],
    label: str,
) -> list[str]:
    references = row.get("fixture_coverage")
    if isinstance(references, str):
        paths = [references]
    elif isinstance(references, list) and all(isinstance(item, str) for item in references):
        paths = references
    else:
        return [f"{label}: fixture_coverage must reference one or more fixture paths"]

    errors: list[str] = []
    for reference in paths:
        if not (root / reference).exists():
            errors.append(f"{label}: fixture_coverage path {reference!r} does not exist")
    return errors


def check_mode_fixture_change_requests(
    schema: dict[str, Any],
    root: pathlib.Path = ROOT,
) -> list[str]:
    errors: list[str] = []
    for path in sorted((root / MODE_FIXTURES).glob("*.yaml")):
        data = load_yaml(path)
        errors.extend(
            validate_mode_fixture_change_requests(
                schema,
                data,
                path.relative_to(root),
            )
        )
    return errors


def validate_mode_fixture_change_requests(
    schema: dict[str, Any],
    fixture: dict[str, Any],
    path: pathlib.Path,
) -> list[str]:
    errors: list[str] = []
    for location, change_request in find_embedded_change_requests(fixture):
        errors.extend(
            validate_artifact_fixture(
                schema,
                {"change_request": change_request},
                ["change_request"],
                f"{path}: {location}",
            )
        )
    if is_change_request_expectation(fixture):
        errors.extend(validate_change_request_expectation_metadata(fixture, path))
    return errors


def find_embedded_change_requests(
    data: Any,
    location: str = "$",
) -> Iterable[tuple[str, dict[str, Any]]]:
    if isinstance(data, dict):
        for key, value in data.items():
            child_location = f"{location}.{key}"
            if key == "change_request" and isinstance(value, dict):
                yield child_location, value
            yield from find_embedded_change_requests(value, child_location)
    elif isinstance(data, list):
        for index, value in enumerate(data):
            yield from find_embedded_change_requests(value, f"{location}[{index}]")


def is_change_request_expectation(fixture: dict[str, Any]) -> bool:
    if "change_request" in str(fixture.get("fixture_id", "")):
        return True
    return has_change_request_signal(fixture)


def has_change_request_signal(data: Any) -> bool:
    if isinstance(data, dict):
        for key, value in data.items():
            if key in CHANGE_REQUEST_SIGNAL_KEYS:
                return True
            if key == "action" and value == "emit_change_request":
                return True
            if has_change_request_signal(value):
                return True
    elif isinstance(data, list):
        return any(has_change_request_signal(value) for value in data)
    return False


def validate_change_request_expectation_metadata(
    fixture: dict[str, Any],
    path: pathlib.Path,
) -> list[str]:
    errors: list[str] = []
    if find_first_value(fixture, "failure_type") is None:
        errors.append(f"{path}: change-request fixture must include failure_type")
    if find_first_value(fixture, "source_id") is None:
        errors.append(f"{path}: change-request fixture must include source_id")
    if find_first_value(fixture, "action") != "emit_change_request":
        errors.append(f"{path}: change-request fixture must expect action emit_change_request")
    if find_first_value(fixture, "change_request_output_path") is None:
        errors.append(f"{path}: change-request fixture must include change_request_output_path")
    if not has_reviewable_change_request_followup(fixture):
        errors.append(
            f"{path}: change-request fixture must include suggested_target_files/tests_to_add "
            "or require both fields explicitly"
        )
    return errors


def has_reviewable_change_request_followup(fixture: dict[str, Any]) -> bool:
    if find_first_value(fixture, "suggested_target_files") is not None and find_first_value(
        fixture,
        "tests_to_add",
    ) is not None:
        return True
    for _location, required_fields in find_key_values(fixture, "required_fields"):
        if isinstance(required_fields, list):
            names = set(required_fields)
            if {"suggested_target_files", "tests_to_add"}.issubset(names):
                return True
    return False


def find_first_value(data: Any, key_name: str) -> Any:
    for _location, value in find_key_values(data, key_name):
        return value
    return None


def find_key_values(
    data: Any,
    key_name: str,
    location: str = "$",
) -> Iterable[tuple[str, Any]]:
    if isinstance(data, dict):
        for key, value in data.items():
            child_location = f"{location}.{key}"
            if key == key_name:
                yield child_location, value
            yield from find_key_values(value, key_name, child_location)
    elif isinstance(data, list):
        for index, value in enumerate(data):
            yield from find_key_values(value, key_name, f"{location}[{index}]")


def run_check(check: str, root: pathlib.Path = ROOT) -> list[str]:
    if check == "adapters":
        return check_adapters(root)
    if check == "fixtures":
        return check_fixtures(root)
    if check == "full-text-boundary":
        return check_full_text_boundary(root)
    if check == "runner-integration":
        return check_runner_integration(root)
    if check == "all":
        errors: list[str] = []
        for subcheck in ("adapters", "fixtures", "full-text-boundary", "runner-integration"):
            errors.extend(run_check(subcheck, root))
        return errors
    raise ValueError(f"unknown check: {check}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        choices=("adapters", "fixtures", "full-text-boundary", "runner-integration", "all"),
        default="all",
        help="Validation check to run.",
    )
    args = parser.parse_args(argv)

    errors = run_check(args.check)
    if errors:
        print(f"FAIL  {args.check}", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"PASS  {args.check}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
