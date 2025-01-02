import torch
from PIL import Image
from transformers import AutoImageProcessor, AutoModelForImageClassification
import numpy as np
from typing import Optional, Dict, List
import torch.nn as nn

class AgePredictor:
    """나이 예측을 위한 클래스"""
    
    def __init__(self, config: dict, device: torch.device):
        """
        나이 예측기를 초기화합니다.
        
        Args:
            config: 설정 딕셔너리
            device: 연산 장치 (CPU/GPU/MPS)
        """
        self.config = config
        self.device = device
        self.model_name = config['models']['vit']['name']
        self.image_size = config['models']['vit']['image_size']
        
        # 모델과 프로세서 로드
        self.processor = AutoImageProcessor.from_pretrained(self.model_name)
        self.model = AutoModelForImageClassification.from_pretrained(
            self.model_name,
            torch_dtype=torch.float16 if device.type == "cuda" else torch.float32,
            device_map="auto"
        ).to(device)
        self.model.eval()
        
        # 나이 그룹 매핑 (UTKFace 데이터셋 기준)
        self.age_groups = {
            0: (0, 2),     # toddler
            1: (3, 9),     # child
            2: (10, 19),   # teenager
            3: (20, 29),   # young adult
            4: (30, 39),   # adult
            5: (40, 49),   # adult
            6: (50, 69),   # old adult
            7: (70, 100)   # elderly
        }
        
        # 나이 그룹 레이블
        self.age_labels = [
            'toddler (0-2)',
            'child (3-9)',
            'teenager (10-19)',
            'young adult (20-29)',
            'adult (30-39)',
            'adult (40-49)',
            'old adult (50-69)',
            'elderly (70+)'
        ]
        
    def _process_image(self, image: Image.Image) -> torch.Tensor:
        """이미지를 전처리합니다."""
        return self.processor(
            images=image,
            return_tensors="pt"
        ).to(self.device)
        
    def _get_age_prediction(self, logits: torch.Tensor) -> tuple:
        """로짓에서 나이 예측을 계산합니다."""
        probs = torch.softmax(logits, dim=1)
        predicted_class = torch.argmax(logits, dim=1).item()
        confidence = probs[0][predicted_class].item()
        
        age_range = self.age_groups[predicted_class]
        predicted_age = (age_range[0] + age_range[1]) // 2
        age_label = self.age_labels[predicted_class]
        
        return predicted_age, age_range, age_label, confidence
        
    def predict_age(self, image: Image.Image, user_info: Optional[Dict] = None) -> dict:
        """
        이미지에서 나이를 예측합니다.
        
        Args:
            image: PIL Image 객체
            user_info: 사용자 정보 딕셔너리 (선택사항)
                - fbUid: 사용자 ID
                - nick: 닉네임
                - country: 국가
                - gender: 성별
                
        Returns:
            dict: 예측된 나이와 신뢰도를 포함하는 딕셔너리
        """
        # 이미지 전처리
        inputs = self._process_image(image)
        
        # 예측 수행
        with torch.no_grad():
            outputs = self.model(**inputs)
            predicted_age, age_range, age_label, confidence = self._get_age_prediction(outputs.logits)
        
        # 결과 생성
        result = {
            'age': predicted_age,
            'age_range': age_range,
            'age_label': age_label,
            'confidence': float(confidence)
        }
        
        # 사용자 정보가 있으면 추가
        if user_info:
            result.update(user_info)
            
        return result
        
    def predict_batch(self, images: List[Image.Image], user_infos: Optional[List[Dict]] = None) -> List[Dict]:
        """
        여러 이미지의 나이를 한 번에 예측합니다.
        
        Args:
            images: PIL Image 객체들의 리스트
            user_infos: 사용자 정보 딕셔너리들의 리스트 (선택사항)
        
        Returns:
            List[Dict]: 각 이미지의 예측 결과 딕셔너리 리스트
        """
        if not images:
            return []
            
        # 이미지 전처리
        batch_inputs = self.processor(
            images=images,
            return_tensors="pt"
        ).to(self.device)
        
        # 예측 수행
        with torch.no_grad():
            outputs = self.model(**batch_inputs)
            
        # 결과 생성
        results = []
        for i, logits in enumerate(outputs.logits):
            predicted_age, age_range, age_label, confidence = self._get_age_prediction(logits.unsqueeze(0))
            
            result = {
                'age': predicted_age,
                'age_range': age_range,
                'age_label': age_label,
                'confidence': float(confidence)
            }
            
            # 사용자 정보가 있으면 추가
            if user_infos and i < len(user_infos):
                result.update(user_infos[i])
                
            results.append(result)
            
        return results
