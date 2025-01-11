import cv2
import numpy as np
import matplotlib.pyplot as plt

def canny(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    canny = cv2.Canny(blur, 50, 150)
    return canny

def display_lines(image, lines):
    line_image = np.zeros_like(image)
    height = image.shape[0]
    width = image.shape[1]
    
    # 차선 변경 가이드라인 그리기
    # 왼쪽 차선 변경
    cv2.arrowedLine(line_image, 
                    (width//2, height-50),
                    (width//4, height-50),
                    (0, 255, 0), 2, tipLength=0.3)
    # 오른쪽 차선 변경
    cv2.arrowedLine(line_image,
                    (width//2, height-50),
                    (3*width//4, height-50),
                    (0, 255, 0), 2, tipLength=0.3)
    
    # 차선 그리기
    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            if x2 != x1:
                slope = (y2 - y1) / (x2 - x1)
                if 0.2 < abs(slope):
                    cv2.line(line_image, (x1, y1), (x2, y2), (0, 0, 255), 3)
    
    return line_image

def region_of_interest(image):
    height = image.shape[0]
    width = image.shape[1]
    
    polygons = np.array([
        [(50, height), (width-50, height), (width-150, int(height/2)), (150, int(height/2))]
    ])
    mask = np.zeros_like(image)
    cv2.fillPoly(mask, polygons, 255)
    masked_image = cv2.bitwise_and(image, mask)
    return masked_image

def process_frame(frame):
    # 이미지 복사
    lane_image = np.copy(frame)
    
    # 엣지 검출
    canny_image = canny(lane_image)
    
    # 관심 영역 설정
    cropped_image = region_of_interest(canny_image)
    
    # 허프 변환으로 직선 검출
    lines = cv2.HoughLinesP(
        cropped_image,
        rho=1,
        theta=np.pi/180,
        threshold=40,
        minLineLength=40,
        maxLineGap=15
    )
    
    # 차선과 가이드라인 그리기
    line_image = display_lines(lane_image, lines)
    
    # 원본 이미지와 차선 이미지 합성
    combo_image = cv2.addWeighted(lane_image, 0.8, line_image, 1, 1)
    
    # 차선 변경 텍스트 추가
    height = frame.shape[0]
    width = frame.shape[1]
    cv2.putText(combo_image, "Left Lane", (width//4-40, height-20), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    cv2.putText(combo_image, "Right Lane", (3*width//4-40, height-20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    
    return combo_image 