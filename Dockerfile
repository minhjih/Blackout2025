# 기본 이미지 사용
FROM python:3.9-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 라이브러리 설치
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    gdal-bin \
    libgdal-dev \
    python3-gdal \
    build-essential \
    python3-dev \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# GDAL 관련 환경 변수 설정
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

# Python 패키지 요구사항 파일 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir pip setuptools wheel
RUN pip install --no-cache-dir fiona
RUN pip install --no-cache-dir -r requirements.txt

# 소스 코드 및 리소스 복사
COPY AI_folder/ ./AI_folder/
COPY input/ ./input/

# output 폴더 생성
RUN mkdir -p output
RUN chmod -R 777 output

# 실행 권한 설정
RUN chmod -R 755 /app
# output 폴더 생성 및 권한 설정
RUN mkdir -p /app/output
RUN chmod -R 777 /app/output
# AI 관련 파일들 복사
COPY AI_folder/* /app/

# 입력 데이터 파일들을 input 디렉토리로 복사
COPY test_road*.mp4 /app/input/
COPY input/강남대치_geo_fence.json /app/input/
COPY input/regionid_560_test_data.csv /app/input/
COPY input/base_station.png /app/input/
COPY input/gold_station.png /app/input/

# 작업 디렉토리의 권한 설정
RUN chmod -R 755 /app
RUN chmod -R 777 /app/output

# 컨테이너 실행 시 실행할 명령
ENTRYPOINT ["python", "AI_folder/geo_visualizer.py"] 