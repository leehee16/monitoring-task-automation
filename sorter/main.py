import sys
from PyQt5.QtWidgets import QApplication
from image_classifier import ImageClassifier
from utils import setup_logging

if __name__ == '__main__':
    setup_logging()
    app = QApplication(sys.argv)
    ex = ImageClassifier()
    ex.show()
    sys.exit(app.exec_())
