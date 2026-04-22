#!/usr/bin/env python3
"""
test_telegram_send.py — Fixtures for telegram_send.py functions.

Tests:
  1. test_telegram_format_html       — convert_md_to_html correctness
  2. test_telegram_no_internal_notes — strip_operator_content correctness
  3. test_digest_file_full_overwrite — Write-not-Edit regression contract
  4. test_strip_run_id_from_footer   — run_id shortening
  5. test_pipe_table_conversion      — GFM table → bullet list
  6. test_validate_html_output       — pre-send validation catches known issues
  7. test_write_presend_cr           — CR written to correct path with correct structure

Run with:
  python3 -m pytest tools/test_telegram_send.py -v
  # or without pytest:
  python3 tools/test_telegram_send.py
"""
from __future__ import annotations

import os
import sys
import tempfile
import pathlib

# Allow running from repo root or from tools/
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from telegram_send import (
    convert_md_to_html,
    strip_operator_content,
    strip_run_id_from_footer,
    validate_html_output,
    write_presend_cr,
)


# ---------------------------------------------------------------------------
# Fixture 1: telegram_format_html
# ---------------------------------------------------------------------------

def test_telegram_format_html() -> None:
    """convert_md_to_html must produce valid Telegram HTML from GFM digest body."""

    # 1a. Headings at all supported levels
    assert convert_md_to_html("# Title") == "<b>Title</b>", "# → <b>"
    assert convert_md_to_html("## Section") == "<b>Section</b>", "## → <b>"
    assert convert_md_to_html("### Subsection") == "<b>Subsection</b>", "### → <b>"

    # 1b. Horizontal rule → removed (blank line or empty)
    result = convert_md_to_html("above\n---\nbelow")
    assert "---" not in result, "--- must be removed"
    assert "above" in result and "below" in result, "surrounding text must be preserved"

    # 1c. Double-star bold → <b>
    assert "<b>bold</b>" in convert_md_to_html("**bold**"), "**bold** → <b>bold</b>"

    # 1d. Single-star bold → <b>
    assert "<b>word</b>" in convert_md_to_html("*word*"), "*word* → <b>word</b>"

    # 1e. Links → <a href>
    result = convert_md_to_html("[Inman](https://inman.com/article)")
    assert '<a href="https://inman.com/article">Inman</a>' in result, "link → <a href>"

    # 1f. Inline code → <code>
    assert "<code>source_id</code>" in convert_md_to_html("`source_id`"), "`…` → <code>"

    # 1g. Plain text HTML special characters must be escaped
    result = convert_md_to_html("price > $100 & < $200")
    assert "&gt;" in result, "< must be escaped as &gt;"
    assert "&lt;" in result, "< must be escaped as &lt;"
    assert "&amp;" in result, "& must be escaped as &amp;"
    assert "<" not in result.replace("<b>", "").replace("</b>", "").replace("<code>", ""), \
        "no raw < in plain text"

    # 1h. Mixed: heading + link + bold in real digest fragment
    fragment = "## ТОП-СИГНАЛЫ\n\n*Аналитика:* подробнее [здесь](https://example.com)"
    out = convert_md_to_html(fragment)
    assert "<b>ТОП-СИГНАЛЫ</b>" in out
    assert '<a href="https://example.com">здесь</a>' in out

    print("PASS  test_telegram_format_html")


# ---------------------------------------------------------------------------
# Fixture 2: telegram_no_internal_notes
# ---------------------------------------------------------------------------

def test_telegram_no_internal_notes() -> None:
    """strip_operator_content must remove blockquote lines with .state/ paths."""

    # 2a. A blockquote operator note is removed
    body_with_note = (
        "First paragraph.\n"
        "\n"
        "> *Предыдущий дайджест сохранён в `.state/briefs/daily/2026-04-22.json`.*\n"
        "\n"
        "Second paragraph."
    )
    result = strip_operator_content(body_with_note)
    assert ".state/" not in result, ".state/ path must be stripped"
    assert "First paragraph." in result, "surrounding text must be kept"
    assert "Second paragraph." in result, "surrounding text must be kept"

    # 2b. A regular blockquote (no .state/ path) is kept
    body_regular_quote = "> This is a regular quote about market trends.\n"
    result2 = strip_operator_content(body_regular_quote)
    assert "regular quote" in result2, "regular blockquote must not be stripped"

    # 2c. A .state/ mention in normal prose (not a blockquote) is kept
    body_prose = "Files are stored in .state/stories/ for reference.\n"
    result3 = strip_operator_content(body_prose)
    assert ".state/stories/" in result3, "prose .state/ mention must not be stripped"

    # 2d. Multiple operator notes — all removed
    body_multi = (
        "> see `.state/briefs/daily/a.json` for context\n"
        "Normal line.\n"
        "> ref `.state/runs/2026-04-22/run.json`\n"
    )
    result4 = strip_operator_content(body_multi)
    assert ".state/" not in result4
    assert "Normal line." in result4

    print("PASS  test_telegram_no_internal_notes")


# ---------------------------------------------------------------------------
# Fixture 3: digest_file_full_overwrite
# ---------------------------------------------------------------------------

def test_digest_file_full_overwrite() -> None:
    """Writing a digest file must use full overwrite (Write), not append (Edit).

    This test documents and enforces the Write-not-Edit contract:
    when a digest for a given date is regenerated, the file must contain
    only the new content — no trailing content from a prior run.

    The test simulates the contract by verifying that writing content B
    to a file that already contains content A leaves only content B.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        digest_path = pathlib.Path(tmpdir) / "2026-04-22-daily-digest.md"

        # Simulate first run (e.g. 2-week window)
        content_a = (
            "# Digest — first run\n"
            "\n"
            "Content from the 2-week window run.\n"
            "Story A, Story B.\n"
        )
        digest_path.write_text(content_a, encoding="utf-8")
        assert digest_path.read_text(encoding="utf-8") == content_a

        # Simulate second run (e.g. 36h window) — full overwrite via Write
        content_b = (
            "# Digest — second run\n"
            "\n"
            "Content from the 36h window run.\n"
            "Story C, Story D.\n"
        )
        # Correct pattern: Write (full overwrite)
        digest_path.write_text(content_b, encoding="utf-8")

        result = digest_path.read_text(encoding="utf-8")

        # Must contain only second-run content
        assert "second run" in result, "second run content must be present"
        assert "first run" not in result, \
            "first run content must NOT be present — use Write, not Edit/append"
        assert result == content_b, "file must be exactly content_b after overwrite"

        # Demonstrate the failure mode: Edit/append leaves stale tail
        digest_path.write_text(content_a, encoding="utf-8")
        with open(digest_path, "a", encoding="utf-8") as f:  # simulates Edit gone wrong
            f.write(content_b)
        bad_result = digest_path.read_text(encoding="utf-8")
        assert "first run" in bad_result and "second run" in bad_result, \
            "append leaves both runs — this is the bug we prevent"

    print("PASS  test_digest_file_full_overwrite")


# ---------------------------------------------------------------------------
# Bonus: strip_run_id_from_footer
# ---------------------------------------------------------------------------

def test_strip_run_id_from_footer() -> None:
    """strip_run_id_from_footer must shorten the full run_id to just the mode."""
    footer = (
        "*Дайджест сгенерирован: 22.04.2026 | mode: build_daily_digest "
        "| run: build_daily_digest__20260422T230500Z__daily_core*"
    )
    result = strip_run_id_from_footer(footer)
    assert "20260422T230500Z" not in result, "timestamp part must be removed"
    assert "daily_core" not in result, "profile suffix must be removed"
    assert "build_daily_digest" in result, "mode name must be kept"
    assert "run: build_daily_digest" in result

    print("PASS  test_strip_run_id_from_footer")


# ---------------------------------------------------------------------------
# Fixture 5: pipe_table_conversion
# ---------------------------------------------------------------------------

def test_pipe_table_conversion() -> None:
    """convert_md_to_html must convert GFM pipe tables to bullet lists."""

    # 5a. Standard table with header + separator + data rows
    table = (
        "| # | Сигнал | Score | Регион |\n"
        "|---|--------|-------|--------|\n"
        "| WS-1 | **AI search wave** | 67.2 | EU |\n"
        "| WS-2 | Immobiliare → Subito | 71.2 | IT |"
    )
    result = convert_md_to_html(table)
    # No raw pipe rows should remain
    for line in result.split("\n"):
        assert not line.startswith("|"), f"Pipe row not converted: {line!r}"
    # Data rows become bullets
    assert "• " in result, "data rows must be bullet points"
    assert "WS-1" in result, "cell content must be preserved"
    assert "WS-2" in result
    # Inline bold within cells should still be converted
    assert "<b>AI search wave</b>" in result, "bold within table cell must be converted"

    # 5b. Table without header/separator (all data rows)
    raw = "| A | B |\n| C | D |"
    out = convert_md_to_html(raw)
    for line in out.split("\n"):
        assert not line.startswith("|"), f"Pipe row not converted: {line!r}"
    assert "A | B" in out or "• A" in out, "data preserved"

    # 5c. Non-table pipe character in prose is NOT converted
    prose = "Probability: low | medium | high"
    out2 = convert_md_to_html(prose)
    # No leading bullet added — this is not a table row (doesn't start with |)
    assert "• " not in out2

    print("PASS  test_pipe_table_conversion")


# ---------------------------------------------------------------------------
# Fixture 6: validate_html_output
# ---------------------------------------------------------------------------

def test_validate_html_output() -> None:
    """validate_html_output must detect known formatting issues."""

    # 6a. Clean HTML — no issues
    clean = (
        "<b>PropTech Monitor | 2026-04-22</b>\n\n"
        "<b>ТОП-СИГНАЛЫ</b>\n\n"
        '<a href="https://example.com">source</a>\n'
    )
    assert validate_html_output(clean) == [], "clean HTML must return no issues"

    # 6b. Raw heading detected
    issues = validate_html_output("## Не сконвертировано\n\ntext")
    check_ids = [i["check_id"] for i in issues]
    assert "raw_md_heading" in check_ids, "## must trigger raw_md_heading error"
    assert any(i["severity"] == "error" for i in issues if i["check_id"] == "raw_md_heading")

    # 6c. Raw horizontal rule
    issues = validate_html_output("above\n---\nbelow")
    assert "raw_hr" in [i["check_id"] for i in issues]

    # 6d. Double-star bold not converted
    issues = validate_html_output("**жирный текст**")
    assert "raw_double_star" in [i["check_id"] for i in issues]

    # 6e. Pipe table rows remaining
    issues = validate_html_output("| WS-1 | text | 67.2 |\n| WS-2 | other | 55.0 |")
    ids = [i["check_id"] for i in issues]
    assert "pipe_table" in ids
    assert any(i["severity"] == "warning" for i in issues if i["check_id"] == "pipe_table")

    # 6f. .state/ path leak — error
    issues = validate_html_output("See .state/briefs/daily/2026-04-22.json for details")
    assert "state_path_leak" in [i["check_id"] for i in issues]
    assert any(i["severity"] == "error" for i in issues if i["check_id"] == "state_path_leak")

    # 6g. Full run_id — warning
    issues = validate_html_output("run: build_daily_digest__20260422T230000Z__daily_core")
    assert "full_run_id" in [i["check_id"] for i in issues]
    assert any(i["severity"] == "warning" for i in issues if i["check_id"] == "full_run_id")

    # 6h. Multiple issues reported together
    multi = "## heading\n---\n**bold**\n| A | B |\n.state/x\nrun: build_x__20260422T000000Z__y"
    issues = validate_html_output(multi)
    assert len(issues) >= 5, f"expected ≥5 issues, got {len(issues)}: {[i['check_id'] for i in issues]}"

    print("PASS  test_validate_html_output")


# ---------------------------------------------------------------------------
# Fixture 7: write_presend_cr
# ---------------------------------------------------------------------------

def test_write_presend_cr() -> None:
    """write_presend_cr must write a valid CR JSON to the correct path."""

    issues = [
        {
            "check_id": "raw_md_heading",
            "severity": "error",
            "symptom": "Raw heading",
            "match_count": 2,
            "examples": ["## Section"],
        },
        {
            "check_id": "pipe_table",
            "severity": "warning",
            "symptom": "Pipe table",
            "match_count": 1,
            "examples": ["| A | B |"],
        },
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        root = pathlib.Path(tmpdir)
        cr_path = write_presend_cr(
            issues, profile="telegram_digest", date="2026-04-22", repo_root=root
        )

        # File must exist in the right location
        assert cr_path.exists(), "CR file must be created"
        expected_dir = root / ".state" / "change-requests" / "2026-04-22"
        assert cr_path.parent == expected_dir, f"CR must be in {expected_dir}"
        assert cr_path.name.startswith("cr_presend_validation__")
        assert cr_path.suffix == ".json"

        # CR content must be valid JSON with required fields
        import json as _json
        cr = _json.loads(cr_path.read_text(encoding="utf-8"))
        assert cr["status"] == "new"
        assert cr["severity"] == "error", "worst severity (error) must be reported"
        assert cr["profile"] == "telegram_digest"
        assert cr["stage"] == "pre_send_validation"
        assert len(cr["issues"]) == 2
        assert cr["issues"][0]["check_id"] == "raw_md_heading"
        assert "symptoms" in cr and len(cr["symptoms"]) == 2

    print("PASS  test_write_presend_cr")


# ---------------------------------------------------------------------------

def _run_all() -> None:
    failures: list[str] = []
    for fn in [
        test_telegram_format_html,
        test_telegram_no_internal_notes,
        test_digest_file_full_overwrite,
        test_strip_run_id_from_footer,
        test_pipe_table_conversion,
        test_validate_html_output,
        test_write_presend_cr,
    ]:
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            failures.append(f"FAIL  {fn.__name__}: {exc}")
            print(f"FAIL  {fn.__name__}: {exc}")
    if failures:
        sys.exit(1)
    print("\nAll tests passed.")


if __name__ == "__main__":
    _run_all()
