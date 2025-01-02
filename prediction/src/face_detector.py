import numpy as np
from PIL import Image
from mtcnn import MTCNN
import dlib

class FaceDetector:
    """얼굴 감지를 위한 클래스"""
    
    def __init__(self, config: dict):
        """
        얼굴 감지기를 초기화.
        
        Args:
            config: 설정 딕셔너리
        """
        self.method = config['models']['face_detection']['method']
        if self.method == 'mtcnn':
            self.detector = MTCNN()
        else:  # dlib
            self.detector = dlib.get_frontal_face_detector()

    def detect_faces(self, image: Image.Image) -> tuple:
        """
        이미지에서 얼굴을 감지.
        
        Args:
            image: PIL Image 객체
        
        Returns:
            (bool, list): 얼굴 감지 여부와 감지된 얼굴 영역 리스트
        """
        if self.method == 'mtcnn':
            return self._detect_faces_mtcnn(image)
        else:
            return self._detect_faces_dlib(image)

    def _detect_faces_mtcnn(self, image: Image.Image) -> tuple:
        """MTCNN을 사용한 얼굴 감지"""
        image_array = np.array(image)
        faces = self.detector.detect_faces(image_array)
        if not faces:
            return False, []
        return True, [face['box'] for face in faces]

    def _detect_faces_dlib(self, image: Image.Image) -> tuple:
        """dlib을 사용한 얼굴 감지"""
        image_array = np.array(image)
        faces = self.detector(image_array)
        if not faces:
            return False, []
        return True, [(face.left(), face.top(), 
                      face.right() - face.left(),
                      face.bottom() - face.top()) for face in faces]

    def crop_face(self, image: Image.Image, face_box: tuple) -> Image.Image:
        """감지된 얼굴 영역을 크롭합니다."""
        x, y, width, height = face_box
        return image.crop((x, y, x + width, y + height))
