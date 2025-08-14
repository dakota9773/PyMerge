#test_merge.py

"""
Purpose:
- Test script for testing merging functionality
"""

import sys, os

#Add src folder for referencing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from PyQt6.QtWidgets import QApplication, QMainWindow
from merge.user_interface import MergePanel

def main():
    app = QApplication(sys.argv)
    window = QMainWindow()
    window.setWindowTitle("Merge Panel Smoke Test")

    # instantiate your panel
    panel = MergePanel(window)
    window.setCentralWidget(panel)

    window.resize(600, 300)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()