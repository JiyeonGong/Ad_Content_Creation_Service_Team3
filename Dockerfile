# 1. Base Image
# 파이썬 버전
FROM python:3.12-slim

# 2. Set Working Directory
# 작업 디렉토리를 /app으로 설정
WORKDIR /app

# 3. Copy and Install Dependencies
# (Copy requirements first to leverage Docker cache)
COPY requirements.txt requirements.txt 
RUN pip install --no-cache-dir -r requirements.txt 
# 여기서 requirements 복사하고 설치, 소스코드가 바뀌어도 라이브러리 잘 받아와요

# 4. Copy Application Code
# 우리 소스코드 전체 복사
COPY . .

# 5. Expose Port (Streamlit default)
# 8501포트에서 실행
EXPOSE 8501

# 6. Default Command (Set to run streamlit)
# (We will override this in docker-compose.yml for development)
CMD ["streamlit", "run", "src/app.py"]