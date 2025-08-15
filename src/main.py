import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QHBoxLayout, QVBoxLayout
)

from merge.user_interface import MergePanel
from bin.user_interface import BinningPanel
from graph.user_interface import GraphSettingsPanel, GraphDisplayPanel


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyMerge")
        self.resize(1550, 800)

        # central layout
        container = QWidget()
        h_main = QHBoxLayout(container)
        self.setCentralWidget(container)

        # instantiate GUI panels
        self.merge_panel = MergePanel(self)
        self.binning_panel = BinningPanel(self)
        self.graph_settings_panel = GraphSettingsPanel()
        self.graph_display_panel = GraphDisplayPanel()

        # CONNECT: autoload merged file path into binning panel
        self.merge_panel.merged_filepath.connect(self.binning_panel.set_bin_file)
        self.binning_panel.binned_filepath.connect(self.graph_settings_panel.set_graph_file)

        # CONNECT: graph settings to graph display
        self.graph_settings_panel.plotReady.connect(self.graph_display_panel.update_plot)
        self.graph_settings_panel.filedataReady.connect(self.graph_display_panel.receive_file_data)

        # left column: merge, bin, graph-settings
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.addWidget(self.merge_panel, 1)
        left_layout.addWidget(self.binning_panel, 1)
        left_layout.addWidget(self.graph_settings_panel, 10)
        h_main.addWidget(left_panel, 1)

        # right column: graph output
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.addWidget(self.graph_display_panel)
        h_main.addWidget(right_panel, 5)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())