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

# input과 output 디렉토리 생성
RUN mkdir -p /app/input /app/output
RUN chmod 777 /app/input /app/output

# AI 관련 파일들 복사
COPY AI_folder/* /app/

# 테스트 비디오 파일들을 input 디렉토리로 복사
COPY test_road*.mp4 /app/input/

# 컨테이너 실행 시 실행할 명령
ENTRYPOINT ["python", "frame_analyzer.py"] 