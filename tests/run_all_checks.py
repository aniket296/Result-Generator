"""Headless QA, security, resilience, offline, resource, and PDF checks.

Run from the repository root with:
    python tests/run_all_checks.py

The runner deliberately uses the application's public generation and academic
 APIs.  It never starts a visible Qt window and returns a non-zero exit code
 when any assertion fails.
"""
from __future__ import annotations

import ast
import gc
import io
import os
import sys
import tempfile
import traceback
import tracemalloc
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pymupdf

from data_engine.academic_engine import (
    calculate_cgpa_from_percentage,
    calculate_dense_ranks,
    calculate_grade,
    calculate_percentiles,
    enrich_records,
    evaluate_result_status,
)
from generation import pdf_generator as pdf_mod
from generation.pdf_generator import (
    GeneratorWorker,
    format_filename_from_pattern,
    generate_single_pdf,
    get_unique_result_filename,
    sanitize_filename_part,
)


@dataclass
class SuiteResult:
    name: str
    passed: bool = True
    details: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)

    def check(self, label: str, fn: Callable[[], None], patch: str) -> None:
        try:
            fn()
            self.details.append(f"PASS: {label}")
        except Exception:
            self.passed = False
            self.failures.append(
                f"FAIL: {label}\n"
                f"Traceback:\n{traceback.format_exc()}"
                f"Immediate code patch needed: {patch}"
            )


def _template(*, chart: bool = False, photo: bool = False) -> dict[str, Any]:
    template: dict[str, Any] = {
        "template_name": "Automated Audit",
        "canvas_width": 500.0,
        "canvas_height": 700.0,
        "fields": [
            {"label": "Student Name", "x": 40, "y": 40, "width": 250, "height": 30}
        ],
        "charts": [],
        "photos": [],
    }
    if chart:
        template["charts"] = [{
            "label": "Performance",
            "chart_columns": ["Math", "Science", "English"],
            "x": 40, "y": 130, "width": 300, "height": 180,
        }]
    if photo:
        template["photos"] = [{
            "label": "Student Photo", "photo_id_column": "Roll No",
            "x": 350, "y": 40, "width": 100, "height": 120,
        }]
    return template


def suite_1() -> SuiteResult:
    result = SuiteResult("Suite 1: Academic Engine Edge Cases")
    def boundaries() -> None:
        assert_equal(calculate_grade(90.9), ("A2", 9.0))
        assert_equal(calculate_grade(91.0), ("A1", 10.0))
        assert_equal(calculate_grade(32.9), ("E", 0.0))
        assert_equal(calculate_grade(33.0), ("D", 4.0))
        assert calculate_grade(0)[0] == "E"
        assert calculate_grade(100)[0] == "A1"
        assert calculate_grade(87.5)[0] == "A2"

    result.check(
        "grade thresholds and score boundaries",
        boundaries,
        "Fix the CBSE matrix bounds in data_engine/academic_engine.py.",
    )

    def ranking() -> None:
        assert calculate_dense_ranks([95, 95, 88, 88, 72, 50]) == ["1", "1", "2", "2", "3", "4"]
        assert calculate_dense_ranks([85]) == ["1"]
        assert calculate_percentiles([85]) == ["50.00"]
        assert calculate_dense_ranks([90, 90, 90]) == ["1", "1", "1"]

    result.check(
        "dense ties, one-record, and identical-score ranking",
        ranking,
        "Fix calculate_dense_ranks/calculate_percentiles in data_engine/academic_engine.py.",
    )

    def dirty_data() -> None:
        for value in (float("nan"), None, "", "   ", "N/A", "<NA>", "None"):
            assert calculate_grade(value) == ("N/A", 0.0)
            assert calculate_cgpa_from_percentage(value) == 0.0
            assert evaluate_result_status(value) == "FAILED"
        _, rows = enrich_records(
            ["Roll No", "Percentage"],
            [{"Roll No": str(i), "Percentage": value} for i, value in enumerate(
                ("85.5", float("nan"), None, "", "   "), 1
            )],
        )
        assert len(rows) == 5
        assert rows[0]["Calculated_Grade"] == "A2"
        assert all(row["Calculated_Grade"] == "" for row in rows[1:])

    result.check(
        "NaN, None, empty, and whitespace fallbacks",
        dirty_data,
        "Guard numeric parsing in data_engine/academic_engine.py before arithmetic.",
    )
    return result


def suite_2() -> SuiteResult:
    result = SuiteResult("Suite 2: Security & Path Traversal Injection")
    with tempfile.TemporaryDirectory() as temp:
        target = Path(temp).resolve()

        def traversal() -> None:
            for token in (
                "../../../../Windows/System32/calc",
                r"..\..\Desktop\pwned",
                "/etc/shadow",
            ):
                candidate = Path(get_unique_result_filename(str(target), token, "student")).resolve()
                assert os.path.commonpath((str(target), str(candidate))) == str(target)
                assert ".." not in candidate.name

        result.check(
            "traversal payloads stay inside target directory",
            traversal,
            "Use get_unique_result_filename() and validate commonpath before writing.",
        )

        def reserved() -> None:
            for name in ("CON.pdf", "PRN.pdf", "AUX.pdf", "NUL.pdf", "COM1.pdf", "LPT1.pdf"):
                stem = Path(format_filename_from_pattern("[Name]", {"Name": name})).stem.upper()
                assert stem not in pdf_mod.RESERVED_WINDOWS_NAMES
                assert stem.startswith("RESULT_")

        result.check(
            "Windows device names are renamed",
            reserved,
            "Prefix reserved device stems in generation/pdf_generator.py.",
        )

        def illegal_and_long() -> None:
            payload = '< > : " / \\ | ? *\x00\x1f'
            cleaned = sanitize_filename_part(payload)
            assert not any(char in cleaned for char in '<>:"/\\|?*\x00\x1f')
            candidate = Path(get_unique_result_filename(str(target), "X" * 600, "Y" * 600))
            assert len(candidate.name) <= 150
            candidate.write_bytes(b"test")
            assert candidate.parent == target

        result.check(
            "illegal characters and 500+ character payloads are bounded",
            illegal_and_long,
            "Strip NTFS characters and cap filename components before joining output paths.",
        )
    return result


def suite_3() -> SuiteResult:
    result = SuiteResult("Suite 3: Asset Corruption & File Lock")

    def bad_images() -> None:
        with tempfile.TemporaryDirectory() as photo_dir, tempfile.TemporaryDirectory() as out_dir:
            corrupt = Path(photo_dir) / "CORRUPT.jpg"
            corrupt.write_bytes(os.urandom(256))
            (Path(photo_dir) / "EMPTY.jpg").write_bytes(b"")
            for directory, roll in (
                (str(Path(photo_dir) / "missing"), "MISSING"),
                (photo_dir, "CORRUPT"),
                (photo_dir, "EMPTY"),
            ):
                output = Path(out_dir) / f"{roll}.pdf"
                generate_single_pdf(
                    _template(photo=True),
                    {"Student Name": roll, "Roll No": roll},
                    str(output),
                    photo_dir=directory,
                )
                with pymupdf.open(str(output)) as document:
                    assert "No Photo" in document[0].get_text()

    result.check(
        "missing, corrupt, and zero-byte images use a PDF placeholder",
        bad_images,
        "Catch image decode failures and draw the No Photo fallback in generation/pdf_generator.py.",
    )

    def locked_batch() -> None:
        with tempfile.TemporaryDirectory() as out_dir:
            original = pdf_mod.generate_single_pdf

            def simulate_lock(template: dict[str, Any], row: dict[str, Any], output: str, **kwargs: Any) -> None:
                if row["Roll No"] == "LOCKED":
                    raise PermissionError("simulated exclusive file lock")
                original(template, row, output, **kwargs)

            pdf_mod.generate_single_pdf = simulate_lock
            try:
                worker = GeneratorWorker(
                    _template(),
                    [
                        {"Roll No": "LOCKED", "Student Name": "Locked"},
                        {"Roll No": "FREE", "Student Name": "Free"},
                    ],
                    out_dir,
                    "Roll No",
                    "Student Name",
                )
                worker.run()
                assert len(worker.failed_records) == 1
                assert len(worker.generated_files) == 1
                assert Path(worker.generated_files[0]).exists()
                assert "Locked" in Path(worker.report_path).read_text(encoding="utf-8")
            finally:
                pdf_mod.generate_single_pdf = original

    result.check(
        "permission failure is audited while the batch continues",
        locked_batch,
        "Keep PermissionError handling in GeneratorWorker.run() and write failed_records to the audit report.",
    )
    return result


def suite_4() -> SuiteResult:
    result = SuiteResult("Suite 4: Offline Purity Audit")
    forbidden = {
        "socket", "urllib", "requests", "http", "aiohttp", "ftplib", "xmlrpc",
        "boto3", "botocore", "google", "azure", "firebase_admin", "paramiko",
        "telnetlib",
    }

    def scan() -> None:
        findings: list[str] = []
        ignored = {".venv", "venv", ".git", "__pycache__", "build", "dist"}
        for path in PROJECT_ROOT.rglob("*.py"):
            if any(part in ignored for part in path.parts):
                continue
            source = path.read_text(encoding="utf-8-sig", errors="ignore")
            tree = ast.parse(source, filename=str(path))
            for node in ast.walk(tree):
                imported = None
                if isinstance(node, ast.Import):
                    imported = [alias.name.split(".")[0] for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported = [node.module.split(".")[0]]
                if imported:
                    findings.extend(f"{path.relative_to(PROJECT_ROOT)}:{node.lineno} import {name}" for name in imported if name in forbidden)
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    if isinstance(node.func.value, ast.Name) and node.func.value.id in forbidden:
                        findings.append(f"{path.relative_to(PROJECT_ROOT)}:{node.lineno} call {node.func.value.id}.{node.func.attr}")
        assert not findings, "\n".join(findings)

    result.check(
        "project AST has no network/cloud imports or calls",
        scan,
        "Remove the reported import/call and replace it with an offline implementation.",
    )
    return result


def suite_5() -> SuiteResult:
    result = SuiteResult("Suite 5: Memory Leak & Resource Profiling")

    def profile() -> None:
        import matplotlib.pyplot as plt

        tracemalloc.start()
        try:
            with tempfile.TemporaryDirectory() as out_dir:
                # The generator emits useful interactive diagnostics; suppress
                # them here so the runner's report remains machine-readable.
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    for index in range(100):
                        output = Path(out_dir) / f"student_{index}.pdf"
                        generate_single_pdf(
                            _template(chart=True),
                            {
                                "Student Name": f"Student {index}",
                                "Math": 60 + index % 40,
                                "Science": 65 + index % 35,
                                "English": 70 + index % 30,
                            },
                            str(output),
                        )
                gc.collect()
                current, peak = tracemalloc.get_traced_memory()
                assert len(list(Path(out_dir).glob("*.pdf"))) == 100
                assert not plt.get_fignums(), f"unclosed Matplotlib figures: {plt.get_fignums()}"
                assert current < 25 * 1024 * 1024, f"active allocations grew to {current / 1048576:.2f} MiB"
                assert peak < 75 * 1024 * 1024, f"peak allocations grew to {peak / 1048576:.2f} MiB"
        finally:
            tracemalloc.stop()
        # Exercise the in-memory buffer contract explicitly.
        buffer = io.BytesIO(b"resource-check")
        buffer.close()
        assert buffer.closed

    result.check(
        "100 PDF/chart records release buffers and figures",
        profile,
        "Close PyMuPDF documents and call plt.close('all') on every chart-rendering path.",
    )
    return result


def suite_6() -> SuiteResult:
    result = SuiteResult("Suite 6: AES-256 PDF Encryption")

    def encryption() -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "secured.pdf"
            password = "Student@2026"
            generate_single_pdf(_template(), {"Student Name": "Encrypted Student"}, str(output), password=password)
            with pymupdf.open(str(output)) as document:
                assert document.is_encrypted
                assert document.authenticate("") == 0
                assert document.authenticate(password) > 0
                assert "Encrypted Student" in document[0].get_text()

    result.check(
        "encrypted PDF rejects empty password and accepts the configured password",
        encryption,
        "Pass the password to pymupdf.PDF encryption and save with AES-256 settings.",
    )
    return result


def assert_equal(actual: Any, expected: Any) -> None:
    assert actual == expected, f"expected {expected!r}, got {actual!r}"


def main() -> int:
    suites = (suite_1, suite_2, suite_3, suite_4, suite_5, suite_6)
    results: list[SuiteResult] = []
    print("AUTOMATED AUDIT & SECURITY HARDENING SUITE")
    print(f"Interpreter: {sys.executable}")
    print(f"Project: {PROJECT_ROOT}")
    print("-" * 72)
    for run in suites:
        result = run()
        results.append(result)
        print(f"[{'PASS' if result.passed else 'FAIL'}] {result.name}")
        for detail in result.details:
            print(f"  {detail}")
        for failure in result.failures:
            print(f"  {failure}")
    passed = sum(result.passed for result in results)
    print("-" * 72)
    print(f"SUMMARY: {passed}/{len(results)} suites passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
