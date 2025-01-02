from PyQt5.QtCore import QThread, pyqtSignal
from constants import IMAGE_EXTENSIONS
import os

class ImageProcessor(QThread):
    progress_updated = pyqtSignal(int)
    finished = pyqtSignal()

    def __init__(self, folder_path):
        super().__init__()
        self.folder_path = folder_path

    def run(self):
        total_files = sum([len(files) for r, d, files in os.walk(self.folder_path)])
        processed_files = 0
        for root, dirs, files in os.walk(self.folder_path):
            for file in files:
                if any(file.lower().endswith(ext) for ext in IMAGE_EXTENSIONS):
                    processed_files += 1
                    self.progress_updated.emit(int(processed_files / total_files * 100))
        self.finished.emit()
