"""
Template Editor view.

Features:
- Visual canvas with image / PDF background rendering.
- Draggable & resizable FieldItem placement.
- Draggable & resizable ChartItem placement (performance chart placeholder).
- Duplicate field name validation.
- Template / Dataset Locking mode when active dataset is loaded.
- Export blank Excel Dataset matching template field structure.
- Save / Load JSON template with embedded template UUID.
- Dirty state tracking and confirmation guards.
"""
from __future__ import annotations

import json
import os
import uuid

from PyQt6.QtCore import QRectF, Qt
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
import pymupdf

from data_engine.excel_loader import export_blank_excel_template
from data_engine.header_normalizer import find_matching_header
from ui.widgets.badge_item import BadgeItem
from ui.widgets.chart_item import ChartItem
from ui.widgets.field_item import FieldItem
from ui.widgets.properties_panel import PropertiesPanel
from utils.constants import TEMPLATES_DIR


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


class TemplateEditorView(QWidget):
    """Visual template designer with background overlay and field / chart / badge mapping."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._template_id: str = str(uuid.uuid4())
        self._template_name: str = "Untitled_Template"
        self._field_items: list[FieldItem] = []
        self._chart_items: list[ChartItem] = []
        self._badge_items: list[BadgeItem] = []
        self._field_counter: int = 0
        self._chart_counter: int = 0
        self._badge_counter: int = 0
        self._bg_item: QGraphicsPixmapItem | None = None
        self._bg_type: str = ""
        self._bg_path: str = ""
        self._selected_item: FieldItem | ChartItem | BadgeItem | None = None
        self._excel_headers: list[str] = []
        self._initial_fit_done: bool = False
        self._has_unsaved_changes: bool = False
        self._is_locked: bool = False
        self._snap_to_grid: bool = True

        self._build_ui()

    # ── UI Construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # 1. Toolbar
        toolbar = self._build_toolbar()
        outer.addWidget(toolbar)

        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet("color: #e5e7eb; margin: 0;")
        outer.addWidget(div)

        # 2. Main content
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Canvas scene & view
        self._scene = QGraphicsScene(self)
        self._scene.setSceneRect(0, 0, 794, 1123)  # A4 at 96 dpi default
        self._scene.selectionChanged.connect(self._on_selection_changed)

        self._view = _CanvasView(self._scene, self)
        main_layout.addWidget(self._view, stretch=1)

        # Properties panel
        self._panel = PropertiesPanel(self)
        self._connect_panel_signals()
        main_layout.addWidget(self._panel)

        outer.addLayout(main_layout, stretch=1)

    def _build_toolbar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(54)
        bar.setStyleSheet("background: #f9fafb;")

        row = QHBoxLayout(bar)
        row.setContentsMargins(16, 0, 16, 0)
        row.setSpacing(8)

        title = QLabel("Template Editor")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #1a1a2e;")
        row.addWidget(title)

        # Lock badge
        self._lock_badge = QLabel("🔒 Template Locked (Active Dataset Loaded)")
        self._lock_badge.setStyleSheet("""
            background: #fef3c7; color: #92400e; font-size: 11px;
            font-weight: 600; padding: 4px 8px; border-radius: 4px;
        """)
        self._lock_badge.hide()
        row.addWidget(self._lock_badge)

        row.addSpacing(12)

        # Action Buttons
        self._bg_btn          = self._tool_btn("🖼  Upload Background",      self._on_upload_bg)
        self._add_btn         = self._tool_btn("➕  Add Field",               self._on_add_field)
        self._add_chart_btn   = self._tool_btn("📊  Add Chart",               self._on_add_chart)
        self._add_badge_btn   = self._tool_btn("🎖  Add Badge",               self._on_add_badge)
        self._snap_btn        = QPushButton("🧲  Snap to Grid")
        self._snap_btn.setCheckable(True)
        self._snap_btn.setChecked(True)
        self._snap_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._snap_btn.setToolTip("Toggle magnetic snap to 10px grid boundaries")
        self._update_snap_btn_style()
        self._snap_btn.toggled.connect(self._on_toggle_snap)

        # Multi-Item Alignment Buttons
        self._align_left_btn   = self._tool_btn("⇤  Left",      self._on_align_left)
        self._align_left_btn.setToolTip("Align selected items to the leftmost X coordinate (select 2+ items)")
        self._align_left_btn.setEnabled(False)

        self._align_center_btn = self._tool_btn("⇥⇤  Center",  self._on_align_center)
        self._align_center_btn.setToolTip("Align selected items to the horizontal midpoint (select 2+ items)")
        self._align_center_btn.setEnabled(False)

        self._align_right_btn  = self._tool_btn("⇥  Right",     self._on_align_right)
        self._align_right_btn.setToolTip("Align selected items to the rightmost edge (select 2+ items)")
        self._align_right_btn.setEnabled(False)

        self._distribute_v_btn = self._tool_btn("↕  Distribute", self._on_distribute_vertically)
        self._distribute_v_btn.setToolTip("Evenly distribute vertical spacing between 3+ selected items")
        self._distribute_v_btn.setEnabled(False)

        self._export_excel_btn = self._tool_btn("📊  Export Excel Template",  self._on_export_excel)
        self._save_btn        = self._tool_btn("💾  Save Template",           self._on_save_template)
        self._load_btn        = self._tool_btn("📂  Open Template",           self._on_load_template)

        # Style the Add Chart button distinctively
        self._add_chart_btn.setStyleSheet("""
            QPushButton {
                background: #eff6ff; color: #1d4ed8; border: 1px solid #93c5fd;
                border-radius: 4px; padding: 6px 12px; font-size: 12px; font-weight: 600;
            }
            QPushButton:hover { background: #dbeafe; }
        """)

        # Style the Add Badge button distinctively
        self._add_badge_btn.setStyleSheet("""
            QPushButton {
                background: #fffbeb; color: #b45309; border: 1px solid #fde68a;
                border-radius: 4px; padding: 6px 12px; font-size: 12px; font-weight: 600;
            }
            QPushButton:hover { background: #fef3c7; }
        """)

        row.addWidget(self._bg_btn)
        row.addWidget(self._add_btn)
        row.addWidget(self._add_chart_btn)
        row.addWidget(self._add_badge_btn)
        row.addWidget(self._snap_btn)
        row.addWidget(self._align_left_btn)
        row.addWidget(self._align_center_btn)
        row.addWidget(self._align_right_btn)
        row.addWidget(self._distribute_v_btn)
        row.addWidget(self._export_excel_btn)
        row.addWidget(self._save_btn)
        row.addWidget(self._load_btn)

        row.addStretch()

        # Zoom controls
        zoom_out = self._icon_btn("−", lambda: self._view.scale(1 / 1.2, 1 / 1.2))
        zoom_in  = self._icon_btn("+", lambda: self._view.scale(1.2, 1.2))
        zoom_fit = self._tool_btn("Fit", self._fit_to_view)

        row.addWidget(zoom_out)
        row.addWidget(zoom_in)
        row.addWidget(zoom_fit)

        return bar

    def _connect_panel_signals(self) -> None:
        p = self._panel

        # ── Field-only signals ──────────────────────────────────────────
        p.label_changed.connect(self._on_label_changed)
        p.column_changed.connect(
            lambda c: self._apply_to_field(lambda i: i.set_mapped_column(c))
        )
        p.unique_changed.connect(
            lambda u: self._apply_to_field(lambda i: i.set_is_unique(u))
        )
        p.font_family_changed.connect(
            lambda f: self._apply_to_field(lambda i: i.set_font_family(f))
        )
        p.font_size_changed.connect(
            lambda s: self._apply_to_field(lambda i: i.set_font_size(s))
        )
        p.color_changed.connect(
            lambda c: self._apply_to_field(lambda i: i.set_color(c))
        )
        p.bold_changed.connect(
            lambda b: self._apply_to_field(lambda i: i.set_bold(b))
        )
        p.italic_changed.connect(
            lambda it: self._apply_to_field(lambda i: i.set_italic(it))
        )
        p.underline_changed.connect(
            lambda un: self._apply_to_field(lambda i: i.set_underline(un))
        )
        p.multiline_changed.connect(
            lambda ml: self._apply_to_field(lambda i: i.set_multiline(ml))
        )
        p.alignment_changed.connect(
            lambda a: self._apply_to_field(lambda i: i.set_alignment(a))
        )
        p.v_alignment_changed.connect(
            lambda va: self._apply_to_field(lambda i: i.set_v_alignment(va))
        )

        # ── Geometry (shared by FieldItem, ChartItem, BadgeItem) ───────
        p.x_changed.connect(self._on_panel_x)
        p.y_changed.connect(self._on_panel_y)
        p.width_changed.connect(self._on_panel_width)
        p.height_changed.connect(self._on_panel_height)
        p.delete_requested.connect(self._on_delete_selected)

        # ── Chart-only signals ──────────────────────────────────────────
        p.chart_columns_changed.connect(
            lambda cols: self._apply_to_chart(lambda i: i.set_chart_columns(cols))
        )
        p.chart_style_changed.connect(
            lambda s: self._apply_to_chart(lambda i: i.set_chart_style(s))
        )

        # ── Badge-only signals ──────────────────────────────────────────
        p.badge_image_changed.connect(
            lambda path: self._apply_to_badge(lambda i: i.set_badge_image(path))
        )
        p.badge_rule_changed.connect(
            lambda col, op, val: self._apply_to_badge(lambda i: i.set_rule(col, op, val))
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def set_excel_columns(self, headers: list[str]) -> None:
        self._excel_headers = list(headers)
        if headers:
            for f in self._field_items:
                if not f.mapped_column or f.mapped_column not in headers:
                    matched = find_matching_header(f.label, headers)
                    if matched:
                        f.set_mapped_column(matched)
        self._panel.set_excel_columns(headers)
        if self._selected_item:
            self._panel.load_item(self._selected_item)

    def set_locked_state(self, locked: bool, reason: str = "") -> None:
        """Lock or unlock template field modifications when an active dataset is attached."""
        self._is_locked = locked
        self._add_btn.setEnabled(not locked)
        self._add_chart_btn.setEnabled(not locked)
        self._add_badge_btn.setEnabled(not locked)
        self._bg_btn.setEnabled(not locked)
        if locked:
            self._lock_badge.setText(f"🔒 {reason or 'Template Locked (Dataset Active)'}")
            self._lock_badge.show()
        else:
            self._lock_badge.hide()

    def has_unsaved_changes(self) -> bool:
        return self._has_unsaved_changes

    def get_state(self) -> dict:
        return self._get_state()

    def get_template_fields(self) -> list[str]:
        """Return list of all field labels in canvas order (chart items excluded)."""
        return [f.label for f in self._field_items]

    def _update_snap_btn_style(self) -> None:
        if hasattr(self, "_snap_btn"):
            if self._snap_btn.isChecked():
                self._snap_btn.setStyleSheet("""
                    QPushButton {
                        background: #dbeafe; color: #1e40af; border: 1px solid #3b82f6;
                        border-radius: 4px; padding: 6px 12px; font-size: 12px; font-weight: 600;
                    }
                    QPushButton:hover { background: #bfdbfe; }
                """)
            else:
                self._snap_btn.setStyleSheet("""
                    QPushButton {
                        background: #f3f4f6; color: #6b7280; border: 1px solid #d1d5db;
                        border-radius: 4px; padding: 6px 12px; font-size: 12px; font-weight: 600;
                    }
                    QPushButton:hover { background: #e5e7eb; color: #374151; }
                """)

    def _on_toggle_snap(self, checked: bool) -> None:
        self._snap_to_grid = checked
        self._update_snap_btn_style()
        for item in self._all_canvas_items():
            item.set_snap_to_grid(checked, 10.0)

    def _all_canvas_items(self) -> list[FieldItem | ChartItem | BadgeItem]:
        return list(self._field_items) + list(self._chart_items) + list(self._badge_items)

    # ── Actions ───────────────────────────────────────────────────────────────

    def _on_add_field(self) -> None:
        if self._is_locked:
            QMessageBox.warning(self, "Template Locked", "Cannot add fields while a dataset is active.")
            return

        self._field_counter += 1
        name = f"Field_{self._field_counter}"
        existing = {f.label.lower() for f in self._field_items}
        while name.lower() in existing:
            self._field_counter += 1
            name = f"Field_{self._field_counter}"

        rect = self._scene.sceneRect()
        cx = rect.center().x() - 100
        cy = rect.center().y() - 18
        if self._snap_to_grid:
            cx = round(cx / 10.0) * 10.0
            cy = round(cy / 10.0) * 10.0

        item = FieldItem(label=name, x=cx, y=cy, width=200, height=36)
        item.set_snap_to_grid(self._snap_to_grid, 10.0)
        if self._excel_headers:
            matched = find_matching_header(name, self._excel_headers)
            if matched:
                item.set_mapped_column(matched)

        item.position_changed.connect(lambda x, y: self._on_item_moved(item, x, y))
        item.geometry_changed.connect(lambda w, h: self._on_item_resized(item, w, h))

        self._scene.addItem(item)
        self._field_items.append(item)

        self._scene.clearSelection()
        item.setSelected(True)
        self._mark_dirty()

    def _on_add_chart(self) -> None:
        if self._is_locked:
            QMessageBox.warning(self, "Template Locked", "Cannot add charts while a dataset is active.")
            return

        self._chart_counter += 1
        rect = self._scene.sceneRect()
        cx = rect.center().x() - 150
        cy = rect.center().y() - 100
        if self._snap_to_grid:
            cx = round(cx / 10.0) * 10.0
            cy = round(cy / 10.0) * 10.0

        item = ChartItem(
            label=f"Performance Chart {self._chart_counter}",
            x=cx, y=cy, width=300, height=200,
        )
        item.set_snap_to_grid(self._snap_to_grid, 10.0)
        # Pre-select all numeric-looking columns if headers already loaded
        if self._excel_headers:
            item.chart_columns = list(self._excel_headers)

        item.position_changed.connect(lambda x, y: self._on_item_moved(item, x, y))
        item.geometry_changed.connect(lambda w, h: self._on_item_resized(item, w, h))

        self._scene.addItem(item)
        self._chart_items.append(item)

        self._scene.clearSelection()
        item.setSelected(True)
        self._mark_dirty()

    def _on_add_badge(self) -> None:
        if self._is_locked:
            QMessageBox.warning(self, "Template Locked", "Cannot add badges while a dataset is active.")
            return

        self._badge_counter += 1
        rect = self._scene.sceneRect()
        cx = rect.center().x() - 50
        cy = rect.center().y() - 50
        if self._snap_to_grid:
            cx = round(cx / 10.0) * 10.0
            cy = round(cy / 10.0) * 10.0

        item = BadgeItem(
            label=f"Badge {self._badge_counter}",
            x=cx, y=cy, width=100, height=100,
        )
        item.set_snap_to_grid(self._snap_to_grid, 10.0)
        if self._excel_headers:
            item.rule_column = self._excel_headers[0]

        item.position_changed.connect(lambda x, y, it=item: self._on_item_moved(it, x, y))
        item.geometry_changed.connect(lambda w, h, it=item: self._on_item_resized(it, w, h))

        self._scene.addItem(item)
        self._badge_items.append(item)

        self._scene.clearSelection()
        item.setSelected(True)
        self._mark_dirty()

    def _on_label_changed(self, new_label: str) -> None:
        if not isinstance(self._selected_item, FieldItem):
            return
        clean = new_label.strip()
        # Prevent duplicate labels
        for f in self._field_items:
            if f is not self._selected_item and f.label.lower() == clean.lower():
                QMessageBox.warning(self, "Duplicate Field Name",
                                    f"A field with name '{clean}' already exists.")
                return
        self._selected_item.set_label(clean or "Field")
        self._mark_dirty()

    def _on_delete_selected(self) -> None:
        if self._is_locked:
            QMessageBox.warning(self, "Template Locked",
                                "Cannot delete items while a dataset is active.")
            return

        if not self._selected_item:
            return

        item = self._selected_item
        self._scene.removeItem(item)
        if isinstance(item, ChartItem) and item in self._chart_items:
            self._chart_items.remove(item)
        elif isinstance(item, BadgeItem) and item in self._badge_items:
            self._badge_items.remove(item)
        elif isinstance(item, FieldItem) and item in self._field_items:
            self._field_items.remove(item)

        self._selected_item = None
        self._panel.load_item(None)
        self._mark_dirty()

    def _on_upload_bg(self) -> None:
        if self._is_locked:
            QMessageBox.warning(self, "Template Locked",
                                "Cannot change background while a dataset is active.")
            return

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Background (Image or PDF)",
            "",
            "All Backgrounds (*.png *.jpg *.jpeg *.pdf);;Images (*.png *.jpg *.jpeg);;PDF Files (*.pdf)",
        )
        if path:
            self._load_background_file(path)
            self._mark_dirty()

    def _load_background_file(self, path: str) -> None:
        if path.lower().endswith(".pdf"):
            doc = pymupdf.open(path)
            page = doc[0]
            pix = page.get_pixmap(dpi=150)
            qpix = QPixmap()
            qpix.loadFromData(pix.tobytes("png"))
            doc.close()
            self._set_background(qpix, "pdf", path)
        else:
            qpix = QPixmap(path)
            if not qpix.isNull():
                self._set_background(qpix, "image", path)

    def _set_background(self, pixmap: QPixmap, bg_type: str, path: str) -> None:
        if self._bg_item:
            self._scene.removeItem(self._bg_item)
            self._bg_item = None

        self._bg_item = QGraphicsPixmapItem(pixmap)
        self._bg_item.setZValue(0)
        self._scene.addItem(self._bg_item)
        self._scene.setSceneRect(QRectF(pixmap.rect()))
        self._bg_type = bg_type
        self._bg_path = path
        self._fit_to_view()

    def _on_export_excel(self) -> None:
        """Export empty Excel sheet containing columns matching template fields."""
        fields = [f.mapped_column or f.label for f in self._field_items]
        if not fields:
            QMessageBox.warning(self, "No Fields",
                                "Please add at least one field to the template before exporting an Excel sheet.")
            return

        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Blank Excel Dataset Template",
            f"{self._template_name}_Dataset.xlsx",
            "Excel Files (*.xlsx)",
        )
        if save_path:
            try:
                export_blank_excel_template(save_path, fields)
                QMessageBox.information(
                    self,
                    "Excel Template Exported",
                    f"Blank Excel dataset template exported successfully:\n{save_path}",
                )
            except Exception as exc:
                QMessageBox.critical(self, "Export Failed", f"Failed to export Excel template:\n{exc}")

    def _on_save_template(self) -> bool:
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Template State",
            os.path.join(TEMPLATES_DIR, f"{self._template_name}.json"),
            "Template Files (*.json)",
        )
        if not save_path:
            return False

        try:
            state = self._get_state()
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
            self._has_unsaved_changes = False
            self._template_name = os.path.splitext(os.path.basename(save_path))[0]
            QMessageBox.information(self, "Saved", f"Template saved successfully:\n{save_path}")
            return True
        except Exception as exc:
            QMessageBox.critical(self, "Save Error", f"Failed to save template:\n{exc}")
            return False

    def _on_load_template(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Template File",
            TEMPLATES_DIR,
            "Template Files (*.json)",
        )
        if path:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    state = json.load(f)
                self._restore_state(state)
                self._has_unsaved_changes = False
                self._template_name = os.path.splitext(os.path.basename(path))[0]
            except Exception as exc:
                QMessageBox.critical(self, "Load Error", f"Failed to load template:\n{exc}")

    def _get_state(self) -> dict:
        r = self._scene.sceneRect()
        return {
            "version"      : "1.0",
            "template_id"  : self._template_id,
            "template_name": self._template_name,
            "canvas_width" : round(r.width(),  2),
            "canvas_height": round(r.height(), 2),
            "background": {
                "type": self._bg_type,
                "path": self._bg_path,
            },
            "fields": [f.to_dict() for f in self._field_items],
            "charts": [c.to_dict() for c in self._chart_items],
            "badges": [b.to_dict() for b in self._badge_items],
        }

    def _restore_state(self, d: dict) -> None:
        # Clear fields
        for f in self._field_items:
            self._scene.removeItem(f)
        self._field_items.clear()

        # Clear charts
        for c in self._chart_items:
            self._scene.removeItem(c)
        self._chart_items.clear()

        # Clear badges
        for b in self._badge_items:
            self._scene.removeItem(b)
        self._badge_items.clear()

        self._selected_item = None
        self._panel.load_item(None)

        self._template_id   = d.get("template_id",   str(uuid.uuid4()))
        self._template_name = d.get("template_name", "Template")

        # Background
        bg      = d.get("background", {})
        bg_path = bg.get("path", "")
        if bg_path and os.path.exists(bg_path):
            self._load_background_file(bg_path)
        else:
            w = d.get("canvas_width",  794.0)
            h = d.get("canvas_height", 1123.0)
            self._scene.setSceneRect(0, 0, w, h)

        # Fields
        for fd in d.get("fields", []):
            item = FieldItem.from_dict(fd)
            item.set_snap_to_grid(self._snap_to_grid, 10.0)
            item.position_changed.connect(lambda x, y, it=item: self._on_item_moved(it, x, y))
            item.geometry_changed.connect(lambda w, h, it=item: self._on_item_resized(it, w, h))
            self._scene.addItem(item)
            self._field_items.append(item)

        # Charts
        for cd in d.get("charts", []):
            item = ChartItem.from_dict(cd)
            item.set_snap_to_grid(self._snap_to_grid, 10.0)
            item.position_changed.connect(lambda x, y, it=item: self._on_item_moved(it, x, y))
            item.geometry_changed.connect(lambda w, h, it=item: self._on_item_resized(it, w, h))
            self._scene.addItem(item)
            self._chart_items.append(item)

        # Badges
        for bd in d.get("badges", []):
            item = BadgeItem.from_dict(bd)
            item.set_snap_to_grid(self._snap_to_grid, 10.0)
            item.position_changed.connect(lambda x, y, it=item: self._on_item_moved(it, x, y))
            item.geometry_changed.connect(lambda w, h, it=item: self._on_item_resized(it, w, h))
            self._scene.addItem(item)
            self._badge_items.append(item)

        self._fit_to_view()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _fit_to_view(self) -> None:
        r = self._scene.sceneRect()
        if not r.isEmpty():
            self._view.fitInView(r, Qt.AspectRatioMode.KeepAspectRatio)

    def _mark_dirty(self) -> None:
        self._has_unsaved_changes = True

    def _on_selection_changed(self) -> None:
        items = self._selected_canvas_items()
        self._selected_item = items[0] if items else None
        self._panel.load_item(self._selected_item)

        count = len(items)
        if hasattr(self, "_align_left_btn"):
            self._align_left_btn.setEnabled(count >= 2)
            self._align_center_btn.setEnabled(count >= 2)
            self._align_right_btn.setEnabled(count >= 2)
            self._distribute_v_btn.setEnabled(count >= 3)

    def _selected_canvas_items(self) -> list[FieldItem | ChartItem | BadgeItem]:
        sel = self._scene.selectedItems()
        return [i for i in sel if isinstance(i, (FieldItem, ChartItem, BadgeItem))]

    # ── Alignment Actions ─────────────────────────────────────────────────────

    def _on_align_left(self) -> None:
        items = self._selected_canvas_items()
        if len(items) < 2:
            return
        min_x = min(it.pos().x() for it in items)
        if self._snap_to_grid:
            min_x = round(min_x / 10.0) * 10.0
        for it in items:
            it.setX(min_x)
            self._on_item_moved(it, it.pos().x(), it.pos().y())
        self._mark_dirty()

    def _on_align_center(self) -> None:
        items = self._selected_canvas_items()
        if len(items) < 2:
            return
        min_left = min(it.pos().x() for it in items)
        max_right = max(it.pos().x() + it.width for it in items)
        mid_x = (min_left + max_right) / 2.0
        for it in items:
            target_x = mid_x - (it.width / 2.0)
            if self._snap_to_grid:
                target_x = round(target_x / 10.0) * 10.0
            it.setX(target_x)
            self._on_item_moved(it, it.pos().x(), it.pos().y())
        self._mark_dirty()

    def _on_align_right(self) -> None:
        items = self._selected_canvas_items()
        if len(items) < 2:
            return
        max_right = max(it.pos().x() + it.width for it in items)
        for it in items:
            target_x = max_right - it.width
            if self._snap_to_grid:
                target_x = round(target_x / 10.0) * 10.0
            it.setX(target_x)
            self._on_item_moved(it, it.pos().x(), it.pos().y())
        self._mark_dirty()

    def _on_distribute_vertically(self) -> None:
        items = self._selected_canvas_items()
        if len(items) < 3:
            return
        sorted_items = sorted(items, key=lambda it: it.pos().y())
        total_items_height = sum(it.height for it in sorted_items)
        top_y = sorted_items[0].pos().y()
        bottom_edge = sorted_items[-1].pos().y() + sorted_items[-1].height
        total_span = bottom_edge - top_y
        total_gap = total_span - total_items_height

        if total_gap > 0:
            gap = total_gap / (len(sorted_items) - 1)
            curr_y = top_y
            for it in sorted_items:
                target_y = curr_y
                if self._snap_to_grid:
                    target_y = round(target_y / 10.0) * 10.0
                it.setY(target_y)
                self._on_item_moved(it, it.pos().x(), it.pos().y())
                curr_y += it.height + gap
        else:
            step = (sorted_items[-1].pos().y() - top_y) / (len(sorted_items) - 1)
            for idx, it in enumerate(sorted_items):
                target_y = top_y + idx * step
                if self._snap_to_grid:
                    target_y = round(target_y / 10.0) * 10.0
                it.setY(target_y)
                self._on_item_moved(it, it.pos().x(), it.pos().y())
        self._mark_dirty()

    def _on_item_moved(self, item: FieldItem | ChartItem | BadgeItem, x: float, y: float) -> None:
        if item is self._selected_item:
            self._panel.update_position(x, y)
        self._mark_dirty()

    def _on_item_resized(self, item: FieldItem | ChartItem | BadgeItem, w: float, h: float) -> None:
        if item is self._selected_item:
            self._panel.update_geometry(w, h)
        self._mark_dirty()

    def _on_panel_x(self, x: float) -> None:
        if self._selected_item:
            self._selected_item.setX(x)
            self._mark_dirty()

    def _on_panel_y(self, y: float) -> None:
        if self._selected_item:
            self._selected_item.setY(y)
            self._mark_dirty()

    def _on_panel_width(self, w: float) -> None:
        if self._selected_item:
            self._selected_item.set_field_size(w, self._selected_item.height)
            self._mark_dirty()

    def _on_panel_height(self, h: float) -> None:
        if self._selected_item:
            self._selected_item.set_field_size(self._selected_item.width, h)
            self._mark_dirty()

    def _apply_to_field(self, fn) -> None:
        """Apply fn only when selected item is a FieldItem."""
        if isinstance(self._selected_item, FieldItem):
            fn(self._selected_item)
            self._mark_dirty()

    def _apply_to_chart(self, fn) -> None:
        """Apply fn only when selected item is a ChartItem."""
        if isinstance(self._selected_item, ChartItem):
            fn(self._selected_item)
            self._mark_dirty()

    def _apply_to_badge(self, fn) -> None:
        """Apply fn only when selected item is a BadgeItem."""
        if isinstance(self._selected_item, BadgeItem):
            fn(self._selected_item)
            self._mark_dirty()

    # ── Button factory helpers ────────────────────────────────────────────────

    def _tool_btn(self, text: str, slot) -> QPushButton:
        btn = QPushButton(text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                background: #ffffff; color: #374151; border: 1px solid #d1d5db;
                border-radius: 4px; padding: 6px 12px; font-size: 12px; font-weight: 600;
            }
            QPushButton:hover { background: #f3f4f6; color: #111827; }
            QPushButton:disabled { background: #f9fafb; color: #9ca3af; border-color: #e5e7eb; }
        """)
        btn.clicked.connect(slot)
        return btn

    def _icon_btn(self, text: str, slot) -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedSize(30, 30)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                background: #ffffff; color: #374151; border: 1px solid #d1d5db;
                border-radius: 4px; font-size: 14px; font-weight: 700;
            }
            QPushButton:hover { background: #f3f4f6; color: #111827; }
        """)
        btn.clicked.connect(slot)
        return btn
