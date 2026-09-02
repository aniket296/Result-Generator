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
        QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox, QFontComboBox, QListWidget {
            color: #000000;
            background-color: #ffffff;
            selection-background-color: #4f7ef8;
            selection-color: #ffffff;
        }
        QComboBox QAbstractItemView {
            color: #000000;
            background-color: #ffffff;
            selection-background-color: #eff6ff;
            selection-color: #1d4ed8;
        }
        QMenu {
            color: #000000;
            background-color: #ffffff;
        }
        QMessageBox QLabel {
            color: #111827;
        }
    """)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
