import sys
from PySide2.QtWidgets import QApplication


import guis.gui_main as gui


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = gui.MainWindow()
    window.show()
    sys.exit(app.exec_())