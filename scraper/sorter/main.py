import sys
import os
from pathlib import Path
from PyQt5.QtWidgets import QApplication
from image_classifier import ImageClassifier
from utils import setup_logging

def get_latest_week_folder():
    """history 폴더에서 가장 최근 주차 폴더를 찾습니다."""
    history_dir = Path(__file__).parent.parent / 'history'
    if not history_dir.exists():
        return None
        
    week_folders = [d for d in history_dir.iterdir() if d.is_dir() and d.name[0].isdigit()]
    if not week_folders:
        return None
        
    # 폴더명이 YYYYMMDD-YYYYMMDD 형식이므로 정렬하면 최신 날짜가 마지막에 옵니다
    latest_folder = sorted(week_folders)[-1]
    return str(latest_folder)

def main():
    setup_logging()
    app = QApplication(sys.argv)
    classifier = ImageClassifier()
    
    # 최신 주차 폴더 찾기
    latest_folder = get_latest_week_folder()
    if latest_folder:
        data_folder = os.path.join(latest_folder, 'data')
        if os.path.exists(data_folder):
            classifier.select_folder(data_folder)
    
    classifier.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
