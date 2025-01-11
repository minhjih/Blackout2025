# Python 3.8 이미지를 기반으로 설정
FROM python:3.8-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 라이브러리 설치
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Python 패키지 요구사항 파일 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 코드 복사
COPY lane_detection.py .
COPY main.py .
COPY test_road.mp4 .

# 컨테이너 실행 시 실행할 명령
CMD ["python", "main.py"] 