"""
Template Editor placeholder view.
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt


class TemplateEditorView(QWidget):
    """Placeholder template editor screen."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon = QLabel("🖊️")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet("font-size: 52px;")

        title = QLabel("Template Editor")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("""
            font-size: 26px;
            font-weight: 700;
            color: #1a1a2e;
            margin-top: 12px;
        """)

        subtitle = QLabel("Design your result template by uploading a background\nand placing text placeholders.")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("font-size: 14px; color: #6b7280;")

        layout.addWidget(icon)
        layout.addWidget(title)
        layout.addWidget(subtitle)
