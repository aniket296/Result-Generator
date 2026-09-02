"""
generation/printer.py
Hardware and Document Printing Subsystem for Teacher Result Management System.

Provides:
- Print One: Render a single student record and send to OS print dialog / default printer.
- Print All: Batch spool all student result papers to the printer queue.
- Uses PyQt6.QtPrintSupport.QPrinter & QPrintDialog with PyMuPDF raster rendering.
"""
from __future__ import annotations

import os
import tempfile
from typing import Any

from PyQt6.QtCore import QMarginsF, QRectF, Qt
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtPrintSupport import QPrintDialog, QPrinter
from PyQt6.QtWidgets import QMessageBox, QWidget
import pymupdf

from generation.pdf_generator import generate_single_pdf


def print_single_student_record(
    template_state: dict[str, Any],
    row_data: dict[str, str],
    parent_widget: QWidget | None = None,
) -> bool:
    """
    Renders a single student result to a temporary PDF and prints it via QPrintDialog.
    Returns True if successfully sent to printer, False if cancelled or failed.
    """
    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    dialog = QPrintDialog(printer, parent_widget)
    dialog.setWindowTitle("Print Student Result")

    if dialog.exec() != QPrintDialog.DialogCode.Accepted:
        return False

    temp_pdf = os.path.join(tempfile.gettempdir(), "temp_print_result.pdf")
    try:
        generate_single_pdf(template_state, row_data, temp_pdf)

        doc = pymupdf.open(temp_pdf)
        if len(doc) == 0:
            return False

        page = doc[0]
        pix = page.get_pixmap(dpi=300)
        img = QImage(
            pix.samples,
            pix.width,
            pix.height,
            pix.stride,
            QImage.Format.Format_RGB888 if pix.n == 3 else QImage.Format.Format_RGBA8888,
        )

        painter = QPainter(printer)
        rect = printer.pageRect(QPrinter.Unit.DevicePixel)
        scaled_img = img.scaled(
            int(rect.width()),
            int(rect.height()),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        x = (rect.width() - scaled_img.width()) / 2
        y = (rect.height() - scaled_img.height()) / 2
        painter.drawImage(int(x), int(y), scaled_img)
        painter.end()

        doc.close()
        return True
    except Exception as exc:
        if parent_widget:
            QMessageBox.critical(
                parent_widget,
                "Printing Error",
                f"Failed to print student result:\n{exc}",
            )
        return False
    finally:
        if os.path.exists(temp_pdf):
            try:
                os.remove(temp_pdf)
            except Exception:
                pass


def print_all_student_records(
    template_state: dict[str, Any],
    rows: list[dict[str, str]],
    parent_widget: QWidget | None = None,
) -> tuple[int, int]:
    """
    Batch prints all student records to the printer.
    Returns (printed_count, failed_count).
    """
    if not rows:
        return 0, 0

    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    dialog = QPrintDialog(printer, parent_widget)
    dialog.setWindowTitle("Print All Student Results")

    if dialog.exec() != QPrintDialog.DialogCode.Accepted:
        return 0, 0

    printed = 0
    failed = 0

    painter = QPainter(printer)
    rect = printer.pageRect(QPrinter.Unit.DevicePixel)

    temp_pdf = os.path.join(tempfile.gettempdir(), "temp_batch_print.pdf")

    try:
        for idx, row in enumerate(rows):
            try:
                generate_single_pdf(template_state, row, temp_pdf)
                doc = pymupdf.open(temp_pdf)
                if len(doc) > 0:
                    if idx > 0:
                        printer.newPage()
                    page = doc[0]
                    pix = page.get_pixmap(dpi=300)
                    img = QImage(
                        pix.samples,
                        pix.width,
                        pix.height,
                        pix.stride,
                        QImage.Format.Format_RGB888 if pix.n == 3 else QImage.Format.Format_RGBA8888,
                    )
                    scaled = img.scaled(
                        int(rect.width()),
                        int(rect.height()),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                    x = (rect.width() - scaled.width()) / 2
                    y = (rect.height() - scaled.height()) / 2
                    painter.drawImage(int(x), int(y), scaled)
                    printed += 1
                doc.close()
            except Exception:
                failed += 1
            finally:
                if os.path.exists(temp_pdf):
                    try:
                        os.remove(temp_pdf)
                    except Exception:
                        pass
    finally:
        painter.end()

    return printed, failed
