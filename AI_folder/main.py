import cv2
import os
from lane_detection import process_frame, set_roi_height, reset_detection_counter, DETECTION_INTERVAL

def main():
    # ROI 높이 설정 (화면 상단 80%부터 검출)
    set_roi_height(0.8)
    
    # 차선 검출 카운터 초기화
    reset_detection_counter()
    
    # 비디오 파일 경로
    video_path = "test_road_3.mp4"
    
    # 파일 존재 여부 확인
    if not os.path.exists(video_path):
        print(f"에러: 비디오 파일을 찾을 수 없습니다: {video_path}")
        return
    
    # 비디오 파일 열기
    cap = cv2.VideoCapture(video_path)
    
    # 비디오 파일이 제대로 열렸는지 확인
    if not cap.isOpened():
        print(f"에러: 비디오 파일을 열 수 없습니다: {video_path}")
        return
    
    # 출본 비디오 크기
    orig_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    orig_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    
    # 비디오 정보 출력
    print(f"\n비디오 파일 정보:")
    print(f"파일 경로: {os.path.abspath(video_path)}")
    print(f"파일 크기: {os.path.getsize(video_path) / (1024*1024):.1f}MB")
    
    # fps가 0이면 기본값 30으로 설정
    if fps <= 0:
        print("경고: FPS를 읽을 수 없어 기본값 30으로 설정합니다.")
        fps = 30
    
    # 1/2 크기 계산
    width = orig_width // 2
    height = orig_height // 2
    
    # 출력 디렉토리 확인 및 생성
    output_dir = '/app/output'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # 출력 비디오 설정
    out = cv2.VideoWriter(f'{output_dir}/output_video.mp4',
                         cv2.VideoWriter_fourcc(*'mp4v'),
                         fps, (width, height))
    
    print("\n영상 처리를 시작합니다...")
    print(f"입력 크기: {orig_width}x{orig_height}")
    print(f"출력 크기: {width}x{height}")
    print(f"FPS: {fps}")
    print(f"차선 검출 간격: {DETECTION_INTERVAL} 프레임 ({DETECTION_INTERVAL/fps:.1f}초)")
    frame_count = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            if frame_count == 0:
                print("에러: 첫 프레임을 읽을 수 없습니다.")
            break
        
        # 프레임 크기를 1/2로 축소
        frame = cv2.resize(frame, (width, height))
        result_frame = process_frame(frame)
        out.write(result_frame)
        
        frame_count += 1
        if frame_count % 30 == 0:
            print(f"처리된 프레임: {frame_count}")
    
    print(f"\n처리 완료:")
    print(f"총 처리된 프레임: {frame_count}")
    print(f"출력 파일: {os.path.join(output_dir, 'output_video.mp4')}")
    
    cap.release()
    out.release()

if __name__ == "__main__":
    main() 