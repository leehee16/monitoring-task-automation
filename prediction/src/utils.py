import os
import yaml
from pathlib import Path
import torch
from PIL import Image
import re
from datetime import datetime
import pytesseract
import numpy as np
import cv2

def load_config(config_path: str) -> dict:
    """설정 파일을 로드합니다."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def get_device(config: dict) -> torch.device:
    """설정에 따라 적절한 디바이스를 반환합니다."""
    device_name = config['processing']['device']
    
    if device_name == "mps" and torch.backends.mps.is_available():
        return torch.device("mps")
    elif device_name == "cuda" and torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")

def get_image_files(directory: str, supported_formats: list) -> list:
    """지원되는 이미지 파일들의 경로를 반환합니다."""
    image_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if any(file.lower().endswith(fmt) for fmt in supported_formats):
                image_files.append(os.path.join(root, file))
    return image_files

def extract_date_from_filename(filename: str) -> str:
    """파일 이름에서 날짜를 추출합니다."""
    try:
        return filename.split('_')[-1].split('.')[0]
    except:
        return None

def preprocess_image_for_ocr(image):
    """OCR을 위한 이미지 전처리를 수행합니다."""
    # PIL Image를 numpy 배열로 변환
    img_np = np.array(image)
    
    # BGR로 변환 (OpenCV 형식)
    if len(img_np.shape) == 3:
        img_np = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
    
    # 그레이스케일로 변환
    gray = cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY)
    
    # 노이즈 제거
    denoised = cv2.fastNlMeansDenoising(gray)
    
    # 이진화
    _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # 다시 PIL Image로 변환
    return Image.fromarray(binary)

def extract_user_info_from_image(image_path: str) -> dict:
    """
    이미지에서 사용자 정보를 추출합니다.
    
    Args:
        image_path: 이미지 파일 경로
        
    Returns:
        dict: 추출된 사용자 정보 (fbUid, nick, country, gender)
    """
    try:
        # 이미지 로드
        image = Image.open(image_path)
        
        # 이미지의 상단 부분만 크롭 (전체 높이의 15%만)
        width, height = image.size
        top_section = image.crop((0, 0, width, int(height * 0.15)))
        
        # 이미지 전처리
        processed_image = preprocess_image_for_ocr(top_section)
        
        # OCR 설정
        custom_config = r'--oem 3 --psm 6'
        
        # OCR 수행
        text = pytesseract.image_to_string(processed_image, lang='eng', config=custom_config)
        
        # 텍스트에서 정보 추출
        fb_uid = None
        nick = None
        country = None
        gender = None
        
        # 대소문자 구분 없이 검색
        text = text.lower()
        
        # fbUid 추출 (대소문자 구분 없이)
        fb_uid_match = re.search(r'fbuid:?\s*([^,\s]+)', text, re.IGNORECASE)
        if fb_uid_match:
            fb_uid = fb_uid_match.group(1)
        
        # nick 추출
        nick_match = re.search(r'nick:?\s*([^,\s]+)', text, re.IGNORECASE)
        if nick_match:
            nick = nick_match.group(1)
        
        # country 추출
        country_match = re.search(r'country:?\s*([^,\s]+)', text, re.IGNORECASE)
        if country_match:
            country = country_match.group(1)
        
        # gender 추출
        gender_match = re.search(r'gender:?\s*([^,\s]+)', text, re.IGNORECASE)
        if gender_match:
            gender = gender_match.group(1)
        
        print(f"이미지 경로: {image_path}")
        print(f"추출된 텍스트:\n{text}")
        print(f"추출된 정보: fbUid={fb_uid}, nick={nick}, country={country}, gender={gender}\n")
        
        return {
            'fbUid': fb_uid or os.path.basename(image_path).split('_')[0],
            'nick': nick,
            'country': country,
            'gender': gender
        }
        
    except Exception as e:
        print(f"사용자 정보 추출 중 오류 발생: {str(e)}")
        return {
            'fbUid': os.path.basename(image_path).split('_')[0],
            'nick': None,
            'country': None,
            'gender': None
        }

def create_output_directories(config: dict) -> None:
    """출력 디렉토리를 생성합니다."""
    Path(config['data']['output_dir']).mkdir(parents=True, exist_ok=True)
