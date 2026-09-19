"""
utils/preset_manager.py
Built-In Offline Template Library & Preset Manager for Phase 4.3.
Manages production-ready templates:
1. Standard School Marksheet (A4 Portrait)
2. Certificate of Merit / Achievement (A4 Landscape)
3. Student Identity Card (CR80 Standard Size)

Generates vector background PDFs and pre-mapped JSON layout states.
"""
from __future__ import annotations

import json
import os
from typing import Any
import pymupdf

from utils.constants import resource_path


PRESETS_DIR = resource_path(os.path.join("assets", "presets"))


def _hex_to_rgb(hex_str: str) -> tuple[float, float, float]:
    """Convert hex string (e.g. #1e3a8a) to RGB tuple with floats 0.0 - 1.0."""
    cleaned = hex_str.lstrip("#")
    if len(cleaned) == 6:
        r = int(cleaned[0:2], 16) / 255.0
        g = int(cleaned[2:4], 16) / 255.0
        b = int(cleaned[4:6], 16) / 255.0
        return (r, g, b)
    return (0.0, 0.0, 0.0)


# ── Vector Background Generators ─────────────────────────────────────────────

def _build_marksheet_background(output_pdf: str) -> None:
    """Generate professional vector background PDF for Standard School Marksheet (A4: 595 x 842 pt)."""
    doc = pymupdf.open()
    page = doc.new_page(width=595.0, height=842.0)
    w, h = 595.0, 842.0

    c_navy = _hex_to_rgb("#1e3a8a")
    c_gold = _hex_to_rgb("#b45309")
    c_bg_light = _hex_to_rgb("#f8fafc")
    c_border_light = _hex_to_rgb("#cbd5e1")
    c_text_muted = _hex_to_rgb("#475569")

    # 1. Outer & Inner Borders
    page.draw_rect(pymupdf.Rect(18, 18, w - 18, h - 18), color=c_navy, width=2.5)
    page.draw_rect(pymupdf.Rect(23, 23, w - 23, h - 23), color=c_gold, width=0.8)

    # 2. Header Section
    # Emblem circle
    page.draw_circle(pymupdf.Point(62, 62), 24, color=c_navy, fill=_hex_to_rgb("#eff6ff"), width=1.5)
    page.draw_circle(pymupdf.Point(62, 62), 19, color=c_gold, width=0.8)
    page.insert_text(pymupdf.Point(54, 68), "🏫", fontsize=16)

    # School titles
    page.insert_text(pymupdf.Point(98, 52), "DELHI PUBLIC ACADEMY", fontsize=18, fontname="helv", color=c_navy)
    page.insert_text(pymupdf.Point(98, 67), "SENIOR SECONDARY SCHOOL  •  AFFILIATED TO CBSE, NEW DELHI", fontsize=8.5, fontname="helv", color=c_text_muted)
    page.insert_text(pymupdf.Point(98, 79), "Affiliation No. 2130849  |  School Code: 40218  |  www.delhipublicacademy.edu", fontsize=7.5, fontname="helv", color=c_text_muted)

    # Title Ribbon Banner
    ribbon_rect = pymupdf.Rect(30, 92, w - 30, 116)
    page.draw_rect(ribbon_rect, color=c_navy, fill=c_navy, width=0)
    page.insert_text(pymupdf.Point(155, 108), "ANNUAL PROGRESS REPORT CARD  (2025 - 2026)", fontsize=11, fontname="helv", color=(1.0, 1.0, 1.0))

    # 3. Student Bio Information Frame
    bio_rect = pymupdf.Rect(30, 124, w - 30, 214)
    page.draw_rect(bio_rect, color=c_border_light, fill=c_bg_light, width=1.0)

    # Sub-header in bio box
    page.draw_rect(pymupdf.Rect(30, 124, w - 30, 140), color=c_border_light, fill=_hex_to_rgb("#e2e8f0"), width=0.5)
    page.insert_text(pymupdf.Point(38, 135), "STUDENT PROFILE & ACADEMIC DETAILS", fontsize=8.5, fontname="helv", color=c_navy)

    # Labels inside bio box
    col1_x = 38
    col2_x = 260
    page.insert_text(pymupdf.Point(col1_x, 156), "Student Name:", fontsize=8.5, fontname="helv", color=c_text_muted)
    page.insert_text(pymupdf.Point(col1_x, 172), "Roll Number:", fontsize=8.5, fontname="helv", color=c_text_muted)
    page.insert_text(pymupdf.Point(col1_x, 188), "Class & Section:", fontsize=8.5, fontname="helv", color=c_text_muted)
    page.insert_text(pymupdf.Point(col1_x, 204), "Date of Birth:", fontsize=8.5, fontname="helv", color=c_text_muted)

    page.insert_text(pymupdf.Point(col2_x, 156), "Father's Name:", fontsize=8.5, fontname="helv", color=c_text_muted)
    page.insert_text(pymupdf.Point(col2_x, 172), "Mother's Name:", fontsize=8.5, fontname="helv", color=c_text_muted)
    page.insert_text(pymupdf.Point(col2_x, 188), "Enrollment ID:", fontsize=8.5, fontname="helv", color=c_text_muted)
    page.insert_text(pymupdf.Point(col2_x, 204), "Attendance:", fontsize=8.5, fontname="helv", color=c_text_muted)

    # Photo Box outline (top right of bio box)
    photo_box = pymupdf.Rect(485, 130, 555, 208)
    page.draw_rect(photo_box, color=_hex_to_rgb("#94a3b8"), fill=(1.0, 1.0, 1.0), width=0.8, dashes="[3 3] 0")
    page.insert_text(pymupdf.Point(494, 172), "STUDENT", fontsize=7.5, fontname="helv", color=_hex_to_rgb("#94a3b8"))
    page.insert_text(pymupdf.Point(497, 182), "PHOTO", fontsize=7.5, fontname="helv", color=_hex_to_rgb("#94a3b8"))

    # 4. Subject Performance Header Line
    page.insert_text(pymupdf.Point(30, 232), "SCHOLASTIC PERFORMANCE (PART - 1)", fontsize=10, fontname="helv", color=c_navy)

    # 5. Co-Scholastic & Summary Box
    sum_rect = pymupdf.Rect(30, 595, w - 30, 715)
    page.draw_rect(sum_rect, color=c_border_light, fill=c_bg_light, width=1.0)
    page.draw_rect(pymupdf.Rect(30, 595, w - 30, 611), color=c_border_light, fill=_hex_to_rgb("#e2e8f0"), width=0.5)
    page.insert_text(pymupdf.Point(38, 606), "FINAL EVALUATION SUMMARY & TEACHER REMARKS", fontsize=8.5, fontname="helv", color=c_navy)

    page.insert_text(pymupdf.Point(col1_x, 628), "Total Marks Obtained:", fontsize=9, fontname="helv", color=c_text_muted)
    page.insert_text(pymupdf.Point(col1_x, 646), "Overall Percentage:", fontsize=9, fontname="helv", color=c_text_muted)
    page.insert_text(pymupdf.Point(col1_x, 664), "Overall Final Grade:", fontsize=9, fontname="helv", color=c_text_muted)

    page.insert_text(pymupdf.Point(col2_x, 628), "Class Rank / Percentile:", fontsize=9, fontname="helv", color=c_text_muted)
    page.insert_text(pymupdf.Point(col2_x, 646), "Result Status:", fontsize=9, fontname="helv", color=c_text_muted)
    page.insert_text(pymupdf.Point(col2_x, 664), "Teacher Remarks:", fontsize=9, fontname="helv", color=c_text_muted)

    # Grading Scale Legend
    page.draw_line(pymupdf.Point(30, 678), pymupdf.Point(w - 30, 678), color=_hex_to_rgb("#cbd5e1"), width=0.6)
    page.insert_text(
        pymupdf.Point(38, 694),
        "Grading Scale: A1 (91-100%), A2 (81-90%), B1 (71-80%), B2 (61-70%), C1 (51-60%), C2 (41-50%), D (33-40%), E/F (Failed)",
        fontsize=7.0,
        fontname="helv",
        color=_hex_to_rgb("#64748b"),
    )
    page.insert_text(
        pymupdf.Point(38, 706),
        "Minimum qualifying mark is 33% in each subject. This marksheet is digitally stamped and tamper-proof.",
        fontsize=7.0,
        fontname="helv",
        color=_hex_to_rgb("#64748b"),
    )

    # 6. QR Code Verification Area & Signatures
    qr_frame = pymupdf.Rect(35, 730, 95, 790)
    page.draw_rect(qr_frame, color=_hex_to_rgb("#94a3b8"), width=0.8, dashes="[2 2] 0")
    page.insert_text(pymupdf.Point(40, 799), "SCAN TO VERIFY", fontsize=6.5, fontname="helv", color=_hex_to_rgb("#64748b"))

    # Signature Lines
    sig_y = 785
    page.draw_line(pymupdf.Point(145, sig_y), pymupdf.Point(245, sig_y), color=c_text_muted, width=0.8)
    page.insert_text(pymupdf.Point(160, sig_y + 12), "Class Teacher", fontsize=8.5, fontname="helv", color=c_navy)

    page.draw_line(pymupdf.Point(285, sig_y), pymupdf.Point(395, sig_y), color=c_text_muted, width=0.8)
    page.insert_text(pymupdf.Point(298, sig_y + 12), "Exam In-Charge", fontsize=8.5, fontname="helv", color=c_navy)

    page.draw_line(pymupdf.Point(440, sig_y), pymupdf.Point(555, sig_y), color=c_text_muted, width=0.8)
    page.insert_text(pymupdf.Point(475, sig_y + 12), "Principal", fontsize=8.5, fontname="helv", color=c_navy)

    os.makedirs(os.path.dirname(output_pdf), exist_ok=True)
    doc.save(output_pdf)
    doc.close()


def _build_certificate_background(output_pdf: str) -> None:
    """Generate professional vector background PDF for Certificate of Merit (A4 Landscape: 842 x 595 pt)."""
    doc = pymupdf.open()
    page = doc.new_page(width=842.0, height=595.0)
    w, h = 842.0, 595.0

    c_navy = _hex_to_rgb("#1e3a8a")
    c_gold = _hex_to_rgb("#b45309")
    c_gold_light = _hex_to_rgb("#fef3c7")
    c_text_dark = _hex_to_rgb("#0f172a")
    c_text_muted = _hex_to_rgb("#475569")

    # 1. Triple Certificate Decorative Borders
    page.draw_rect(pymupdf.Rect(20, 20, w - 20, h - 20), color=c_navy, width=3.0)
    page.draw_rect(pymupdf.Rect(26, 26, w - 26, h - 26), color=c_gold, width=1.0)
    page.draw_rect(pymupdf.Rect(32, 32, w - 32, h - 32), color=c_navy, width=0.8)

    # Corner Ornaments (decorative corner squares)
    corners = [(20, 20), (w - 32, 20), (20, h - 32), (w - 32, h - 32)]
    for cx, cy in corners:
        page.draw_rect(pymupdf.Rect(cx, cy, cx + 12, cy + 12), color=c_gold, fill=c_gold, width=0)

    # 2. Academy Header
    page.insert_text(pymupdf.Point(286, 75), "NATIONAL EXCELLENCE ACADEMY", fontsize=16, fontname="times-bold", color=c_navy)
    page.insert_text(pymupdf.Point(320, 92), "BOARD OF ACADEMIC AWARDS & MERIT HONORS", fontsize=9, fontname="helv", color=c_gold)

    # Divider line with decorative diamond
    page.draw_line(pymupdf.Point(180, 104), pymupdf.Point(395, 104), color=c_gold, width=1.0)
    page.draw_line(pymupdf.Point(445, 104), pymupdf.Point(662, 104), color=c_gold, width=1.0)
    page.draw_polyline([pymupdf.Point(420, 99), pymupdf.Point(425, 104), pymupdf.Point(420, 109), pymupdf.Point(415, 104), pymupdf.Point(420, 99)], color=c_gold, fill=c_gold, width=1.0)

    # 3. Main Title
    page.insert_text(pymupdf.Point(232, 160), "CERTIFICATE OF MERIT", fontsize=34, fontname="times-bold", color=c_navy)
    page.insert_text(pymupdf.Point(335, 192), "THIS IS PROUDLY PRESENTED TO", fontsize=11, fontname="helv", color=c_gold)

    # Student Name underline bar
    page.draw_line(pymupdf.Point(160, 268), pymupdf.Point(682, 268), color=c_gold, width=1.5)

    # 4. Body Citation Text
    page.insert_text(pymupdf.Point(170, 310), "In recognition of exemplary academic excellence, dedication, and outstanding scholastic achievement,", fontsize=11.5, fontname="helv", color=c_text_dark)
    page.insert_text(pymupdf.Point(255, 332), "demonstrating highest standards of merit during the Academic Session.", fontsize=11.5, fontname="helv", color=c_text_dark)

    # Details subtitle line
    page.draw_line(pymupdf.Point(220, 420), pymupdf.Point(622, 420), color=_hex_to_rgb("#e2e8f0"), width=0.8)

    # 5. Golden Seal / Badge Graphic at Bottom-Left
    seal_center = pymupdf.Point(125, 490)
    page.draw_circle(seal_center, 38, color=c_gold, fill=c_gold_light, width=2.0)
    page.draw_circle(seal_center, 33, color=c_gold, width=0.8, dashes="[2 2] 0")
    page.insert_text(pymupdf.Point(100, 486), "EXCELLENCE", fontsize=7.5, fontname="helv", color=c_gold)
    page.insert_text(pymupdf.Point(108, 498), "AWARD", fontsize=7.5, fontname="helv", color=c_gold)

    # QR Verification Box at Center
    qr_frame = pymupdf.Rect(386, 465, 456, 535)
    page.draw_rect(qr_frame, color=_hex_to_rgb("#cbd5e1"), width=0.8, dashes="[2 2] 0")
    page.insert_text(pymupdf.Point(389, 545), "TAMPER-PROOF VERIFY", fontsize=6.0, fontname="helv", color=_hex_to_rgb("#64748b"))

    # 6. Authorized Signatures
    sig_y = 525
    page.draw_line(pymupdf.Point(540, sig_y), pymupdf.Point(690, sig_y), color=c_text_muted, width=1.0)
    page.insert_text(pymupdf.Point(575, sig_y + 14), "Academic Director", fontsize=9.5, fontname="helv", color=c_navy)

    page.draw_line(pymupdf.Point(210, sig_y), pymupdf.Point(340, sig_y), color=c_text_muted, width=1.0)
    page.insert_text(pymupdf.Point(235, sig_y + 14), "Class Coordinator", fontsize=9.5, fontname="helv", color=c_navy)

    os.makedirs(os.path.dirname(output_pdf), exist_ok=True)
    doc.save(output_pdf)
    doc.close()


def _build_id_card_background(output_pdf: str) -> None:
    """Generate professional vector background PDF for Student Identity Card (CR80 Standard: 242 x 153 pt)."""
    doc = pymupdf.open()
    page = doc.new_page(width=242.0, height=153.0)
    w, h = 242.0, 153.0

    c_navy = _hex_to_rgb("#1e3a8a")
    c_gold = _hex_to_rgb("#d97706")
    c_card_bg = (1.0, 1.0, 1.0)
    c_bar_bg = _hex_to_rgb("#f1f5f9")
    c_text_muted = _hex_to_rgb("#475569")

    # Card background & Border
    page.draw_rect(pymupdf.Rect(0, 0, w, h), color=c_navy, fill=c_card_bg, width=1.0)

    # 1. Top Header Banner (0 to 32 pt)
    page.draw_rect(pymupdf.Rect(0, 0, w, 32), color=c_navy, fill=c_navy, width=0)
    page.draw_line(pymupdf.Point(0, 32), pymupdf.Point(w, 32), color=c_gold, width=1.2)

    page.insert_text(pymupdf.Point(12, 14), "APEX INTERNATIONAL SCHOOL", fontsize=8.5, fontname="helv", color=(1.0, 1.0, 1.0))
    page.insert_text(pymupdf.Point(12, 25), "STUDENT IDENTITY CARD  •  2025-26", fontsize=6.2, fontname="helv", color=_hex_to_rgb("#fef08a"))

    # 2. Photo Frame Placeholder Box (left: x=10, y=38, w=52, h=66)
    photo_frame = pymupdf.Rect(10, 38, 62, 104)
    page.draw_rect(photo_frame, color=_hex_to_rgb("#cbd5e1"), fill=_hex_to_rgb("#f8fafc"), width=0.8)
    page.insert_text(pymupdf.Point(21, 72), "PHOTO", fontsize=6.5, fontname="helv", color=_hex_to_rgb("#94a3b8"))

    # 3. Student Details Labels
    info_x = 68
    page.insert_text(pymupdf.Point(info_x, 48), "Name:", fontsize=6.2, fontname="helv", color=c_text_muted)
    page.insert_text(pymupdf.Point(info_x, 62), "Roll No:", fontsize=6.2, fontname="helv", color=c_text_muted)
    page.insert_text(pymupdf.Point(info_x, 76), "Class & Sec:", fontsize=6.2, fontname="helv", color=c_text_muted)
    page.insert_text(pymupdf.Point(info_x, 90), "Date of Birth:", fontsize=6.2, fontname="helv", color=c_text_muted)
    page.insert_text(pymupdf.Point(info_x, 104), "Blood Group:", fontsize=6.2, fontname="helv", color=c_text_muted)
    page.insert_text(pymupdf.Point(info_x, 118), "Emergency:", fontsize=6.2, fontname="helv", color=c_text_muted)

    # 4. QR Box Placeholder (top-right: x=186, y=42, w=46, h=46)
    qr_frame = pymupdf.Rect(186, 42, 232, 88)
    page.draw_rect(qr_frame, color=_hex_to_rgb("#cbd5e1"), fill=_hex_to_rgb("#f8fafc"), width=0.8, dashes="[2 2] 0")
    page.insert_text(pymupdf.Point(194, 98), "ID VERIFY", fontsize=5.5, fontname="helv", color=_hex_to_rgb("#64748b"))

    # Principal Signature Box
    page.draw_line(pymupdf.Point(180, 122), pymupdf.Point(234, 122), color=_hex_to_rgb("#94a3b8"), width=0.6)
    page.insert_text(pymupdf.Point(188, 128), "Principal Sig.", fontsize=5.5, fontname="helv", color=c_navy)

    # 5. Bottom Footer Bar (134 to 153 pt)
    page.draw_rect(pymupdf.Rect(0, 134, w, h), color=c_navy, fill=c_bar_bg, width=0.5)
    page.insert_text(
        pymupdf.Point(12, 144),
        "If found, please return to school office. Tel: +91 98765 43210  |  Campus: Block B, City Center",
        fontsize=4.8,
        fontname="helv",
        color=c_text_muted,
    )

    os.makedirs(os.path.dirname(output_pdf), exist_ok=True)
    doc.save(output_pdf)
    doc.close()


# ── Preset JSON State Builders ───────────────────────────────────────────────

def _get_marksheet_json_state(bg_pdf_path: str) -> dict[str, Any]:
    """Pre-mapped JSON configuration for Standard School Marksheet."""
    return {
        "version": "1.0",
        "template_id": "preset-marksheet-001",
        "template_name": "Standard School Marksheet",
        "num_pages": 1,
        "canvas_width": 595.0,
        "canvas_height": 842.0,
        "background": {
            "type": "pdf",
            "path": bg_pdf_path,
        },
        "background_page2": {"type": "", "path": ""},
        "backgrounds": [{"type": "pdf", "path": bg_pdf_path}],
        "fields": [
            # Student Bio Details
            {"label": "Student Name", "mapped_column": "Student Name", "page": 1, "x": 105, "y": 145, "width": 140, "height": 16, "font_size": 9.5, "bold": True, "color": "#1e293b"},
            {"label": "Roll No", "mapped_column": "Roll No", "page": 1, "x": 105, "y": 161, "width": 140, "height": 16, "font_size": 9.0, "bold": False, "color": "#1e293b"},
            {"label": "Class", "mapped_column": "Class", "page": 1, "x": 105, "y": 177, "width": 140, "height": 16, "font_size": 9.0, "bold": False, "color": "#1e293b"},
            {"label": "Date of Birth", "mapped_column": "Date of Birth", "page": 1, "x": 105, "y": 193, "width": 140, "height": 16, "font_size": 9.0, "bold": False, "color": "#1e293b"},

            {"label": "Father Name", "mapped_column": "Father Name", "page": 1, "x": 335, "y": 145, "width": 140, "height": 16, "font_size": 9.0, "bold": False, "color": "#1e293b"},
            {"label": "Mother Name", "mapped_column": "Mother Name", "page": 1, "x": 335, "y": 161, "width": 140, "height": 16, "font_size": 9.0, "bold": False, "color": "#1e293b"},
            {"label": "Enrollment", "mapped_column": "Enrollment number", "page": 1, "x": 335, "y": 177, "width": 140, "height": 16, "font_size": 9.0, "bold": False, "color": "#1e293b"},
            {"label": "Attendance", "mapped_column": "Attendance", "page": 1, "x": 335, "y": 193, "width": 140, "height": 16, "font_size": 9.0, "bold": False, "color": "#1e293b"},

            # Final Evaluation Summary Fields
            {"label": "Total Marks", "mapped_column": "Total Marks", "page": 1, "x": 145, "y": 618, "width": 95, "height": 16, "font_size": 9.5, "bold": True, "color": "#0f172a"},
            {"label": "Percentage", "mapped_column": "Percentage", "page": 1, "x": 145, "y": 636, "width": 95, "height": 16, "font_size": 9.5, "bold": True, "color": "#0f172a"},
            {"label": "Calculated Grade", "mapped_column": "Calculated_Grade", "page": 1, "x": 145, "y": 654, "width": 95, "height": 16, "font_size": 10.0, "bold": True, "color": "#1e3a8a"},

            {"label": "Class Rank", "mapped_column": "Class_Rank", "page": 1, "x": 365, "y": 618, "width": 180, "height": 16, "font_size": 9.5, "bold": True, "color": "#0f172a"},
            {"label": "Result Status", "mapped_column": "Result_Status", "page": 1, "x": 365, "y": 636, "width": 180, "height": 16, "font_size": 9.5, "bold": True, "color": "#047857"},
            {"label": "Teacher Remarks", "mapped_column": "Teacher_Remarks", "page": 1, "x": 365, "y": 654, "width": 180, "height": 18, "font_size": 8.5, "bold": False, "color": "#334155", "auto_shrink": True},
        ],
        "tables": [
            {
                "item_type": "table",
                "label": "Scholastic Subjects Table",
                "page": 1,
                "x": 30.0,
                "y": 248.0,
                "width": 535.0,
                "height": 330.0,
                "columns": ["Subject", "Max Marks", "Marks Obtained", "Grade"],
                "header_bg": "#1e3a8a",
                "header_color": "#ffffff",
                "row_alt_bg": "#f8fafc",
                "border_color": "#cbd5e1",
                "font_size": 9.0,
            }
        ],
        "photos": [
            {
                "item_type": "photo",
                "label": "Student Photo",
                "page": 1,
                "x": 487.0,
                "y": 132.0,
                "width": 66.0,
                "height": 74.0,
                "shape": "rect",
            }
        ],
        "qrs": [
            {
                "item_type": "qr",
                "label": "Verification QR",
                "page": 1,
                "x": 37.0,
                "y": 732.0,
                "width": 56.0,
                "height": 56.0,
                "qr_type": "summary",
                "error_correction": "M",
            }
        ],
        "badges": [
            {
                "item_type": "badge",
                "label": "Result Badge",
                "page": 1,
                "x": 480.0,
                "y": 616.0,
                "width": 75.0,
                "height": 28.0,
                "condition_column": "Result_Status",
                "condition_value": "PASSED",
                "badge_text": "PASSED",
                "bg_color": "#d1fae5",
                "text_color": "#065f46",
            }
        ],
        "charts": [],
    }


def _get_certificate_json_state(bg_pdf_path: str) -> dict[str, Any]:
    """Pre-mapped JSON configuration for Certificate of Merit / Achievement."""
    return {
        "version": "1.0",
        "template_id": "preset-certificate-002",
        "template_name": "Certificate of Merit",
        "num_pages": 1,
        "canvas_width": 842.0,
        "canvas_height": 595.0,
        "background": {
            "type": "pdf",
            "path": bg_pdf_path,
        },
        "background_page2": {"type": "", "path": ""},
        "backgrounds": [{"type": "pdf", "path": bg_pdf_path}],
        "fields": [
            {
                "label": "Student Name",
                "mapped_column": "Student Name",
                "page": 1,
                "x": 171.0,
                "y": 222.0,
                "width": 500.0,
                "height": 42.0,
                "font_size": 26.0,
                "bold": True,
                "color": "#1e3a8a",
                "alignment": "center",
            },
            {
                "label": "Achievement Details",
                "mapped_column": "Achievement",
                "page": 1,
                "x": 180.0,
                "y": 350.0,
                "width": 482.0,
                "height": 30.0,
                "font_size": 12.0,
                "bold": True,
                "color": "#b45309",
                "alignment": "center",
                "auto_shrink": True,
            },
            {
                "label": "Class & Section",
                "mapped_column": "Class",
                "page": 1,
                "x": 230.0,
                "y": 395.0,
                "width": 160.0,
                "height": 20.0,
                "font_size": 10.0,
                "bold": False,
                "color": "#475569",
                "alignment": "center",
            },
            {
                "label": "Academic Year",
                "mapped_column": "Academic Year",
                "page": 1,
                "x": 450.0,
                "y": 395.0,
                "width": 160.0,
                "height": 20.0,
                "font_size": 10.0,
                "bold": False,
                "color": "#475569",
                "alignment": "center",
            },
            {
                "label": "Issue Date",
                "mapped_column": "Date",
                "page": 1,
                "x": 371.0,
                "y": 440.0,
                "width": 100.0,
                "height": 18.0,
                "font_size": 9.0,
                "bold": False,
                "color": "#64748b",
                "alignment": "center",
            },
        ],
        "tables": [],
        "photos": [],
        "qrs": [
            {
                "item_type": "qr",
                "label": "Verification QR",
                "page": 1,
                "x": 396.0,
                "y": 472.0,
                "width": 50.0,
                "height": 50.0,
                "qr_type": "tamper_proof",
                "error_correction": "M",
            }
        ],
        "badges": [
            {
                "item_type": "badge",
                "label": "Merit Badge",
                "page": 1,
                "x": 92.0,
                "y": 455.0,
                "width": 66.0,
                "height": 66.0,
                "condition_column": "Calculated_Grade",
                "condition_value": "A1",
                "badge_text": "HONOR ROLL",
                "bg_color": "#fef3c7",
                "text_color": "#b45309",
            }
        ],
        "charts": [],
    }


def _get_id_card_json_state(bg_pdf_path: str) -> dict[str, Any]:
    """Pre-mapped JSON configuration for Student Identity Card (CR80 Standard)."""
    return {
        "version": "1.0",
        "template_id": "preset-idcard-003",
        "template_name": "Student Identity Card",
        "num_pages": 1,
        "canvas_width": 242.0,
        "canvas_height": 153.0,
        "background": {
            "type": "pdf",
            "path": bg_pdf_path,
        },
        "background_page2": {"type": "", "path": ""},
        "backgrounds": [{"type": "pdf", "path": bg_pdf_path}],
        "fields": [
            {"label": "Student Name", "mapped_column": "Student Name", "page": 1, "x": 108, "y": 41, "width": 75, "height": 12, "font_size": 7.5, "bold": True, "color": "#1e293b", "auto_shrink": True},
            {"label": "Roll No", "mapped_column": "Roll No", "page": 1, "x": 108, "y": 55, "width": 75, "height": 11, "font_size": 6.5, "bold": False, "color": "#1e293b"},
            {"label": "Class", "mapped_column": "Class", "page": 1, "x": 108, "y": 69, "width": 75, "height": 11, "font_size": 6.5, "bold": False, "color": "#1e293b"},
            {"label": "Date of Birth", "mapped_column": "Date of Birth", "page": 1, "x": 108, "y": 83, "width": 75, "height": 11, "font_size": 6.5, "bold": False, "color": "#1e293b"},
            {"label": "Blood Group", "mapped_column": "Blood Group", "page": 1, "x": 108, "y": 97, "width": 75, "height": 11, "font_size": 6.5, "bold": False, "color": "#1e293b"},
            {"label": "Emergency Phone", "mapped_column": "Phone", "page": 1, "x": 108, "y": 111, "width": 75, "height": 11, "font_size": 6.5, "bold": True, "color": "#b91c1c"},
        ],
        "tables": [],
        "photos": [
            {
                "item_type": "photo",
                "label": "Student Photo",
                "page": 1,
                "x": 11.0,
                "y": 39.0,
                "width": 50.0,
                "height": 64.0,
                "shape": "rect",
            }
        ],
        "qrs": [
            {
                "item_type": "qr",
                "label": "ID Verification QR",
                "page": 1,
                "x": 188.0,
                "y": 44.0,
                "width": 42.0,
                "height": 42.0,
                "qr_type": "summary",
                "error_correction": "M",
            }
        ],
        "badges": [],
        "charts": [],
    }


# ── Public API & Presets Registry ───────────────────────────────────────────

def ensure_presets_built() -> list[dict[str, Any]]:
    """
    Ensures all 3 built-in offline preset background PDFs and JSON templates
    exist in assets/presets/ and returns their metadata.
    """
    os.makedirs(PRESETS_DIR, exist_ok=True)

    presets_def = [
        {
            "id": "school_marksheet",
            "name": "Standard School Marksheet",
            "category": "Marksheet & Report Card",
            "paper_size": "Portrait A4 (595 × 842 pt)",
            "dimensions": (595.0, 842.0),
            "description": "Board-compliant academic marksheet with student bio details, dynamic variable-row subject marks table, grading matrix, photo frame, and verification QR stamp.",
            "recommended_cols": ["Roll No", "Student Name", "Class", "Section", "Father Name", "Total Marks", "Percentage", "Calculated_Grade", "Result_Status"],
            "bg_filename": "school_marksheet_bg.pdf",
            "json_filename": "school_marksheet.json",
            "builder": _build_marksheet_background,
            "state_fn": _get_marksheet_json_state,
        },
        {
            "id": "certificate_merit",
            "name": "Certificate of Merit / Achievement",
            "category": "Merit Certificate",
            "paper_size": "Landscape A4 (842 × 595 pt)",
            "dimensions": (842.0, 595.0),
            "description": "Ornate academic award certificate with decorative borders, achievement text, distinction honor badge, and digital verification seal.",
            "recommended_cols": ["Student Name", "Achievement", "Class", "Academic Year", "Date", "Calculated_Grade"],
            "bg_filename": "certificate_merit_bg.pdf",
            "json_filename": "certificate_merit.json",
            "builder": _build_certificate_background,
            "state_fn": _get_certificate_json_state,
        },
        {
            "id": "student_id_card",
            "name": "Student Identity Card",
            "category": "Identity Card",
            "paper_size": "CR80 Standard (242 × 153 pt)",
            "dimensions": (242.0, 153.0),
            "description": "CR80 standard identity card designed for 10-Up print sheet imposition. Includes student photo, emergency contacts, and verification QR.",
            "recommended_cols": ["Student Name", "Roll No", "Class", "Date of Birth", "Blood Group", "Phone"],
            "bg_filename": "student_id_card_bg.pdf",
            "json_filename": "student_id_card.json",
            "builder": _build_id_card_background,
            "state_fn": _get_id_card_json_state,
        },
    ]

    registry = []
    for p in presets_def:
        bg_path = os.path.join(PRESETS_DIR, p["bg_filename"])
        json_path = os.path.join(PRESETS_DIR, p["json_filename"])

        # 1. Ensure background vector PDF exists
        if not os.path.exists(bg_path):
            p["builder"](bg_path)

        # 2. Ensure JSON configuration exists
        if not os.path.exists(json_path):
            state = p["state_fn"](bg_path)
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)

        entry = {
            "id": p["id"],
            "name": p["name"],
            "category": p["category"],
            "paper_size": p["paper_size"],
            "dimensions": p["dimensions"],
            "description": p["description"],
            "recommended_cols": p["recommended_cols"],
            "bg_path": os.path.abspath(bg_path),
            "json_path": os.path.abspath(json_path),
        }
        registry.append(entry)

    return registry


def load_preset_template_state(preset_id_or_path: str) -> dict[str, Any] | None:
    """
    Loads and returns the template dictionary for the specified preset ID or JSON path,
    ensuring that background paths are resolved correctly.
    """
    presets = ensure_presets_built()
    target_path = ""
    for p in presets:
        if p["id"] == preset_id_or_path or p["json_path"] == preset_id_or_path or p["name"].lower() == preset_id_or_path.lower():
            target_path = p["json_path"]
            break

    if not target_path and os.path.exists(preset_id_or_path):
        target_path = preset_id_or_path

    if not target_path or not os.path.exists(target_path):
        return None

    with open(target_path, "r", encoding="utf-8") as f:
        state = json.load(f)

    # Ensure background paths exist and are absolute
    bg = state.get("background", {})
    bg_p = bg.get("path", "")
    if bg_p and not os.path.exists(bg_p):
        cand = os.path.join(PRESETS_DIR, os.path.basename(bg_p))
        if os.path.exists(cand):
            bg["path"] = os.path.abspath(cand)
            state["background"] = bg

    return state

