import cv2
import numpy as np
import json

# 전역 변수 설정
ROI_HEIGHT_RATIO = 0.6  # 기본값 0.8 (80%)

def canny(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # 점선을 더 잘 감지하기 위한 전처리
    # 1. 가우시안 블러 강화
    blur = cv2.GaussianBlur(gray, (7, 7), 0)
    
    # 2. 이미지 개선을 위한 CLAHE 적용
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    enhanced = clahe.apply(blur)
    
    # 3. 모폴로지 연산으로 점선 연결
    kernel = np.ones((5,5), np.uint8)
    dilated = cv2.dilate(enhanced, kernel, iterations=1)
    eroded = cv2.erode(dilated, kernel, iterations=1)
    
    # 4. 캐니 엣지 파라미터 조정
    canny = cv2.Canny(eroded, 30, 150)  # 낮은 임계값으로 조정
    
    return canny

def region_of_interest(image):
    height = image.shape[0]
    width = image.shape[1]
    
    bottom_padding = 0
    roi_height = int(height * (1 - ROI_HEIGHT_RATIO))  # ROI_HEIGHT_RATIO에 맞춰 조정
    
    polygons = np.array([
        [(50, height-bottom_padding), 
         (width-50, height-bottom_padding), 
         (width-100, height-roi_height), 
         (100, height-roi_height)]
    ])
    mask = np.zeros_like(image)
    cv2.fillPoly(mask, polygons, 255)
    masked_image = cv2.bitwise_and(image, mask)
    return masked_image

def merge_close_lines(lines, min_distance=50):
    """가까운 선들을 하나로 합치는 함수"""
    if lines is None or len(lines) < 2:
        return lines
        
    merged_lines = []
    used = [False] * len(lines)
    
    for i in range(len(lines)):
        if used[i]:
            continue
            
        current_line = lines[i][0]
        x1, y1, x2, y2 = current_line
        x_avg = (x1 + x2) / 2
        
        # 현재 선과 가까운 다른 선들을 찾아서 평균 계산
        close_lines = [current_line]
        used[i] = True
        
        for j in range(i + 1, len(lines)):
            if used[j]:
                continue
                
            other_line = lines[j][0]
            ox1, oy1, ox2, oy2 = other_line
            other_x_avg = (ox1 + ox2) / 2
            
            # x 좌표의 평균값 차이로 거리 계산
            if abs(x_avg - other_x_avg) < min_distance:
                close_lines.append(other_line)
                used[j] = True
        
        if len(close_lines) >= 1:
            # 가까운 선들의 평균 계산
            avg_line = np.mean(close_lines, axis=0)
            merged_lines.append(np.array([avg_line], dtype=np.int32))
    
    return merged_lines if merged_lines else None

class Coin:
    def __init__(self, x, y, size=10):
        self.x = x
        self.y = y
        self.size = size
        self.speed = 5  # 코인이 아래로 내려오는 속도

    def update(self, slope):
        # 코인을 아래로 이동하면서 차선 기울기에 따라 x좌표도 조정
        self.y += self.speed
        self.x += self.speed * slope
        # 크기도 점점 커지게 (원근감)
        self.size = min(25, self.size + 0.5)

def analyze_frame(frame):
    """한 프레임을 분석하여 차선 정보와 점수를 JSON 형식으로 반환하는 함수"""
    
    # 결과를 저장할 딕셔너리
    result = {
        "score": None,
        "frame_id": 0,
        "road_outline": None,
        "coins": []
    }
    
    # static 변수로 coins 리스트와 frame_count 관리
    if not hasattr(analyze_frame, 'coins'):
        analyze_frame.coins = []
    if not hasattr(analyze_frame, 'frame_count'):
        analyze_frame.frame_count = 0
    
    analyze_frame.frame_count += 1
    
    height = frame.shape[0]
    width = frame.shape[1]
    
    # 차선 검출
    canny_image = canny(frame)
    cropped_image = region_of_interest(canny_image)
    
    kernel = np.ones((3,15), np.uint8)
    processed = cv2.dilate(cropped_image, kernel, iterations=1)
    processed = cv2.erode(processed, kernel, iterations=1)
    
    lines = cv2.HoughLinesP(
        processed,
        rho=1,
        theta=np.pi/180,
        threshold=40,
        minLineLength=35,
        maxLineGap=100
    )
    
    # 차선 분석
    if lines is not None:
        # 기울기로 필터링된 선들
        filtered_lines = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            if y1 < height * ROI_HEIGHT_RATIO or y2 < height * ROI_HEIGHT_RATIO:
                continue
            
            if x2 != x1:
                slope = (y2 - y1) / (x2 - x1)
                if (slope > 0.05) or slope < -0.5:
                    filtered_lines.append(line)
        
        # 가까운 선들 병합
        right_lines = []
        if filtered_lines:
            merged_lines = merge_close_lines(filtered_lines)
            if merged_lines is not None:
                for line in merged_lines:
                    x1, y1, x2, y2 = line[0]
                    x_avg = (x1 + x2) / 2
                    right_lines.append((line[0], x_avg))
        
        # 차선 정보 추출
        if len(right_lines) >= 2:
            right_lines.sort(key=lambda x: x[1], reverse=True)
            right_most_line = right_lines[0][0]
            second_right_line = right_lines[1][0]
            
            x1_r, y1_r, x2_r, y2_r = right_most_line
            x1_s, y1_s, x2_s, y2_s = second_right_line
            
            if y2_r != y1_r and y2_s != y1_s:
                slope_r = (x2_r - x1_r) / (y2_r - y1_r)
                slope_s = (x2_s - x1_s) / (y2_s - y1_s)
                
                steep_enough = abs(slope_r) > 0.5 and abs(slope_s) > 0.5
                
                bottom_y = height - 30
                top_y = height * ROI_HEIGHT_RATIO
                
                bottom_x_r = x1_r + slope_r * (bottom_y - y1_r)
                bottom_x_s = x1_s + slope_s * (bottom_y - y1_s)
                top_x_r = x1_r + slope_r * (top_y - y1_r)
                top_x_s = x1_s + slope_s * (top_y - y1_s)
                
                # 차선 간격 계산
                lane_width = abs(bottom_x_r - bottom_x_s)
                
                # 중앙선 좌표 계산
                center_x = width / 2
                
                # 차선 간격이 충분히 넓고 기울기가 충분할 때
                if lane_width > 100 and steep_enough and lane_width < 500:
                    # road_outline 정보 업데이트
                    result["road_outline"] = {
                        "bottom_x_r": float(bottom_x_r),
                        "bottom_x_s": float(bottom_x_s),
                        "bottom_y": float(bottom_y),
                        "top_x_r": float(top_x_r),
                        "top_x_s": float(top_x_s),
                        "top_y": float(top_y)
                    }
                    
                    # 점수 계산
                    if (min(bottom_x_r, bottom_x_s) <= center_x <= max(bottom_x_r, bottom_x_s) and
                        min(top_x_r, top_x_s) <= center_x <= max(top_x_r, top_x_s)):
                        result["score"] = 100.0
                    else:
                        result["score"] = 0.0
                    
                    # 대표 코인 생성
                    coin_x = (top_x_r + top_x_s) / 2
                    coin_y = top_y
                    coin_size = 10.0
                    result["coins"] = [{
                        "x": float(coin_x),
                        "y": float(coin_y),
                        "r": float(coin_size)
                    }]
    
    return result

def process_single_frame(frame_path):
    """이미지 파일을 읽어서 분석하는 함수"""
    frame = cv2.imread(frame_path)
    if frame is None:
        return json.dumps({"error": "Failed to load image"})
    
    result = analyze_frame(frame)
    return json.dumps(result, indent=2)

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python frame_analyzer.py <image_path>")
        sys.exit(1)
    
    print(process_single_frame(sys.argv[1])) 