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

# 소스 코드 복사
COPY *.py /app/

RUN mkdir -p /app/server
RUN chmod -R 755 /app/server
COPY server /app/server

# 실행 권한 설정
RUN chmod -R 755 /app

# AI 관련 파일들 복사
COPY AI_folder/* /app/

# 작업 디렉토리의 권한 설정
RUN chmod -R 755 /app

# Expose the port the app runs on
EXPOSE 5000

# Set environment variables for Flask
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV DEBUG=False

# Run the Flask application
CMD ["python", "app.py"]