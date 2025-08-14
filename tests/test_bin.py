#test_bin.py

"""
Purpose:
- Test script for testing binning functionality
"""

import sys, os

#Add src folder for referencing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from PyQt6.QtWidgets import QApplication, QMainWindow
from bin.user_interface import BinningPanel

def main():
    app = QApplication(sys.argv)
    window = QMainWindow()
    window.setWindowTitle("Binning Panel Smoke Test")

    panel = BinningPanel(window)

    window.setCentralWidget(panel)
    window.resize(600, 400)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()