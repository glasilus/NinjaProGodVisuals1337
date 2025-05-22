# main.py
import sys
import json
from PyQt5.QtWidgets import QApplication
from ui.main_window import MainWindow

if __name__ == "__main__":
    with open("config.json", "r") as f:
        config = json.load(f)

    app = QApplication(sys.argv)
    win = MainWindow(config)
    win.show()
    sys.exit(app.exec_())
