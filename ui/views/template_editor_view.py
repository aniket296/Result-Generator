"""
Template Editor view.

Layout
------
TemplateEditorView (QWidget)
 └─ QVBoxLayout
     ├─ Toolbar strip  (fixed height 52px)
     └─ QHBoxLayout (main content)
         ├─ _CanvasView  (QGraphicsView, expands to fill space)
         └─ PropertiesPanel  (fixed width 272px, shows when item selected)

Canvas
------
- QGraphicsScene default rect = A4 at 96 dpi (794 x 1123 px)
- Background: QGraphicsPixmapItem at Z=0, non-movable / non-selectable
- Fields    : FieldItem instances at Z=1+
- Ctrl+Scroll = zoom;  rubber-band drag on empty space = multi-select

JSON template format (v1.0)
-----------------------------
{
  "version": "1.0",
  "background": {"type": "image"|"pdf"|"", "path": "..."},
  "canvas": {"width": int, "height": int},
  "fields": [ <FieldItem.to_dict()>, ... ]
}
"""
from __future__ import annotations

import json
import os

from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QBrush, QColor, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGraphicsItem,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ui.widgets.field_item import FieldItem
from ui.widgets.properties_panel import PropertiesPanel
from utils.constants import APP_DATA_DIR

try:
    import pymupdf
    _HAS_PYMUPDF = True
except ImportError:
    _HAS_PYMUPDF = False

_TEMPLATES_DIR = os.path.join(APP_DATA_DIR, "templates")


# ---------------------------------------------------------------------------
# Custom QGraphicsView with Ctrl+Scroll zoom
# ---------------------------------------------------------------------------


class _CanvasView(QGraphicsView):
    """QGraphicsView with Ctrl+Scroll zoom and rubber-band selection."""

    def __init__(self, scene: QGraphicsScene, parent: QWidget | None = None) -> None:
        super().__init__(scene, parent)
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.SmoothPixmapTransform
        )
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setBackgroundBrush(QBrush(QColor("#d1d5db")))
        self.setStyleSheet("border: none;")

    def wheelEvent(self, event) -> None:
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            factor = 1.15 if event.angleDelta().y() > 0 else 1.0 / 1.15
            self.scale(factor, factor)
        else:
            super().wheelEvent(event)


# ---------------------------------------------------------------------------
# Template Editor View
# ---------------------------------------------------------------------------


class TemplateEditorView(QWidget):
    """Visual template designer: background image + draggable field placeholders."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._field_items: list[FieldItem] = []
        self._field_counter: int = 0
        self._bg_item: QGraphicsPixmapItem | None = None
        self._bg_type: str = ""
        self._bg_path: str = ""
        self._selected_item: FieldItem | None = None
        self._excel_headers: list[str] = []
        self._initial_fit_done: bool = False

        os.makedirs(_TEMPLATES_DIR, exist_ok=True)
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_toolbar())

        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet("color: #e5e7eb; margin: 0;")
        root.addWidget(div)

        content = QHBoxLayout()
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(0)
        content.addWidget(self._build_canvas(), stretch=1)
        content.addWidget(self._build_props_panel())
        root.addLayout(content, stretch=1)

    # ── Toolbar ───────────────────────────────────────────────────────────────

    def _build_toolbar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(52)
        bar.setStyleSheet("background: #f9fafb;")

        row = QHBoxLayout(bar)
        row.setContentsMargins(16, 0, 16, 0)
        row.setSpacing(8)

        title = QLabel("Template Editor")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #1a1a2e;")
        row.addWidget(title)
        row.addSpacing(12)
        row.addWidget(self._vdivider())
        row.addSpacing(8)

        self._upload_btn = self._mkbtn("📂  Upload Background", "#22c55e", "#16a34a")
        self._add_btn    = self._mkbtn("➕  Add Field",          "#4f7ef8", "#3b6ef0")
        self._del_btn    = self._mkbtn("🗑  Delete",             "#ef4444", "#dc2626")
        self._del_btn.setEnabled(False)

        self._upload_btn.clicked.connect(self._on_upload_bg)
        self._add_btn.clicked.connect(self._on_add_field)
        self._del_btn.clicked.connect(self._on_delete_selected)

        row.addWidget(self._upload_btn)
        row.addWidget(self._add_btn)
        row.addWidget(self._del_btn)
        row.addSpacing(8)
        row.addWidget(self._vdivider())
        row.addSpacing(8)

        save_btn = self._mkbtn("💾  Save Template", "#1f2937", "#111827")
        load_btn = self._mkbtn("📤  Load Template", outline=True)
        save_btn.clicked.connect(self._on_save_template)
        load_btn.clicked.connect(self._on_load_template)
        row.addWidget(save_btn)
        row.addWidget(load_btn)

        row.addStretch()

        # Zoom controls
        zm = self._zkbtn
        self._zoom_lbl = QLabel("100%")
        self._zoom_lbl.setFixedWidth(44)
        self._zoom_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._zoom_lbl.setStyleSheet("font-size: 12px; color: #374151;")

        zout = zm("−")
        zrst = zm("⟳", 26)
        zin  = zm("+")
        zout.clicked.connect(lambda: self._do_zoom(1.0 / 1.2))
        zrst.clicked.connect(self._reset_zoom)
        zin.clicked.connect(lambda: self._do_zoom(1.2))

        row.addWidget(QLabel("Zoom:"))
        row.addWidget(zout)
        row.addWidget(self._zoom_lbl)
        row.addWidget(zin)
        row.addWidget(zrst)

        return bar

    # ── Canvas ────────────────────────────────────────────────────────────────

    def _build_canvas(self) -> _CanvasView:
        self._scene = QGraphicsScene(self)
        # Default canvas = A4 @ 96 dpi
        self._scene.setSceneRect(QRectF(0, 0, 794, 1123))
        self._scene.selectionChanged.connect(self._on_selection_changed)

        self._canvas = _CanvasView(self._scene)
        return self._canvas

    # ── Properties panel ──────────────────────────────────────────────────────

    def _build_props_panel(self) -> PropertiesPanel:
        self._props = PropertiesPanel(self)

        # Wire: panel signal → apply to selected item
        P = self._props
        S = self._on_sel   # helper that calls fn(item) if item exists

        P.label_changed.connect(       lambda v: S(lambda i: i.set_label(v)))
        P.column_changed.connect(      lambda v: S(lambda i: i.set_mapped_column(v)))
        P.font_family_changed.connect( lambda v: S(lambda i: i.set_font_family(v)))
        P.font_size_changed.connect(   lambda v: S(lambda i: i.set_font_size(v)))
        P.color_changed.connect(       lambda v: S(lambda i: i.set_color(v)))
        P.bold_changed.connect(        lambda v: S(lambda i: i.set_bold(v)))
        P.italic_changed.connect(      lambda v: S(lambda i: i.set_italic(v)))
        P.alignment_changed.connect(   lambda v: S(lambda i: i.set_alignment(v)))
        P.x_changed.connect(           lambda v: S(lambda i: i.setX(float(v))))
        P.y_changed.connect(           lambda v: S(lambda i: i.setY(float(v))))
        P.width_changed.connect(       lambda v: S(lambda i: i.set_width(v)))
        P.height_changed.connect(      lambda v: S(lambda i: i.set_height(v)))
        P.delete_requested.connect(self._on_delete_selected)

        return self._props

    # ------------------------------------------------------------------
    # First show: fit canvas into view
    # ------------------------------------------------------------------

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not self._initial_fit_done:
            self._canvas.fitInView(
                self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio
            )
            self._sync_zoom_label()
            self._initial_fit_done = True

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_excel_headers(self, headers: list[str]) -> None:
        """Receive column headers from DashboardView and forward to panel."""
        self._excel_headers = headers
        self._props.set_excel_headers(headers)

    def get_template_state(self) -> dict:
        """Returns the current template dictionary state."""
        return self._get_state()


    # ------------------------------------------------------------------
    # Toolbar action slots
    # ------------------------------------------------------------------

    def _on_upload_bg(self) -> None:
        if _HAS_PYMUPDF:
            flt = "Images & PDF (*.png *.jpg *.jpeg *.bmp *.pdf);;All Files (*)"
        else:
            flt = "Images (*.png *.jpg *.jpeg *.bmp);;All Files (*)"

        path, _ = QFileDialog.getOpenFileName(self, "Upload Background", "", flt)
        if not path:
            return
        pixmap, bg_type = self._load_as_pixmap(path)
        if pixmap:
            self._set_background(pixmap, bg_type, path)

    def _on_add_field(self) -> None:
        self._field_counter += 1
        label = f"Field_{self._field_counter}"
        centre = self._canvas.mapToScene(
            self._canvas.viewport().rect().center()
        )
        item = FieldItem(
            label=label,
            x=centre.x() - 100.0,
            y=centre.y() - 18.0,
        )
        # Pre-populate column dropdown choices from loaded headers
        if self._excel_headers:
            item.mapped_column = ""   # user maps explicitly in the panel

        self._register_field(item)
        self._scene.clearSelection()
        item.setSelected(True)

    def _on_delete_selected(self) -> None:
        to_remove = [i for i in self._scene.selectedItems() if isinstance(i, FieldItem)]
        for item in to_remove:
            self._scene.removeItem(item)
            if item in self._field_items:
                self._field_items.remove(item)
        self._del_btn.setEnabled(False)

    def _on_save_template(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Template", _TEMPLATES_DIR,
            "Template Files (*.json);;All Files (*)"
        )
        if not path:
            return
        if not path.endswith(".json"):
            path += ".json"
        state = self._get_state()
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(state, fh, indent=2, ensure_ascii=False)
        except OSError as exc:
            QMessageBox.critical(self, "Save Error", f"Could not save:\n{exc}")
        else:
            QMessageBox.information(self, "Saved", f"Template saved:\n{path}")

    def _on_load_template(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Template", _TEMPLATES_DIR,
            "Template Files (*.json);;All Files (*)"
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as fh:
                state = json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            QMessageBox.critical(self, "Load Error", f"Cannot read template:\n{exc}")
            return
        self._restore_state(state)

    # ------------------------------------------------------------------
    # Scene event
    # ------------------------------------------------------------------

    def _on_selection_changed(self) -> None:
        items = [i for i in self._scene.selectedItems() if isinstance(i, FieldItem)]

        # Disconnect position/geometry signals from the old item
        if self._selected_item is not None:
            try:
                self._selected_item.position_changed.disconnect(
                    self._props.update_position
                )
                self._selected_item.geometry_changed.disconnect(
                    self._props.update_geometry
                )
            except RuntimeError:
                pass

        self._selected_item = items[0] if items else None

        # Connect to new item
        if self._selected_item is not None:
            self._selected_item.position_changed.connect(self._props.update_position)
            self._selected_item.geometry_changed.connect(self._props.update_geometry)

        self._props.load_item(self._selected_item)
        self._del_btn.setEnabled(self._selected_item is not None)

    # ------------------------------------------------------------------
    # Background management
    # ------------------------------------------------------------------

    def _load_as_pixmap(self, path: str) -> tuple[QPixmap | None, str]:
        ext = os.path.splitext(path)[1].lower()

        if ext == ".pdf":
            if not _HAS_PYMUPDF:
                QMessageBox.warning(
                    self, "PyMuPDF Missing",
                    "Install PyMuPDF to use PDF backgrounds:\n  pip install PyMuPDF"
                )
                return None, ""
            try:
                doc  = pymupdf.open(path)
                page = doc[0]
                mat  = pymupdf.Matrix(2.0, 2.0)   # 2x for crisp rendering
                pix  = page.get_pixmap(matrix=mat)
                doc.close()
                qpix = QPixmap()
                qpix.loadFromData(bytes(pix.tobytes("png")))
                return qpix, "pdf"
            except Exception as exc:
                QMessageBox.critical(self, "PDF Error", f"Could not render PDF:\n{exc}")
                return None, ""

        # Image formats
        qpix = QPixmap(path)
        if qpix.isNull():
            QMessageBox.critical(self, "Image Error", f"Could not load image:\n{path}")
            return None, ""
        return qpix, "image"

    def _set_background(self, pixmap: QPixmap, bg_type: str, bg_path: str) -> None:
        if self._bg_item is not None:
            self._scene.removeItem(self._bg_item)

        self._bg_item = QGraphicsPixmapItem(pixmap)
        self._bg_item.setZValue(0)
        self._bg_item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable,    False)
        self._bg_item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        self._scene.addItem(self._bg_item)
        self._scene.setSceneRect(QRectF(pixmap.rect()))
        self._canvas.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self._sync_zoom_label()

        self._bg_type = bg_type
        self._bg_path = bg_path

    # ------------------------------------------------------------------
    # Field management
    # ------------------------------------------------------------------

    def _register_field(self, item: FieldItem) -> None:
        self._scene.addItem(item)
        self._field_items.append(item)

    # ------------------------------------------------------------------
    # Zoom helpers
    # ------------------------------------------------------------------

    def _do_zoom(self, factor: float) -> None:
        self._canvas.scale(factor, factor)
        self._sync_zoom_label()

    def _reset_zoom(self) -> None:
        if self._scene.sceneRect().isValid():
            self._canvas.fitInView(
                self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio
            )
        else:
            self._canvas.resetTransform()
        self._sync_zoom_label()

    def _sync_zoom_label(self) -> None:
        pct = round(self._canvas.transform().m11() * 100)
        self._zoom_lbl.setText(f"{pct}%")

    # ------------------------------------------------------------------
    # JSON serialization
    # ------------------------------------------------------------------

    def _get_state(self) -> dict:
        sr = self._scene.sceneRect()
        return {
            "version"   : "1.0",
            "background": {"type": self._bg_type, "path": self._bg_path},
            "canvas"    : {"width": round(sr.width()), "height": round(sr.height())},
            "fields"    : [item.to_dict() for item in self._field_items],
        }

    def _restore_state(self, state: dict) -> None:
        # Clear existing fields
        for item in list(self._field_items):
            self._scene.removeItem(item)
        self._field_items.clear()
        self._selected_item = None
        self._props.load_item(None)

        # Restore background
        bg      = state.get("background", {})
        bg_path = bg.get("path", "")
        bg_type = bg.get("type", "")
        if bg_path:
            if os.path.exists(bg_path):
                pixmap, resolved = self._load_as_pixmap(bg_path)
                if pixmap:
                    self._set_background(pixmap, resolved, bg_path)
            else:
                QMessageBox.warning(
                    self, "Background Not Found",
                    f"Could not find:\n{bg_path}\n\nFields will still be restored."
                )

        # Restore fields
        for fdata in state.get("fields", []):
            item = FieldItem.from_dict(fdata)
            self._register_field(item)

        if self._field_items:
            # Try to infer the counter from stored labels so new fields don't clash
            nums = []
            for it in self._field_items:
                parts = it.label.rsplit("_", 1)
                if len(parts) == 2 and parts[1].isdigit():
                    nums.append(int(parts[1]))
            if nums:
                self._field_counter = max(nums)

    # ------------------------------------------------------------------
    # Widget factory helpers
    # ------------------------------------------------------------------

    def _on_sel(self, fn) -> None:
        """Apply fn(item) to the currently selected FieldItem, if any."""
        if self._selected_item is not None:
            fn(self._selected_item)

    def _mkbtn(
        self,
        text: str,
        bg: str | None = None,
        hover: str | None = None,
        *,
        outline: bool = False,
    ) -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedHeight(34)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        if outline:
            btn.setStyleSheet("""
                QPushButton {
                    background: white; color: #374151;
                    border: 1px solid #d1d5db; border-radius: 5px;
                    padding: 0 14px; font-size: 12px; font-weight: 600;
                }
                QPushButton:hover { background: #f3f4f6; }
            """)
        else:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {bg}; color: white;
                    border: none; border-radius: 5px;
                    padding: 0 14px; font-size: 12px; font-weight: 600;
                }}
                QPushButton:hover    {{ background: {hover}; }}
                QPushButton:disabled {{ background: #d1d5db; color: #9ca3af; }}
            """)
        return btn

    @staticmethod
    def _zkbtn(text: str, width: int = 24) -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedSize(width, 26)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                background: white; color: #374151;
                border: 1px solid #d1d5db; border-radius: 4px;
                font-size: 13px; font-weight: 700;
            }
            QPushButton:hover { background: #f3f4f6; }
        """)
        return btn

    @staticmethod
    def _vdivider() -> QFrame:
        div = QFrame()
        div.setFrameShape(QFrame.Shape.VLine)
        div.setFixedHeight(28)
        div.setStyleSheet("color: #e5e7eb;")
        return div
