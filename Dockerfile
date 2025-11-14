# Dockerfile
# 1. Base Image
FROM python:3.12-slim

# 2. Set Working Directory
WORKDIR /app

# 3. Install uv (가장 먼저 uv를 설치합니다)
# 이 레이어는 거의 변경되지 않으므로 캐시 효율이 좋습니다.
RUN pip install --no-cache-dir uv

# 4. Copy and Install Dependencies (uv 사용)
# requirements.txt를 먼저 복사하여 Docker 캐시 활용
COPY pyproject.toml .

# 5. Install Dependencies directly from pyproject.toml
# --system: 가상환경을 만들지 않고 도커 시스템 파이썬에 직접 설치 (이미지 크기 최적화)
RUN uv pip install --no-cache --system -r pyproject.toml

# 5. Copy Application Code
# (소스코드 변경 시 여기부터 다시 빌드됨)
COPY . .

# 6. Expose Port (Streamlit default)
# 도커 이미지는 내부적으로 8000번(백), 8501번(프론트엔드)포트를 사용 
EXPOSE 8000 8501

# 7. Default Command
CMD ["/bin/bash"]