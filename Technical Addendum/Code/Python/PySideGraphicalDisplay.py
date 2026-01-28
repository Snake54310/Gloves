from PySide6.QtWidgets import QApplication, QMainWindow, QLabel
from PySide6.QtCore import Qt

app = QApplication.instance()
if app is None:
    app = QApplication([])

class GloveMonitorWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle('Acquisition Window')

        label = QLabel('Test for label')
        label.setAlignment(Qt.AlignCenter)

        self.setCentralWidget(label)

    def initDisplay(self):
        self.show()
        return

    def terminateDisplay(self):
        # self.hide() # this hides widget without deleting it
        self.close()
        return
