#!/usr/bin/env python3
"""
Offline contract tests for pdf_extract.py.

Run with:
  python3 tools/test_pdf_extract.py
"""
from __future__ import annotations

import os
import pathlib
import tempfile
import warnings
from contextlib import contextmanager
from io import StringIO
from typing import Iterator
from unittest.mock import patch

warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL.*")
import requests

import pdf_extract


def _pdf_literal(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def make_minimal_text_pdf(lines: list[str]) -> bytes:
    """Create a tiny valid PDF whose text is extractable by pypdf."""
    text_ops = ["BT", "/F1 12 Tf", "72 720 Td", "14 TL"]
    for index, line in enumerate(lines):
        if index:
            text_ops.append("T*")
        text_ops.append(f"({_pdf_literal(line)}) Tj")
    text_ops.append("ET")
    stream = "\n".join(text_ops).encode("ascii")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
        ),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length %d >>\nstream\n%s\nendstream" % (len(stream), stream),
        b"<< /Title (Rightmove PLC RNS) /Author (London Stock Exchange) >>",
    ]

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, body in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{number} 0 obj\n".encode("ascii"))
        pdf.extend(body)
        pdf.extend(b"\nendobj\n")
    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R /Info 6 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(pdf)


class FakePage:
    def __init__(self, text: str | None) -> None:
        self._text = text

    def extract_text(self) -> str | None:
        return self._text


class FakeReader:
    def __init__(
        self,
        pages: list[str | None],
        *,
        metadata: dict[str, str] | None = None,
    ) -> None:
        self.pages = [FakePage(text) for text in pages]
        self.metadata = metadata or {}


class FakeResponse:
    def __init__(
        self,
        *,
        status_code: int = 200,
        content: bytes = b"%PDF-1.4\nfixture\n",
        url: str = "https://example.test/final.pdf",
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self.content = content
        self.url = url
        self.headers = headers or {"Content-Type": "application/pdf"}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} error")


@contextmanager
def fake_reader(reader: FakeReader) -> Iterator[None]:
    original = pdf_extract.PdfReader
    pdf_extract.PdfReader = lambda _stream: reader
    try:
        yield
    finally:
        pdf_extract.PdfReader = original


@contextmanager
def fake_request(response_or_exc: FakeResponse | Exception) -> Iterator[None]:
    original = pdf_extract.requests.get

    def _fake_get(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
        if isinstance(response_or_exc, Exception):
            raise response_or_exc
        return response_or_exc

    pdf_extract.requests.get = _fake_get
    try:
        yield
    finally:
        pdf_extract.requests.get = original


def test_local_pdf_extracts_compact_text_metadata_and_full_hint() -> None:
    """Local PDFs return compact text, metadata, and a full body status hint."""
    long_tail = " ".join(["market update"] * 200)
    reader = FakeReader(
        [
            "Rightmove plc RNS\nDirectorate change announced today.",
            f"Portfolio commentary {long_tail}",
        ],
        metadata={
            "/Title": "Rightmove PLC RNS",
            "/Author": "London Stock Exchange",
        },
    )
    with tempfile.NamedTemporaryFile(suffix=".pdf") as pdf_file:
        pdf_file.write(b"%PDF-1.4\nfixture\n")
        pdf_file.flush()
        with fake_reader(reader):
            result = pdf_extract.extract_source(
                {
                    "source_id": "rightmove_plc_rns",
                    "path": pdf_file.name,
                    "max_chars": 180,
                    "min_text_chars": 50,
                }
            )

    assert result["source_id"] == "rightmove_plc_rns"
    assert result["path"].endswith(".pdf")
    assert result["url"] is None
    assert result["kind"] == "pdf"
    assert result["metadata"]["page_count"] == 2
    assert result["metadata"]["title"] == "Rightmove PLC RNS"
    assert result["metadata"]["author"] == "London Stock Exchange"
    assert result["text"].startswith("Rightmove plc RNS")
    assert len(result["text"]) <= 180
    assert result["text_char_count"] > 180
    assert result["body_status_hint"] == "full"
    assert result["soft_fail"] is None
    assert result["error"] is None


def test_local_pdf_fixture_uses_real_pypdf_parser() -> None:
    """A generated valid PDF fixture exercises actual pypdf text extraction."""
    if pdf_extract.PdfReader is None:
        raise AssertionError("pypdf must be installed for real PDF fixture coverage")

    fixture_text = [
        "Rightmove plc RNS real parser fixture",
        "Directorate change announced today.",
        "Enrichment text should be compact and classified as full.",
    ]
    with tempfile.NamedTemporaryFile(suffix=".pdf") as pdf_file:
        pdf_file.write(make_minimal_text_pdf(fixture_text))
        pdf_file.flush()
        result = pdf_extract.extract_source(
            {
                "source_id": "rightmove_plc_rns",
                "path": pdf_file.name,
                "max_chars": 500,
                "min_text_chars": 50,
            }
        )

    assert result["error"] is None
    assert result["soft_fail"] is None
    assert result["metadata"]["page_count"] == 1
    assert result["metadata"]["title"] == "Rightmove PLC RNS"
    assert result["metadata"]["author"] == "London Stock Exchange"
    assert "Rightmove plc RNS real parser fixture" in result["text"]
    assert "Directorate change announced today." in result["text"]
    assert result["text_char_count"] >= 50
    assert result["body_status_hint"] == "full"


def test_downloaded_pdf_uses_url_and_maps_short_text_to_snippet_fallback() -> None:
    """Public PDF URL extraction is supported for shortlisted enrichment items."""
    reader = FakeReader(["Short notice."])
    response = FakeResponse(url="https://otp.tools.investis.com/rightmove-rns.pdf")
    with fake_request(response), fake_reader(reader):
        result = pdf_extract.extract_source(
            {
                "source_id": "rightmove_plc_rns",
                "url": "https://otp.tools.investis.com/rightmove-rns.pdf",
                "min_text_chars": 40,
            }
        )

    assert result["source_id"] == "rightmove_plc_rns"
    assert result["url"] == "https://otp.tools.investis.com/rightmove-rns.pdf"
    assert result["path"] is None
    assert result["metadata"]["page_count"] == 1
    assert result["metadata"]["content_type"] == "application/pdf"
    assert result["metadata"]["final_url"] == "https://otp.tools.investis.com/rightmove-rns.pdf"
    assert result["text"] == "Short notice."
    assert result["body_status_hint"] == "snippet_fallback"
    assert result["soft_fail"] is None
    assert result["error"] is None


def test_blocked_download_maps_to_paywall_stub_soft_fail() -> None:
    """Blocked or inaccessible PDF downloads surface as paywall_stub hints."""
    with fake_request(FakeResponse(status_code=403)):
        result = pdf_extract.extract_source(
            {
                "source_id": "blocked_pdf",
                "url": "https://example.test/blocked.pdf",
            }
        )

    assert result["text"] == ""
    assert result["text_char_count"] == 0
    assert result["body_status_hint"] == "paywall_stub"
    assert result["soft_fail"] == "blocked_or_paywall"
    assert "HTTP 403" in result["error"]


def test_pdf_extract_does_not_write_state() -> None:
    """The helper returns JSON-ready data and leaves .state writes to runtime."""
    reader = FakeReader(
        ["Rightmove plc RNS content for enrichment only. " * 3]
    )
    original_cwd = pathlib.Path.cwd()
    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)
        try:
            pdf_path = pathlib.Path(tmpdir) / "fixture.pdf"
            pdf_path.write_bytes(b"%PDF-1.4\nfixture\n")
            with fake_reader(reader):
                result = pdf_extract.extract_source(
                    {
                        "source_id": "no_state",
                        "path": str(pdf_path),
                    }
                )
            assert result["text"].startswith("Rightmove plc RNS")
            assert not (pathlib.Path(tmpdir) / ".state").exists()
        finally:
            os.chdir(original_cwd)


def test_cli_emits_one_json_document_for_batch_stdin() -> None:
    """The CLI keeps JSON-in/JSON-out shape for runner batch calls."""
    reader = FakeReader(["Rightmove plc RNS content for enrichment only. " * 3])
    stdin_payload = (
        '{"sources":[{"source_id":"rightmove_plc_rns",'
        '"path":"/tmp/runner-fixture.pdf","max_chars":500}]}'
    )
    stdout = StringIO()
    with fake_reader(reader), patch("pdf_extract.Path.exists", return_value=True), patch(
        "pdf_extract.Path.is_file", return_value=True
    ), patch("pdf_extract.Path.open", return_value=StringIO("pdf")), patch(
        "sys.stdin", StringIO(stdin_payload)
    ), patch(
        "sys.stdout", stdout
    ):
        exit_code = pdf_extract.main(["--stdin"])

    assert exit_code == 0
    output = stdout.getvalue().strip()
    assert output.startswith("{")
    assert output.count("\n") == 0
    assert '"source_id":"rightmove_plc_rns"' in output
    assert '"body_status_hint":"full"' in output


def main() -> None:
    tests = [
        test_local_pdf_extracts_compact_text_metadata_and_full_hint,
        test_local_pdf_fixture_uses_real_pypdf_parser,
        test_downloaded_pdf_uses_url_and_maps_short_text_to_snippet_fallback,
        test_blocked_download_maps_to_paywall_stub_soft_fail,
        test_pdf_extract_does_not_write_state,
        test_cli_emits_one_json_document_for_batch_stdin,
    ]
    for test in tests:
        test()
        print(f"PASS  {test.__name__}")


if __name__ == "__main__":
    main()
