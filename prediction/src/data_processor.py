import os
from PIL import Image
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple
import torch
import numpy as np
from .face_detector import FaceDetector
from .age_predictor import AgePredictor
from .utils import get_image_files, extract_date_from_filename, extract_user_info_from_image

class DataProcessor:
    """데이터 처리를 위한 클래스"""
    
    def __init__(self, config: dict, device: torch.device):
        """
        데이터 처리기를 초기화합니다.
        
        Args:
            config: 설정 딕셔너리
            device: 연산 장치 (CPU/GPU/MPS)
        """
        self.config = config
        self.device = device
        self.face_detector = FaceDetector(config)
        self.age_predictor = AgePredictor(config, device)
        self.batch_size = config['processing']['batch_size']
        
    def process_directory(self, directory: str) -> Dict:
        """
        디렉토리 내의 모든 이미지를 처리합니다.
        
        Args:
            directory: 처리할 디렉토리 경로
            
        Returns:
            Dict: 처리 결과를 포함하는 딕셔너리
        """
        user_id = Path(directory).name
        results = {
            'user_id': user_id,
            'total_images': 0,
            'faces_detected': 0,
            'age_predictions': [],
            'face_ratio': 0.0,
            'dates': [],
            'user_info': None  # 사용자 정보 저장
        }
        
        # 이미지 파일 목록 가져오기
        image_files = get_image_files(directory, self.config['data']['supported_formats'])
        results['total_images'] = len(image_files)
        
        if not image_files:
            return results
            
        # 먼저 사용자 정보 추출 시도
        for img_path in image_files:
            user_info = extract_user_info_from_image(img_path)
            if user_info['nick'] and user_info['country'] and user_info['gender']:
                results['user_info'] = user_info
                break
        
        # 사용자 정보를 찾지 못한 경우 기본값 사용
        if not results['user_info']:
            results['user_info'] = {
                'fbUid': user_id,
                'nick': None,
                'country': None,
                'gender': None
            }
            
        # 이미지 처리
        for img_path in image_files:
            try:
                image = Image.open(img_path).convert('RGB')
                date = extract_date_from_filename(img_path)
                
                # 얼굴 감지
                has_face, face_boxes = self.face_detector.detect_faces(image)
                
                if has_face:
                    results['faces_detected'] += 1
                    results['dates'].append(date)
                    
                    # 각 얼굴에 대해 나이 예측
                    for face_box in face_boxes:
                        face_image = self.face_detector.crop_face(image, face_box)
                        age_prediction = self.age_predictor.predict_age(face_image, results['user_info'])
                        age_prediction['date'] = date
                        results['age_predictions'].append(age_prediction)
                        
            except Exception as e:
                print(f"Error processing {img_path}: {str(e)}")
                continue
                
        # 결과 계산
        if results['total_images'] > 0:
            results['face_ratio'] = results['faces_detected'] / results['total_images']
            
        if results['age_predictions']:
            ages = [float(pred['age']) for pred in results['age_predictions']]
            results['average_age'] = np.mean(ages)
            results['age_std'] = np.std(ages)
            
        return results
        
    def process_all_users(self, base_directory: str) -> pd.DataFrame:
        """
        모든 사용자의 데이터를 처리합니다.
        
        Args:
            base_directory: 기본 디렉토리 경로
            
        Returns:
            pd.DataFrame: 모든 사용자의 처리 결과
        """
        all_results = []
        
        for user_dir in os.listdir(base_directory):
            user_path = os.path.join(base_directory, user_dir)
            if os.path.isdir(user_path):
                print(f"Processing user: {user_dir}")
                result = self.process_directory(user_path)
                all_results.append(result)
                
        # 결과를 DataFrame으로 변환
        df = pd.DataFrame(all_results)
        
        # 결과 저장
        output_path = os.path.join(
            self.config['data']['output_dir'],
            'results.csv'
        )
        df.to_csv(output_path, index=False)
        
        return df
