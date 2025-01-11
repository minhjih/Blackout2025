import cv2
from lane_detection import process_frame

def main():
    # 비디오 파일 열기
    cap = cv2.VideoCapture("test_road.mp4")
    
    # 출본 비디오 크기
    orig_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    orig_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    
    # 절반 크기 계산
    width = orig_width // 2
    height = orig_height // 2
    
    # 출력 비디오 설정
    out = cv2.VideoWriter('/app/output/output_video.mp4',
                         cv2.VideoWriter_fourcc(*'mp4v'),
                         fps, (width, height))  # 절반 크기로 출력
    
    print("영상 처리를 시작합니다...")
    print(f"입력 크기: {orig_width}x{orig_height}")
    print(f"출력 크기: {width}x{height}")
    frame_count = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # 프레임 크기 절반으로 축소
        frame = cv2.resize(frame, (width, height))
            
        # 프레임 처리
        result_frame = process_frame(frame)
        
        # 결과 저장
        out.write(result_frame)
        
        # 진행 상황 출력
        frame_count += 1
        if frame_count % 30 == 0:
            print(f"처리된 프레임: {frame_count}")
    
    print("영상 처리가 완료되었습니다.")
    print(f"출력 파일: /app/output/output_video.mp4")
    
    cap.release()
    out.release()

if __name__ == "__main__":
    main() 