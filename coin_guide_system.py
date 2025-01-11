import cv2
import numpy as np
import math
from ar_utils import ARUtils  # AR 관련 유틸리티 클래스
from lane_detection import ROI_HEIGHT_RATIO  # ROI 전역 변수 import

class SafetyGuideSystem:
    def __init__(self):
        self.ar_utils = ARUtils()
        self.coin_spacing = 50  # 코인 간 간격 (픽셀)
        self.coin_size = 30     # 코인 크기
        
    def detect_lane(self, frame):
        """차선 검출 함수"""
        # 이미지 크기 조정
        height, width = frame.shape[:2]
        frame = cv2.resize(frame, (960, 540))
        
        # 관심 영역(ROI) 정의
        roi_vertices = np.array([
            [(100, 540), (440, int(540 * (1-ROI_HEIGHT_RATIO))), 
             (520, int(540 * (1-ROI_HEIGHT_RATIO))), (860, 540)]
        ], dtype=np.int32)
        
        def region_of_interest(img, vertices):
            mask = np.zeros_like(img)
            cv2.fillPoly(mask, vertices, 255)
            masked_img = cv2.bitwise_and(img, mask)
            return masked_img
        
        # 이미지 전처리
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Canny 엣지 검출
        edges = cv2.Canny(blur, 50, 150)
        
        # ROI 적용
        roi_image = region_of_interest(edges, roi_vertices)
        
        # 허프 변환 파라미터
        rho = 2
        theta = np.pi/180
        threshold = 40
        min_line_length = 100
        max_line_gap = 50
        
        # 허프 변환으로 직선 검출
        lines = cv2.HoughLinesP(roi_image, rho, theta, threshold,
                               minLineLength=min_line_length,
                               maxLineGap=max_line_gap)
        
        if lines is None:
            return None
            
        # 차선 분류 및 평균 계산
        left_lines = []
        right_lines = []
        
        for line in lines:
            x1, y1, x2, y2 = line[0]
            if x2 == x1:
                continue
                
            slope = (y2 - y1) / (x2 - x1)
            if abs(slope) < 0.5:  # 수평에 가까운 선 제외
                continue
                
            if slope < 0:
                left_lines.append(line)
            else:
                right_lines.append(line)
        
        def average_line(lines):
            if len(lines) == 0:
                return None
                
            avg_line = np.mean(lines, axis=0, dtype=np.int32)
            x1, y1, x2, y2 = avg_line[0]
            
            # y 좌표 범위 설정
            y1 = frame.shape[0]  # 이미지 하단
            y2 = int(frame.shape[0] * ROI_HEIGHT_RATIO)  # ROI 높이에 맞춰 조정
            
            # x 좌표 계산
            slope = (y2 - y1) / (x2 - x1) if x2 != x1 else 0
            x1 = int(x1 + (y1 - y1) / slope) if slope != 0 else x1
            x2 = int(x2 + (y2 - y2) / slope) if slope != 0 else x2
            
            return np.array([[x1, y1, x2, y2]])
        
        # 최종 차선 계산
        final_lines = []
        left_avg = average_line(left_lines)
        right_avg = average_line(right_lines)
        
        if left_avg is not None:
            final_lines.append(left_avg)
        if right_avg is not None:
            final_lines.append(right_avg)
            
        if not final_lines:
            return None
            
        # 원본 이미지 크기로 좌표 변환
        scale_x = width / 960
        scale_y = height / 540
        
        adjusted_lines = []
        for line in final_lines:
            x1, y1, x2, y2 = line[0]
            adjusted_line = np.array([[
                int(x1 * scale_x),
                int(y1 * scale_y),
                int(x2 * scale_x),
                int(y2 * scale_y)
            ]])
            adjusted_lines.append(adjusted_line)
            
        return np.array(adjusted_lines)
    
    def place_coins(self, frame, lines):
        """차선 끝에 코인 배치"""
        if lines is None:
            return frame
            
        for line in lines:
            x1, y1, x2, y2 = line[0]
            # 차선의 방향 계산
            angle = math.atan2(y2-y1, x2-x1)
            
            # 차선을 따라 코인 배치
            current_x, current_y = x1, y1
            while current_x < x2 and current_y < y2:
                # AR 코인 렌더링
                frame = self.ar_utils.render_coin(frame, 
                                                (int(current_x), int(current_y)),
                                                self.coin_size)
                
                # 다음 코인 위치 계산
                current_x += self.coin_spacing * math.cos(angle)
                current_y += self.coin_spacing * math.sin(angle)
                
        return frame
    
    def draw_lanes(self, frame, lines):
        """검출된 차선을 프레임에 그리는 함수"""
        if lines is None:
            return frame
        
        # 차선을 그릴 이미지 생성
        lane_image = np.zeros_like(frame)
        
        # 왼쪽/오른쪽 차선 구분
        left_line = None
        right_line = None
        
        for line in lines:
            x1, y1, x2, y2 = line[0]
            slope = (y2 - y1) / (x2 - x1) if x2 != x1 else 0
            
            if slope < 0:  # 왼쪽 차선
                left_line = line[0]
            else:  # 오른쪽 차선
                right_line = line[0]
        
        if left_line is not None and right_line is not None:
            # 차선 사이 영역을 채우기 위한 다각형 좌표
            polygon_points = np.array([
                [left_line[0], left_line[1]],
                [left_line[2], left_line[3]],
                [right_line[2], right_line[3]],
                [right_line[0], right_line[1]]
            ], np.int32)
            
            # 차선 사이 영역 채우기 (반투명 녹색)
            cv2.fillPoly(lane_image, [polygon_points], (0, 200, 0))
            
            # 왼쪽 차선 그리기 (빨간색)
            cv2.line(lane_image, 
                    (left_line[0], left_line[1]), 
                    (left_line[2], left_line[3]), 
                    (0, 0, 255), 5)
            
            # 오른쪽 차선 그리기 (빨간색)
            cv2.line(lane_image, 
                    (right_line[0], right_line[1]), 
                    (right_line[2], right_line[3]), 
                    (0, 0, 255), 5)
        
        # 원본 이미지와 차선 이미지를 합성
        result = cv2.addWeighted(frame, 1, lane_image, 0.3, 0)
        
        return result
    
    def process_frame(self, frame):
        """실시간 프레임 처리"""
        lines = self.detect_lane(frame)
        
        # 차선 그리기
        frame_with_lanes = self.draw_lanes(frame, lines)
        
        # 코인 배치
        result_frame = self.place_coins(frame_with_lanes, lines)
        
        return result_frame 