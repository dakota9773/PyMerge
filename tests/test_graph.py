#test_graph.py

"""
Purpose:
- Test script for testing graphing functionality
"""

import sys, os

#Add src folder for referencing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QHBoxLayout
from graph.user_interface import GraphSettingsPanel, GraphDisplayPanel

def main():
    app = QApplication(sys.argv)
    window = QMainWindow()
    window.setWindowTitle("Graph Panels Smoke Test")

    # Central container with horizontal layout
    central = QWidget()
    layout = QHBoxLayout(central)

    settings = GraphSettingsPanel()
    display = GraphDisplayPanel()

    # Wire signals to display panel's slots
    settings.plotReady.connect(display.update_plot)                     #plotReady = (object, str, str, object)
    settings.filedataReady.connect(display.receive_file_data)           #filedataReady = (list, list, object)

    # Add panels side by side
    layout.addWidget(settings)
    layout.addWidget(display)

    window.setCentralWidget(central)
    window.resize(1000, 600)
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()