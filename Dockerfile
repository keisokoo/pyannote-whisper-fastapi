FROM pytorch/pytorch:2.1.0-cuda11.8-cudnn8-runtime

# 기본 의존성 설치
RUN apt-get update && apt-get install -y ffmpeg git

# Python 패키지 설치
RUN pip install --no-cache-dir \
  fastapi \
  uvicorn \
  python-multipart \
  python-dotenv \
  openai-whisper \
  pyannote.audio \
  git+https://github.com/keisokoo/pyannote-whisper

# 작업 디렉토리 설정
WORKDIR /app

# 환경 변수 설정
ENV HUGGING_FACE_TOKEN=""

# 소스 코드 복사
COPY api.py .
COPY .env .

# 포트 설정
EXPOSE 8080

# 실행
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8080"]