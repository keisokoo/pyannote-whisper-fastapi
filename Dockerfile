FROM python:3.11-slim

# 시간대 설정을 비대화형으로 변경
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Seoul

# 기본 의존성 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
  ffmpeg \
  git \
  && rm -rf /var/lib/apt/lists/*

# Python 패키지 설치 (PyTorch MPS 지원 버전)
RUN pip install --no-cache-dir 'numpy<2.0' && \
  pip install --no-cache-dir \
  torch torchvision torchaudio && \
  pip install --no-cache-dir \
  fastapi \
  uvicorn \
  python-multipart \
  python-dotenv \
  openai-whisper \
  pyannote.audio \
  git+https://github.com/keisokoo/pyannote-whisper

# 작업 디렉토리 설정
WORKDIR /app

# 소스 코드 복사
COPY api.py .

# 포트 설정
ENV PORT=8088
EXPOSE 8088

# 실행
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8088"] 