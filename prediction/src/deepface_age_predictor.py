"""
DeepFace를 사용한 나이 예측 클래스
"""

import os
from deepface import DeepFace
from PIL import Image
import numpy as np
from typing import Optional, Dict, Tuple
import logging

class DeepFaceAgePredictor:
    """DeepFace를 사용한 나이 예측 클래스"""
    
    def __init__(self, config: dict):
        """
        DeepFace 기반 나이 예측기를 초기화.
        
        Args:
            config: 설정 딕셔너리
        """
        self.UNDERAGE_MAX = config['age_detection']['underage_threshold']
        self.MIN_CONFIDENCE = config['age_detection']['min_confidence']
        
    def _convert_to_age_group(self, age: float) -> str:
        """
        나이를 연령 그룹으로 변환.
        
        Args:
            age: 예측된 나이
            
        Returns:
            str: 연령 그룹 레이블
        """
        if age < self.UNDERAGE_MAX:
            return 'underage'
        return 'adult'
        
    def _get_age_range(self, age: float) -> Tuple[int, int]:
        """
        예측된 나이에 대한 추정 범위를 반환.
        
        Args:
            age: 예측된 나이
            
        Returns:
            Tuple[int, int]: (최소 나이, 최대 나이)
        """
        # 나이에 따라 다른 범위 적용
        if age < 15:
            margin = 1
        elif age < 20:
            margin = 2
        else:
            margin = 3
            
        return (max(0, int(age - margin)), int(age + margin))
        
    def _calculate_confidence(self, result: dict) -> float:
        """
        예측 결과의 신뢰도를 계산.
        
        Args:
            result: DeepFace 분석 결과
            
        Returns:
            float: 0과 1 사이의 신뢰도 점수
        """
        # 얼굴 감지 품질과 나이 예측의 확실성을 기반으로 신뢰도 계산
        face_confidence = result.get('face_confidence', 0.5)
        
        # 나이가 경계값(19세)에 가까울수록 신뢰도 감소
        age = result.get('age', 0)
        age_margin = abs(age - self.UNDERAGE_MAX)
        age_confidence = min(1.0, age_margin / 5.0)  # 5년을 기준으로 정규화
        
        # 종합 신뢰도 계산
        confidence = (face_confidence + age_confidence) / 2
        return min(1.0, max(0.0, confidence))
        
    def predict_age(self, image: Image.Image, user_info: Optional[Dict] = None) -> dict:
        """
        이미지에서 나이를 예측.
        
        Args:
            image: PIL Image 객체
            user_info: 사용자 정보 딕셔너리 (선택사항)
            
        Returns:
            dict: 예측 결과를 포함하는 딕셔너리
        """
        try:
            # PIL Image를 numpy 배열로 변환
            img_array = np.array(image)
            
            # DeepFace 분석 수행
            result = DeepFace.analyze(
                img_array,
                actions=['age'],
                enforce_detection=False,
                silent=True
            )[0]  # 첫 번째 얼굴만 사용
            
            if not result or 'age' not in result:
                return {
                    'has_face': False,
                    'predicted_age': None,
                    'age_range': None,
                    'age_group': None,
                    'confidence': None,
                    'is_reliable': False
                }
            
            predicted_age = float(result['age'])
            
            # 나이 범위와 그룹 계산
            age_range = self._get_age_range(predicted_age)
            age_group = self._convert_to_age_group(predicted_age)
            
            # 신뢰도 계산
            confidence = self._calculate_confidence(result)
            
            result = {
                'has_face': True,
                'predicted_age': round(predicted_age, 1),
                'age_range': f"{age_range[0]}-{age_range[1]}",
                'age_group': age_group,
                'confidence': confidence,
                'is_reliable': confidence >= self.MIN_CONFIDENCE,
                'is_underage': age_group == 'underage'
            }
            
            # 사용자 정보가 있으면 추가
            if user_info:
                result.update(user_info)
                
            return result
            
        except Exception as e:
            logging.error(f"DeepFace 분석 중 오류 발생: {str(e)}")
            return {
                'has_face': False,
                'predicted_age': None,
                'age_range': None,
                'age_group': None,
                'confidence': None,
                'is_reliable': False,
                'error': str(e)
            }
            
    def predict_batch(self, images: list, user_infos: Optional[list] = None) -> list:
        """
        여러 이미지의 나이를 한 번에 예측.
        
        Args:
            images: PIL Image 객체들의 리스트
            user_infos: 사용자 정보 딕셔너리들의 리스트 (선택사항)
            
        Returns:
            List[Dict]: 각 이미지의 예측 결과 딕셔너리 리스트
        """
        results = []
        for i, image in enumerate(images):
            user_info = user_infos[i] if user_infos and i < len(user_infos) else None
            result = self.predict_age(image, user_info)
            results.append(result)
        return results 