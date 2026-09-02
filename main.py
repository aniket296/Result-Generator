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

    # Ensure all user input fields unconditionally use black font color
    app.setStyleSheet("""
        /* All text-input widgets: black text on white background */
        QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox,
        QComboBox, QFontComboBox, QListWidget {
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

        /* All plain labels default to dark text (safe on light backgrounds).
           Labels on dark backgrounds override this with their own inline style. */
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
        }

        /* Checkbox text */
        QCheckBox {
            color: #111827;
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
