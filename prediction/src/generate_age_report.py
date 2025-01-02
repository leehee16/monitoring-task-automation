"""
이미지 폴더로부터 나이를 예측하고 CSV 리포트를 생성하는 스크립트
DeepFace를 사용한 정확한 나이 예측
"""

import os
import csv
import json
import re
import shutil
from PIL import Image
from deepface_age_predictor import DeepFaceAgePredictor
from pathlib import Path
import yaml
from tqdm import tqdm
import logging
import cv2
import numpy as np
from datetime import datetime

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def load_config():
    """설정 파일을 로드합니다."""
    config_path = Path("config/config.yaml")
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

def extract_metadata_from_filename(filename):
    """파일 이름에서 날짜 정보를 추출합니다."""
    date_match = re.search(r'_(\d{8})\.', filename)
    if date_match:
        date_str = date_match.group(1)
        try:
            return datetime.strptime(date_str, '%Y%m%d').strftime('%Y-%m-%d')
        except ValueError:
            return None
    return None

def extract_metadata_from_folder(folder_path):
    """폴더 이름에서 메타데이터를 추출합니다."""
    folder_id = os.path.basename(folder_path)
    
    # 기본 메타데이터
    metadata = {
        'fbUid': folder_id,
        'nick': None,
        'country': None,
        'gender': None
    }
    
    # 이미지 파일에서 메타데이터 찾기
    image_files = get_image_files(folder_path)
    if image_files:
        first_image = os.path.basename(image_files[0])
        # fbUid_YYYYMMDD.jpg 형식에서 fbUid 추출
        metadata['fbUid'] = first_image.split('_')[0]
    
    return metadata

def get_image_files(folder_path):
    """폴더 내의 이미지 파일들을 찾습니다."""
    image_extensions = {'.jpg', '.jpeg', '.png', '.webp'}
    image_files = []
    
    for file in os.listdir(folder_path):
        if os.path.splitext(file)[1].lower() in image_extensions:
            image_files.append(os.path.join(folder_path, file))
    
    # 날짜순으로 정렬
    image_files.sort()
    return image_files

def detect_face(image):
    """이미지에서 얼굴을 검출합니다."""
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    
    # PIL Image를 OpenCV 형식으로 변환
    img_array = np.array(image)
    img_array = img_array[:, :, ::-1].copy() # RGB to BGR
    
    gray = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.1, 4)
    
    return len(faces) > 0, len(faces)

def process_folder(folder_path, predictor):
    """하나의 폴더에 대한 나이 예측을 수행합니다."""
    folder_metadata = extract_metadata_from_folder(folder_path)
    image_files = get_image_files(folder_path)
    
    if not image_files:
        logging.warning(f"이미지를 찾을 수 없음: {folder_metadata['fbUid']}")
        return [{
            **folder_metadata,
            'date': None,
            'has_face': False,
            'face_count': 0,
            'predicted_age': None,
            'age_range': None,
            'age_group': None,
            'confidence': None,
            'is_reliable': False,
            'is_underage': None
        }]
    
    results = []
    for img_path in image_files:
        try:
            image = Image.open(img_path)
            date = extract_metadata_from_filename(os.path.basename(img_path))
            
            # DeepFace API로 나이 예측
            prediction = predictor.predict_age(image, folder_metadata)
            prediction['date'] = date
            prediction['image_name'] = os.path.basename(img_path)
            
            results.append(prediction)
            
        except Exception as e:
            logging.error(f"이미지 처리 중 오류 발생 {img_path}: {str(e)}")
    
    return results

def copy_underage_images(results, output_path):
    """미성년자로 예측된 이미지들을 별도 폴더로 복사합니다."""
    underage_dir = os.path.join(output_path, 'underage_images')
    os.makedirs(underage_dir, exist_ok=True)
    
    # 미성년자 이미지 찾기 (신뢰도가 높은 것만)
    underage_results = [r for r in results if r.get('is_underage') and r.get('is_reliable')]
    
    if not underage_results:
        logging.info("신뢰할 수 있는 미성년자 예측 결과가 없습니다.")
        return
    
    # 이미지 복사
    for result in underage_results:
        try:
            # 원본 이미지 경로 구성
            src_path = os.path.join('data/policemonitor_20241216-20241222', 
                                  result['fbUid'], 
                                  result['image_name'])
            
            # 대상 경로 구성 (fbUid_날짜_나이_신뢰도.jpg 형식)
            confidence_str = f"{result['confidence']:.3f}"
            age_str = f"{result['predicted_age']:.1f}"
            dest_filename = f"{result['fbUid']}_{result['date']}_{age_str}_{confidence_str}.jpg"
            dest_path = os.path.join(underage_dir, dest_filename)
            
            # 이미지 복사
            shutil.copy2(src_path, dest_path)
            logging.info(f"미성년자 이미지 복사됨: {dest_filename}")
            
        except Exception as e:
            logging.error(f"이미지 복사 중 오류 발생: {str(e)}")
    
    logging.info(f"총 {len(underage_results)}개의 미성년자 이미지가 {underage_dir}에 복사되었습니다.")

def generate_underage_report(results, output_path):
    """미성년자로 예측된 사용자들의 상세 리포트를 생성합니다."""
    underage_results = [r for r in results if r.get('is_underage') and r.get('is_reliable')]
    
    if not underage_results:
        logging.info("신뢰할 수 있는 미성년자 예측 결과가 없습니다.")
        return
    
    # 결과를 정렬 (나이 순, 신뢰도 순)
    underage_results.sort(key=lambda x: (x['predicted_age'], -x['confidence']))
    
    # 리포트 파일 생성
    report_file = os.path.join(output_path, 'underage_report.csv')
    
    fieldnames = ['fbUid', 'predicted_age', 'age_range', 'confidence', 'date']
    
    with open(report_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for result in underage_results:
            writer.writerow({
                'fbUid': result['fbUid'],
                'predicted_age': f"{result['predicted_age']:.1f}",
                'age_range': result['age_range'],
                'confidence': f"{result['confidence']:.3f}",
                'date': result['date']
            })
    
    # 콘솔에 요약 출력
    logging.info("\n=== 미성년자 예측 결과 ===")
    logging.info(f"총 {len(underage_results)}개의 미성년자 예측 결과")
    logging.info("\n상위 10개 결과 (나이 순):")
    logging.info(f"{'ID':30} | {'나이':6} | {'범위':10} | {'신뢰도':8} | {'날짜'}")
    logging.info("-" * 70)
    
    for result in underage_results[:10]:
        logging.info(
            f"{result['fbUid']:30} | {result['predicted_age']:6.1f} | "
            f"{result['age_range']:10} | {result['confidence']:.3f} | {result['date']}"
        )
    
    # 사용자별 통계
    user_stats = {}
    for result in underage_results:
        fbUid = result['fbUid']
        if fbUid not in user_stats:
            user_stats[fbUid] = {
                'predictions': [],
                'confidences': []
            }
        user_stats[fbUid]['predictions'].append(result['predicted_age'])
        user_stats[fbUid]['confidences'].append(result['confidence'])
    
    # 사용자별 평균 통계
    logging.info("\n=== 사용자별 평균 통계 ===")
    logging.info(f"{'ID':30} | {'평균나이':8} | {'평균신뢰도':10} | {'예측횟수'}")
    logging.info("-" * 70)
    
    for fbUid, stats in user_stats.items():
        avg_age = np.mean(stats['predictions'])
        avg_conf = np.mean(stats['confidences'])
        count = len(stats['predictions'])
        logging.info(f"{fbUid:30} | {avg_age:8.1f} | {avg_conf:10.3f} | {count}")

def generate_report(data_path, output_path):
    """전체 데이터셋에 대한 나이 예측 리포트를 생성합니다."""
    # 설정 로드
    config = load_config()
    
    # DeepFace 나이 예측기 초기화
    predictor = DeepFaceAgePredictor(config)
    
    # 결과를 저장할 리스트
    all_results = []
    
    # 각 폴더 처리
    folders = [f.path for f in os.scandir(data_path) if f.is_dir()]
    for folder in tqdm(folders, desc="폴더 처리 중"):
        results = process_folder(folder, predictor)
        if results:
            all_results.extend(results)
    
    # CSV 파일로 저장
    if all_results:
        output_file = os.path.join(output_path, 'age_prediction_report.csv')
        os.makedirs(output_path, exist_ok=True)
        
        fieldnames = [
            'fbUid', 'nick', 'country', 'gender', 'date',
            'image_name', 'has_face',
            'predicted_age', 'age_range', 'age_group',
            'confidence', 'is_reliable', 'is_underage'
        ]
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_results)
        
        logging.info(f"리포트 생성 완료: {output_file}")
        
        # 통계 정보 생성
        generate_statistics(all_results, output_path)
        
        # 미성년자 이미지 복사 및 리포트 생성
        copy_underage_images(all_results, output_path)
        generate_underage_report(all_results, output_path)
    else:
        logging.warning("CSV로 저장할 결과가 없습니다")

def generate_statistics(results, output_path):
    """결과에 대한 통계 정보를 생성합니다."""
    stats = {
        'total_users': len(set(r['fbUid'] for r in results)),
        'total_images': len(results),
        'images_with_faces': len([r for r in results if r['has_face']]),
        'images_without_faces': len([r for r in results if not r['has_face']]),
        'reliable_predictions': len([r for r in results if r['is_reliable']]),
        'underage_predictions': len([r for r in results if r['is_underage'] and r['is_reliable']]),
        'adult_predictions': len([r for r in results if not r['is_underage'] and r['is_reliable']]),
        'average_age': np.mean([r['predicted_age'] for r in results if r['predicted_age'] is not None]),
        'age_distribution': {}
    }
    
    # 나이 분포 계산 (신뢰할 수 있는 예측만)
    reliable_results = [r for r in results if r['is_reliable'] and r['predicted_age'] is not None]
    if reliable_results:
        age_ranges = [
            (0, 15, '15세 미만'),
            (15, 17, '15-17세'),
            (17, 19, '17-19세'),
            (19, 25, '19-25세'),
            (25, float('inf'), '25세 이상')
        ]
        
        stats['age_distribution'] = {
            label: len([r for r in reliable_results 
                       if age_range[0] <= r['predicted_age'] < age_range[1]])
            for age_range, label in [(r[:2], r[2]) for r in age_ranges]
        }
    
    # 통계 정보 저장
    stats_file = os.path.join(output_path, 'statistics.json')
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    
    logging.info(f"통계 정보 생성 완료: {stats_file}")
    
    # 요약 정보 출력
    logging.info("\n=== 통계 요약 ===")
    logging.info(f"총 사용자 수: {stats['total_users']}")
    logging.info(f"총 이미지 수: {stats['total_images']}")
    logging.info(f"얼굴이 있는 이미지 수: {stats['images_with_faces']}")
    logging.info(f"신뢰할 수 있는 예측 수: {stats['reliable_predictions']}")
    logging.info(f"미성년자 예측 수: {stats['underage_predictions']}")
    logging.info(f"성인 예측 수: {stats['adult_predictions']}")
    if stats['average_age']:
        logging.info(f"평균 나이: {stats['average_age']:.1f}")
    logging.info("\n나이 분포:")
    for label, count in stats['age_distribution'].items():
        logging.info(f"  {label}: {count}")

if __name__ == "__main__":
    data_path = "data/policemonitor_20241216-20241222"
    output_path = "output"
    generate_report(data_path, output_path) 