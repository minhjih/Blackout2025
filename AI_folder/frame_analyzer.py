import cv2
import numpy as np
import json

# 전역 변수 설정
ROI_HEIGHT_RATIO = 0.55  # lane_detection.py와 동일하게 설정

def canny(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # 점선을 더 잘 감지하기 위한 전처리
    # 1. 가우시안 블러 강화
    blur = cv2.GaussianBlur(gray, (7, 7), 0)
    blur = cv2.GaussianBlur(gray, (7, 7), 0)  # 두 번 적용
    
    # 3. 모폴로지 연산으로 점선 연결
    kernel = np.ones((5,5), np.uint8)
    dilated = cv2.dilate(blur, kernel, iterations=1)
    eroded = cv2.erode(dilated, kernel, iterations=1)
    
    # 4. 캐니 엣지 파라미터 조정
    canny = cv2.Canny(eroded, 30, 150)
    
    return canny

def region_of_interest(image):
    height = image.shape[0]
    width = image.shape[1]
    
    # 하단 20% 제외
    bottom_padding = int(height * 0)
    # ROI_HEIGHT_RATIO에 맞춰 조정
    roi_height = int(height * (1 - ROI_HEIGHT_RATIO))
    
    polygons = np.array([
        [(width//3, height-bottom_padding), 
         (width, height-bottom_padding), 
         (width, roi_height), 
         (width//4, roi_height)]
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
    
    result = {
        "score": None,
        "frame_id": 0,
        "road_outline": None
    }
    
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
        threshold=20,
        minLineLength=25,
        maxLineGap=100
    )
    
    # 차선 분석
    if lines is not None:
        filtered_lines = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            if y1 < height * ROI_HEIGHT_RATIO or y2 < height * ROI_HEIGHT_RATIO:
                continue
            
            if x2 != x1:
                slope = (y2 - y1) / (x2 - x1)
                if abs(slope) > 2:  # lane_detection.py와 동일한 기울기 임계값
                    filtered_lines.append(line)
        
        right_lines = []
        if filtered_lines:
            merged_lines = merge_close_lines(filtered_lines)
            if merged_lines is not None:
                for line in merged_lines:
                    x1, y1, x2, y2 = line[0]
                    x_avg = (x1 + x2) / 2
                    right_lines.append((line[0], x_avg))
        
        if len(right_lines) >= 2:
            right_lines.sort(key=lambda x: x[1], reverse=True)
            right_most_line = right_lines[0][0]
            second_right_line = right_lines[1][0]
            
            x1_r, y1_r, x2_r, y2_r = right_most_line
            x1_s, y1_s, x2_s, y2_s = second_right_line
            
            if y2_r != y1_r and y2_s != y1_s:
                slope_r = (y2_r - y1_r) / (x2_r - x1_r)
                slope_s = (y2_s - y1_s) / (x2_s - x1_s)
                
                steep_enough = abs(slope_r) > 2 and abs(slope_s) > 2
                
                bottom_y = height - 30
                top_y = height * ROI_HEIGHT_RATIO
                
                bottom_x_r = x1_r + (bottom_y - y1_r) / slope_r
                bottom_x_s = x1_s + (bottom_y - y1_s) / slope_s
                top_x_r = x1_r + (top_y - y1_r) / slope_r
                top_x_s = x1_s + (top_y - y1_s) / slope_s
                
                center_x = width / 2
                
                if steep_enough:
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
