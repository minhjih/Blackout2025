import cv2
import numpy as np
import matplotlib.pyplot as plt

# 전역 변수 설정
ROI_HEIGHT_RATIO = 0.8  # 기본값 0.8 (80%)

# 전역 변수 추가
last_detected_lines = None
last_detection_frame = 0
DETECTION_INTERVAL = 20  # 20프레임마다 검출

def set_roi_height(ratio):
    """ROI 높이 비율을 설정하는 함수"""
    global ROI_HEIGHT_RATIO
    ROI_HEIGHT_RATIO = ratio

def reset_detection_counter():
    """차선 검출 카운터를 초기화하는 함수"""
    global last_detection_frame
    last_detection_frame = 0

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

def display_lines(image, lines):
    line_image = np.zeros_like(image)
    height = image.shape[0]
    width = image.shape[1]
    
    # 오인 리스트 (static variable로 유지)
    if not hasattr(display_lines, 'coins'):
        display_lines.coins = []
    if not hasattr(display_lines, 'frame_count'):
        display_lines.frame_count = 0
    
    display_lines.frame_count += 1
    
    # 오른쪽에서 첫 번째와 두 번째 차선 찾기
    right_most_line = None
    second_right_line = None
    right_lines = []
    
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
        if filtered_lines:
            merged_lines = merge_close_lines(filtered_lines)
            if merged_lines is not None:
                for line in merged_lines:
                    x1, y1, x2, y2 = line[0]
                    x_avg = (x1 + x2) / 2
                    right_lines.append((line[0], x_avg))
                    cv2.line(line_image, (x1, y1), (x2, y2), (0, 0, 255), 3)
        
        # x 좌표 평균값을 기준으로 정렬
        if right_lines:
            right_lines.sort(key=lambda x: x[1], reverse=True)
            if len(right_lines) >= 1:
                right_most_line = right_lines[0][0]
            if len(right_lines) >= 2:
                second_right_line = right_lines[1][0]
    
    # 두 차선이 모두 검출된 경우 사이 영역을 초록색으로 채우기
    if right_most_line is not None and second_right_line is not None:
        x1_r, y1_r, x2_r, y2_r = right_most_line
        x1_s, y1_s, x2_s, y2_s = second_right_line
        
        if y2_r != y1_r and y2_s != y1_s:
            slope_r = (x2_r - x1_r) / (y2_r - y1_r)
            slope_s = (x2_s - x1_s) / (y2_s - y1_s)
            
            # 두 차선의 기울기가 모두 1보다 큰 경우에만 코인 생성
            steep_enough = abs(slope_r) > 0.5 and abs(slope_s) > 0.5
            
            bottom_y = height - 30
            top_y = height * ROI_HEIGHT_RATIO
            
            bottom_x_r = x1_r + slope_r * (bottom_y - y1_r)
            bottom_x_s = x1_s + slope_s * (bottom_y - y1_s)
            top_x_r = x1_r + slope_r * (top_y - y1_r)
            top_x_s = x1_s + slope_s * (top_y - y1_s)
            
            # 차선 간격 계산
            lane_width = abs(bottom_x_r - bottom_x_s)
            
            # 차선 간격이 충분히 넓고 기울기가 충분할 때만 코인 생성
            if lane_width > 100 and steep_enough and lane_width < 500:  
                if display_lines.frame_count % 15 == 0:
                    coin_x = (top_x_r + top_x_s) / 2
                    coin_y = top_y
                    display_lines.coins.append(Coin(coin_x, coin_y))
            
            # 코인 업데이트 및 그리기
            new_coins = []
            for coin in display_lines.coins:
                # 차선의 평균 기울기로 코인 이동
                avg_slope = (slope_r + slope_s) / 2
                coin.update(avg_slope)
                
                # 화면 안에 있는 코인만 유지
                if coin.y < height:
                    # 코인 그리기 (노란색 원)
                    cv2.circle(line_image, 
                             (int(coin.x), int(coin.y)), 
                             int(coin.size), 
                             (0, 255, 255), 
                             -1)  # -1은 원을 채우기
                    # 광택 효과
                    highlight_size = max(2, int(coin.size // 3))
                    cv2.circle(line_image, 
                             (int(coin.x - coin.size//3), int(coin.y - coin.size//3)),
                             highlight_size, 
                             (255, 255, 255), 
                             -1)
                    new_coins.append(coin)
            
            display_lines.coins = new_coins
            
            # 영역 채우기
            polygon = np.array([
                [int(bottom_x_r), int(bottom_y)],
                [int(top_x_r), int(top_y)],
                [int(top_x_s), int(top_y)],
                [int(bottom_x_s), int(bottom_y)]
            ], np.int32)
            
            overlay = np.zeros_like(image)
            cv2.fillPoly(overlay, [polygon], (0, 255, 0))
            cv2.addWeighted(overlay, 0.5, line_image, 1, 0, line_image)
    
    return line_image

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

def process_frame(frame):
    global last_detected_lines, last_detection_frame
    
    lane_image = np.copy(frame)
    
    # 30프레임마다 새로운 차선 검출
    if last_detection_frame % DETECTION_INTERVAL == 0:
        canny_image = canny(lane_image)
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
        
        if lines is not None:
            last_detected_lines = lines
    
    # 이전에 검출된 차선 사용
    line_image = display_lines(lane_image, last_detected_lines)
    combo_image = cv2.addWeighted(lane_image, 0.8, line_image, 1, 1)
    
    last_detection_frame += 1
    return combo_image

# main.py에서 프레임 카운트 초기화를 위한 함수 추가
def reset_detection_counter():
    global last_detection_frame
    last_detection_frame = 0 