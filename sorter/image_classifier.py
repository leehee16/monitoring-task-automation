from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QScrollArea, QFileDialog, QInputDialog, QMessageBox, QProgressBar
from PyQt5.QtGui import QPixmap, QKeyEvent, QResizeEvent
from PyQt5.QtCore import Qt, QSize
from image_processor import ImageProcessor
from utils import load_excel_file, create_new_excel_file, save_to_excel, get_image_files
from constants import CLASSIFICATIONS, SETTINGS_FILE
import os
import json
import logging
from datetime import datetime

class ImageClassifier(QWidget):
    def __init__(self):
        super().__init__()
        self.initializeVariables()
        self.initUI()

    def initializeVariables(self):
        self.current_folder = None
        self.current_images = []
        self.current_index = 0
        self.classifications = {}
        self.user_folders = []
        self.current_user_index = 0
        self.problem_images = set()
        self.current_pixmap = None
        self.excel_file = None
        self.total_images = 0
        self.total_problem_images = 0

    def initUI(self):
        self.setWindowTitle('Image Classifier')
        self.setGeometry(100, 100, 1000, 800)

        layout = QVBoxLayout()

        self.setupImageDisplay(layout)
        self.setupStatusLabels(layout)
        self.setupButtons(layout)
        self.setupProgressBar(layout)

        self.setLayout(layout)
        self.setFocusPolicy(Qt.StrongFocus)

    def setupImageDisplay(self, layout):
        self.scroll_area = QScrollArea()
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.scroll_area.setWidget(self.image_label)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # 수직 스크롤바도 비활성화
        layout.addWidget(self.scroll_area)

    def setupStatusLabels(self, layout):
        self.problem_label = QLabel('문제 있음: 아니오')
        self.progress_label = QLabel('진행 상황: 0/0')
        status_layout = QHBoxLayout()
        status_layout.addWidget(self.problem_label)
        status_layout.addWidget(self.progress_label)
        layout.addLayout(status_layout)

    def setupButtons(self, layout):
        self.select_folder_button = QPushButton('Select Folder')
        self.select_folder_button.clicked.connect(self.select_folder)
        layout.addWidget(self.select_folder_button)

        self.save_button = QPushButton('Save to Excel')
        self.save_button.clicked.connect(self.save_to_excel)
        self.save_button.setEnabled(False)
        layout.addWidget(self.save_button)

    def setupProgressBar(self, layout):
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r') as f:
                    settings = json.load(f)
                    last_folder = settings.get('last_folder')
                    if last_folder and os.path.exists(last_folder):
                        self.select_folder(last_folder)
            except Exception as e:
                logging.error(f"설정 파일 로드 중 오류 발생: {e}")

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Directory", self.current_folder)
        if folder:
            self.current_folder = folder
            self.excel_file = os.path.join(folder, "classifications.xlsx")
            self.load_existing_classifications()
            self.load_user_folders()
            self.save_settings()
            self.start_image_processing()

    def load_existing_classifications(self):
        if os.path.exists(self.excel_file):
            self.classifications = load_excel_file(self.excel_file)
        else:
            create_new_excel_file(self.excel_file)

    def load_user_folders(self):
        self.user_folders = [f for f in os.listdir(self.current_folder) if os.path.isdir(os.path.join(self.current_folder, f))]
        self.user_folders = [f for f in self.user_folders if f not in self.classifications]
        self.current_user_index = 0
        self.total_images = 0
        self.total_problem_images = 0
        if self.user_folders:
            self.load_images()
        else:
            self.save_button.setEnabled(True)
            QMessageBox.information(self, '알림', '분류할 이미지가 없습니다.')

    def load_images(self):
        if self.current_user_index < len(self.user_folders):
            user_folder = self.user_folders[self.current_user_index]
            user_path = os.path.join(self.current_folder, user_folder)
            if os.path.exists(user_path):
                self.current_images = get_image_files(user_path)
                self.total_images += len(self.current_images)
                self.current_index = 0
                self.problem_images.clear()
                if self.current_images:
                    self.show_current_image()
                else:
                    self.delete_empty_folder(user_path)
                    self.next_user()
            else:
                # 폴더가 존재하지 않으면 다음 사용자로 이동
                self.next_user()
        else:
            self.save_button.setEnabled(True)
            QMessageBox.information(self, '완료', '모든 사용자 분류가 완료되었습니다.')

    def show_current_image(self):
        if self.current_images and self.current_index < len(self.current_images):
            user_folder = self.user_folders[self.current_user_index]
            image_path = os.path.join(self.current_folder, user_folder, self.current_images[self.current_index])
            self.current_pixmap = QPixmap(image_path)
            self.update_image_label()
            
            self.problem_label.setText(f"문제 있음: {'예' if self.current_images[self.current_index] in self.problem_images else '아니오'}")
            self.update_progress_label()
        else:
            self.image_label.clear()
            self.problem_label.setText("문제 있음: -")

    def update_image_label(self):
        if self.current_pixmap:
            scaled_pixmap = self.current_pixmap.scaled(
                self.scroll_area.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.image_label.setPixmap(scaled_pixmap)

    def update_progress_label(self):
        total = len(self.user_folders)
        current = self.current_user_index + 1
        self.progress_label.setText(f'진행 상황: {current}/{total}')

    def next_user(self):
        if not self.problem_images:
            reply = QMessageBox.question(self, '다음 폴더로 이동', 
                                         '문제가 있는 이미지가 없습니다. 다음 폴더로 이동하시겠습니까?',
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            if reply == QMessageBox.Yes:
                self.finalize_current_folder()
                self.move_to_next_folder()
            else:
                return
        else:
            self.classify_and_next_user()

    def classify_and_next_user(self):
        classification, ok = QInputDialog.getItem(self, "분류", "이 사용자의 분류를 선택하세요:", CLASSIFICATIONS, 0, False)
        if ok and classification:
            self.finalize_current_folder(classification)
            self.move_to_next_folder()
        else:
            return

    def finalize_current_folder(self, classification=None):
        self.delete_non_problem_images()
        if classification:
            self.save_classification(classification)

    def delete_non_problem_images(self):
        user_folder = self.user_folders[self.current_user_index]
        user_path = os.path.join(self.current_folder, user_folder)
        for image in self.current_images[:]:
            if image not in self.problem_images:
                image_path = os.path.join(user_path, image)
                try:
                    os.remove(image_path)
                    self.current_images.remove(image)
                    logging.info(f"이미지 삭제: {image_path}")
                except OSError as e:
                    logging.error(f"이미지를 삭제할 수 없습니다: {image_path}. 오류: {e}")
        
        if not self.current_images:
            self.delete_empty_folder(user_path)

    def delete_empty_folder(self, folder_path):
        try:
            os.rmdir(folder_path)
            logging.info(f"빈 폴더 삭제: {folder_path}")
        except OSError as e:
            logging.error(f"폴더를 삭제할 수 없습니다: {folder_path}. 오류: {e}")

    def move_to_next_folder(self):
        if self.current_user_index < len(self.user_folders) - 1:
            self.current_user_index += 1
            self.load_images()
        else:
            self.generate_report()
            QMessageBox.information(self, '완료', '모든 사용자 분류가 완료되었습니다.')
            self.save_button.setEnabled(True)

    def save_classification(self, classification):
        user_id = self.user_folders[self.current_user_index]
        problem_dates = sorted([img.split('_')[1].split('.')[0] for img in self.problem_images], reverse=True)
        self.classifications[user_id] = {
            'classification': classification,
            'problem_dates': problem_dates
        }
        save_to_excel(self.excel_file, {user_id: self.classifications[user_id]})

    def generate_report(self):
        report_file = os.path.join(self.current_folder, f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
        try:
            with open(report_file, 'w') as f:
                f.write(f"작업 완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"총 이미지 수: {self.total_images}\n")
                f.write(f"문제 있는 이미지 수: {self.total_problem_images}\n")
                f.write(f"문제 비율: {self.total_problem_images / self.total_images * 100:.2f}%\n\n")
                
                for classification in CLASSIFICATIONS:
                    count = sum(1 for data in self.classifications.values() if data['classification'] == classification)
                    f.write(f"{classification} 분류 수: {count}\n")
            
            QMessageBox.information(self, '레포트 생성', f'레포트가 생성되었습니다: {report_file}')
        except Exception as e:
            logging.error(f"레포트 생성 중 오류 발생: {e}")
            QMessageBox.warning(self, '오류', '레포트를 생성하는 중 오류가 발생했습니다.')

    def save_settings(self):
        settings = {
            'last_folder': self.current_folder
        }
        try:
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(settings, f)
        except Exception as e:
            logging.error(f"설정 파일 저장 중 오류 발생: {e}")

    def start_image_processing(self):
        self.image_processor = ImageProcessor(self.current_folder)
        self.image_processor.progress_updated.connect(self.update_progress_bar)
        self.image_processor.finished.connect(self.on_image_processing_finished)
        self.image_processor.start()

    def update_progress_bar(self, value):
        self.progress_bar.setValue(value)

    def on_image_processing_finished(self):
        QMessageBox.information(self, '처리 완료', '모든 이미지 처리가 완료되었습니다.')

    def keyPressEvent(self, event: QKeyEvent):
        key_actions = {
            Qt.Key_Right: self.next_image_or_user,
            Qt.Key_Left: self.prev_image_or_user,
            Qt.Key_Up: self.toggle_problem_image
        }
        action = key_actions.get(event.key())
        if action:
            action()
            event.accept()
        else:
            super().keyPressEvent(event)

    def next_image_or_user(self):
        if self.current_images and self.current_index < len(self.current_images) - 1:
            self.current_index += 1
            self.show_current_image()
        else:
            self.next_user()

    def prev_image_or_user(self):
        if self.current_images and self.current_index > 0:
            self.current_index -= 1
            self.show_current_image()
        elif self.current_user_index > 0:
            original_index = self.current_user_index
            original_images = self.current_images.copy()
            original_current_index = self.current_index

            while self.current_user_index > 0:
                self.current_user_index -= 1
                user_folder = self.user_folders[self.current_user_index]
                user_path = os.path.join(self.current_folder, user_folder)
                
                if os.path.exists(user_path):
                    self.load_images()
                    if self.current_images:
                        self.current_index = len(self.current_images) - 1
                        self.show_current_image()
                        return
                
            # 이전 유효한 폴더를 찾지 못한 경우
            self.current_user_index = original_index
            self.current_images = original_images
            self.current_index = original_current_index
            QMessageBox.information(self, '알림', '이전 유효한 폴더가 없습니다.')

    def toggle_problem_image(self):
        if self.current_images and self.current_index < len(self.current_images):
            current_image = self.current_images[self.current_index]
            if current_image in self.problem_images:
                self.problem_images.remove(current_image)
                self.total_problem_images -= 1
            else:
                self.problem_images.add(current_image)
                self.total_problem_images += 1
            self.problem_label.setText(f"문제 있음: {'예' if current_image in self.problem_images else '아니오'}")

    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        if self.current_pixmap:
            self.show_current_image()

    def save_to_excel(self):
        if not self.classifications:
            QMessageBox.warning(self, '경고', '저장할 분류 데이터가 없습니다.')
            return

        try:
            save_to_excel(self.excel_file, self.classifications)
            QMessageBox.information(self, '저장 완료', f'분류 데이터가 {self.excel_file}에 저장되었습니다.')
        except Exception as e:
            logging.error(f"엑셀 파일 저장 중 오류 발생: {e}")
            QMessageBox.critical(self, '오류', '엑셀 파일 저장 중 오류가 발생했습니다.')

