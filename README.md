# 🎓 Teacher Result Management System (TRMS)

[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078D6?logo=windows&logoColor=white)](#)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](#)
[![GUI](https://img.shields.io/badge/GUI-PyQt6-41CD52?logo=qt&logoColor=white)](#)
[![Offline](https://img.shields.io/badge/Architecture-100%25%20Offline%20%2F%20Air--Gapped-success)](#)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](#license)

## Overview

**Teacher Result Management System (TRMS)** is an enterprise-grade, **100% offline Windows desktop application** engineered with **Python** and **PyQt6** for batch generating high-precision student marksheets, academic certificates, and institutional ID cards directly from Excel/CSV datasets.

Designed from the ground up for schools, colleges, and examination boards operating under strict data governance mandates, TRMS executes all spreadsheet parsing, academic grading calculations, chart rendering, QR code generation, and cryptographic PDF stamping locally in memory—with **zero cloud dependencies, zero telemetry, and zero outbound network calls**.

---

## ✨ Core Highlights

- **🛡️ 100% Offline Privacy & FERPA/DPDP Compliance**
  Operates cleanly in air-gapped environments. Zero telemetry, zero external API calls, and zero cloud storage ensure complete sovereignty over sensitive student PII and academic records. Verified via automated AST static analysis.
- **🎨 Interactive Drag-and-Drop Visual Canvas**
  Powered by PyQt6 `QGraphicsScene` and `QGraphicsView` with magnetic snap-to-grid alignment, multi-page template support, zoom/pan controls, real-time live data preview, and a full Undo/Redo command stack (`QUndoStack`).
- **📊 Per-Student Dynamic Visualizations**
  Generates customized subject performance bar, line, and radar charts in-memory per student using `matplotlib` (`io.BytesIO`) and stamps high-DPI vector/raster graphics directly onto PDF pages via `PyMuPDF` (`fitz`).
- **📚 Smart Class-Wise Print Bundling & N-Up Imposition**
  Automatically groups and merges individual student PDFs into section- or class-specific master print bundles, alongside 2-up / 4-up print imposition sheets with precision crop/cut guides for commercial print shops.
- **📱 Offline Tamper-Proof QR Codes**
  Synthesizes local verification QR code bitmaps (`qrcode`) containing structured plain-text or Base64-encoded student verification payloads for instant offline authenticity checks.
- **🧹 Pre-Flight Data Sanitizer & Academic Engine**
  Performs in-memory validation for duplicate IDs, missing marks, NaN/null cells, Windows reserved device names (`CON`, `PRN`, `AUX`, `NUL`), and directory path-traversal vectors (`../`), coupled with automated dense ranking, percentile calculation, CGPA conversion, and custom grading scales.
- **🔐 AES-256 PDF Password Protection**
  Supports per-student cryptographic PDF encryption (`PDF_ENCRYPT_AES_256`) dynamically keyed to each student's Date of Birth (DOB), Roll Number, or custom password column.

---

## 🛠️ Tech Stack Matrix

| Layer | Technology | Role & Responsibility |
| :--- | :--- | :--- |
| **GUI Framework** | `PyQt6` | Desktop windowing, interactive `QGraphicsScene` designer canvas, multi-threaded `QThread` worker pipelines |
| **Data Ingestion** | `pandas`, `openpyxl` | High-speed Excel (`.xlsx`, `.xls`) and CSV parsing, schema validation, and tabular data normalization |
| **PDF Stamping** | `PyMuPDF` (`fitz`) | Sub-millimeter text typography, dynamic table layout, image insertion, N-up imposition, and AES-256 encryption |
| **Charting** | `matplotlib` | Headless in-memory (`Agg`) generation of per-student subject comparison and performance charts |
| **Security & QR** | `qrcode`, `cryptography` | Local tamper-evident QR code bitmap synthesis, SHA-256 integrity hashing, and cryptographic primitives |
| **Packaging** | `PyInstaller`, `Inno Setup` | Standalone Windows `onedir` executable freezing and native Windows Setup Wizard (`Setup.exe`) compilation |

---

## 📂 Directory Structure

```text
Result Generator/
├── assets/                     # Bundled fonts, application icons, and sample templates
├── core/                       # Core domain logic, academic calculation, and data sanitization
│   ├── data_engine/            # Excel/CSV ingestion, pre-flight validation, and academic grading
│   ├── generation/             # PyMuPDF batch PDF generator, chart renderer, and print imposition
│   └── utils/                  # Path resolution, logging, and offline system utilities
├── ui/                         # PyQt6 user interface components, dialogs, and visual canvas
│   ├── canvas/                 # Interactive QGraphicsScene, resizable field items, and rulers
│   ├── dialogs/                # Pre-flight audit, grading rules, and batch progress dialogs
│   └── main_window.py          # Primary application workspace and ribbon/toolbar controllers
├── tests/                      # Automated unit, integration, and security audit suites
│   └── run_all_checks.py       # Headless 6-suite QA & AppSec validation runner
├── installer/                  # Windows packaging scripts and Inno Setup (.iss) definitions
│   └── build_installer.py      # End-to-end PyInstaller + Inno Setup build automation
├── main.py                     # Application entry point and global exception handler
├── requirements.txt            # Pinned Python dependencies
└── README.md                   # Project documentation
```

---

## 🚀 Setup & Execution Guide

### Prerequisites
- **Operating System:** Windows 10 or Windows 11 (64-bit)
- **Python:** Python 3.10 or higher

### 1. Clone the Repository
```powershell
git clone <repository-url>
cd "Result Generator"
```

### 2. Create & Activate a Virtual Environment
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies
```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Launch the Application
```powershell
python main.py
```

---

## 🧪 Automated Testing & Security Scan

TRMS includes a standalone, headless QA and Application Security audit runner (`tests/run_all_checks.py`) that validates 6 critical suites without requiring manual GUI interaction:

1. **Suite 1: Academic Engine Edge Cases** — Boundary threshold precision (`90.9%` vs `91.0%`), dense ranking ties, and `NaN`/`None`/whitespace resilience.
2. **Suite 2: Security & Path Traversal Injection** — Neutralization of `../` directory escape payloads, Windows reserved filenames (`CON.pdf`, `NUL.pdf`), NTFS illegal characters, and 500+ character buffer exhaustion strings.
3. **Suite 3: Asset Corruption & File Lock Resilience** — Graceful fallback on 0-byte or corrupt binary `.jpg` photos and non-blocking recovery when output PDFs are locked by external viewers.
4. **Suite 4: Offline Purity Audit** — AST static scan across all `.py` source files asserting zero imports of outbound networking or cloud modules (`socket`, `urllib`, `requests`, `http`, `aiohttp`, etc.).
5. **Suite 5: Memory Leak & Resource Profiling** — `tracemalloc` profiling over 100 batch PDF + Matplotlib chart generations verifying deterministic buffer and handle release.
6. **Suite 6: AES-256 PDF Encryption** — Verification of PyMuPDF `PDF_ENCRYPT_AES_256` lock enforcement and password authentication.

### Run the Audit Suite
```powershell
python tests/run_all_checks.py
```

---

## 📦 Build Pipeline (Windows Executable & Installer)

### Option A: Freeze Standalone Executable via PyInstaller (`onedir`)
To bundle the Python interpreter, PyQt6 binaries, PyMuPDF, and `assets/` into a standalone folder distribution:
```powershell
pyinstaller --noconfirm --clean TeacherResultSoftware.spec
```
The compiled application will be output to `dist/TeacherResultSoftware/TeacherResultSoftware.exe`.

### Option B: Compile Full Windows Installer (`Setup.exe`)
To run the automated end-to-end packaging pipeline (PyInstaller freeze + Inno Setup compiler):
```powershell
python installer/build_installer.py
```
*(Note: If `build_installer.py` is located at the project root in your checkout, run `python build_installer.py`.)*

---

## 📄 License

This project is licensed under the **MIT License**. Free for educational, institutional, and commercial use with attribution.

