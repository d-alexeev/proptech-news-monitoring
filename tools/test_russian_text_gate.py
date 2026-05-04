#!/usr/bin/env python3
from __future__ import annotations

import russian_text_gate


def test_russian_digest_passes_with_english_names_and_links() -> None:
    text = """# PropTech Monitor | 04.05.2026

## Главное

1. **[CoStar claims inventory shift](https://example.test/story)**
   - Сигнал: CoStar заявил о росте предложения OnTheMarket в Великобритании.
   - Почему важно: глубина инвентаря остается ключевым конкурентным рычагом порталов.
   - Для Avito: стоит отдельно отслеживать полноту базы, свежесть объявлений и работу с брокерами.

mode: build_daily_digest | 04.05.2026
"""
    result = russian_text_gate.check_russian_text(text, field_path="digest_markdown")
    assert result["status"] == "pass", result


def test_english_digest_fails_on_ratio_and_markers() -> None:
    text = """# PropTech Monitor | 04.05.2026

## Top Signals

Evidence note: this digest is non-canonical.

Avito lens: challenger pressure starts with inventory.

Source: AIM Group
"""
    result = russian_text_gate.check_russian_text(text, field_path="digest_markdown")
    assert result["status"] == "fail", result
    assert "Top Signals" in result["english_markers"]
    assert result["cyrillic_ratio"] < 0.55


def test_short_internal_strings_are_skipped() -> None:
    result = russian_text_gate.check_russian_text("mode: build_daily_digest | 04.05.2026", field_path="footer")
    assert result["status"] == "skip", result


def test_english_editorial_jargon_fails_inside_russian_digest() -> None:
    text = """# PropTech Monitor | 04.05.2026

## Главные сигналы

Scout24 показывает, что professional customer monetization остается одним из profit pools для порталов.
Для Avito это benchmark по agent tooling, lead quality и data products.
"""
    result = russian_text_gate.check_russian_text(text, field_path="digest_markdown")
    assert result["status"] == "fail", result
    assert "profit pools" in result["english_markers"]
    assert "agent tooling" in result["english_markers"]


def main() -> None:
    tests = [
        test_russian_digest_passes_with_english_names_and_links,
        test_english_digest_fails_on_ratio_and_markers,
        test_short_internal_strings_are_skipped,
        test_english_editorial_jargon_fails_inside_russian_digest,
    ]
    for test in tests:
        test()
    print(f"{len(tests)} tests passed")


if __name__ == "__main__":
    main()
