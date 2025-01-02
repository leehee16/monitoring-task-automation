import os
import argparse
from src.utils import load_config, get_device, create_output_directories
from src.data_processor import DataProcessor

def main(config_path: str):
    """
    메인 실행 함수
    
    Args:
        config_path: 설정 파일 경로
    """
    # 설정 로드
    config = load_config(config_path)
    
    # 디바이스 설정
    device = get_device(config)
    print(f"Using device: {device}")
    
    # 출력 디렉토리 생성
    create_output_directories(config)
    
    # 데이터 처리기 초기화
    processor = DataProcessor(config, device)
    
    # 데이터 처리 실행
    results_df = processor.process_all_users(config['data']['input_dir'])
    
    # 결과 출력
    print("\n=== Processing Results ===")
    print(f"Total users processed: {len(results_df)}")
    print("\nAverage age by user:")
    for _, row in results_df.iterrows():
        if 'average_age' in row:
            print(f"User {row['user_id']}: {row['average_age']:.1f} years (±{row['age_std']:.1f})")
    
    print("\nFace detection ratios:")
    for _, row in results_df.iterrows():
        print(f"User {row['user_id']}: {row['face_ratio']*100:.1f}%")
    
    print(f"\nResults saved to: {os.path.join(config['data']['output_dir'], 'results.csv')}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Age Prediction from Images")
    parser.add_argument(
        "--config",
        type=str,
        default="config/config.yaml",
        help="Path to configuration file"
    )
    args = parser.parse_args()
    main(args.config)
