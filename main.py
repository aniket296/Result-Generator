"""
Entry point for the Teacher Result Management System.
"""
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont
from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("TeacherResultSoftware")
    app.setOrganizationName("TeacherResultSoftware")

    # Global default font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # Global High-Contrast Stylesheet ensuring black/dark text on light elements and white text on dark elements
    app.setStyleSheet("""
        /* All text-input widgets: black text on white background */
        QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox,
        QComboBox, QFontComboBox, QListWidget, QTableWidget {
            color: #000000;
            background-color: #ffffff;
            selection-background-color: #4f7ef8;
            selection-color: #ffffff;
        }

        /* Dropdown list popups */
        QComboBox QAbstractItemView {
            color: #000000;
            background-color: #ffffff;
            selection-background-color: #eff6ff;
            selection-color: #1d4ed8;
        }

        /* Default Buttons: dark text on light background with visible border */
        QPushButton {
            color: #111827;
            background-color: #ffffff;
            border: 1px solid #d1d5db;
            border-radius: 4px;
            padding: 6px 12px;
            font-weight: 500;
        }
        QPushButton:hover {
            background-color: #f3f4f6;
            color: #111827;
        }
        QPushButton:pressed {
            background-color: #e5e7eb;
            color: #111827;
        }
        QPushButton:disabled {
            color: #9ca3af;
            background-color: #f3f4f6;
            border-color: #e5e7eb;
        }

        /* MessageBox & Dialog standard buttons */
        QMessageBox QPushButton, QDialogButtonBox QPushButton {
            color: #111827;
            background-color: #ffffff;
            border: 1px solid #d1d5db;
            border-radius: 4px;
            padding: 6px 14px;
            font-weight: 600;
            min-width: 65px;
        }
        QMessageBox QPushButton:hover, QDialogButtonBox QPushButton:hover {
            background-color: #f3f4f6;
            color: #111827;
        }

        /* All plain labels default to dark text */
        QLabel {
            color: #111827;
        }

        /* Dialog/window labels */
        QMessageBox QLabel {
            color: #111827;
        }

        /* Menus */
        QMenu {
            color: #000000;
            background-color: #ffffff;
        }

        /* Group box titles */
        QGroupBox {
            color: #374151;
            font-weight: 600;
        }

        /* Checkbox text */
        QCheckBox {
            color: #111827;
        }

        /* Table header styling */
        QHeaderView::section {
            color: #374151;
            background-color: #f9fafb;
            border: 1px solid #e5e7eb;
            padding: 4px 8px;
            font-weight: 600;
        }

        /* Tooltips: white text on dark card */
        QToolTip {
            color: #ffffff;
            background-color: #1f2937;
            border: 1px solid #374151;
            border-radius: 4px;
            padding: 4px;
        }

        /* Scroll area and general widget backgrounds */
        QDialog, QWidget#centralWidget {
            background-color: #f3f4f8;
        }
    """)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
