import os
from pathlib import Path

# 기본 경로 설정
BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / 'policemonitor_*'
HISTORY_DIR = BASE_DIR / 'history'
ANALYSIS_DIR = BASE_DIR / 'analysis'

# 이미지 분류 설정
IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png']
CLASSIFICATIONS = ['NOLOOK', 'BLACK', 'NAKED', 'MALE']

# 데이터베이스 설정
DB_CONFIG = {
    'history_file': HISTORY_DIR / 'user_history.json',
    'analysis_file': ANALYSIS_DIR / 'analysis_data.json',
    'classification_file': ANALYSIS_DIR / 'classifications.xlsx'
}

# 분석 설정
ANALYSIS_CONFIG = {
    'batch_size': 32,
    'image_size': (224, 224),
    'channels': 3,
    'threshold': 0.8
}

# 로깅 설정
LOG_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'file': ANALYSIS_DIR / 'analyzer.log'
}

# 디렉토리 생성
for directory in [HISTORY_DIR, ANALYSIS_DIR]:
    directory.mkdir(exist_ok=True) 