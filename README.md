```shell
# Python 3.11로 새 가상환경 생성
python3.11 -m venv pyannote-env
source pyannote-env/bin/activate

# 필요한 패키지 재설치
pip install pyannote.audio
pip install openai-whisper
pip install git+https://github.com/keisokoo/pyannote-whisper
pip install python-dotenv

# numpy 버전 다운그레이드
pip uninstall numpy
pip install 'numpy<2.0'

python main.py
```

```shell
# 환경 변수 설정
.env
HUGGING_FACE_TOKEN=<your_hugging_face_token>
# api 의존성
pip install fastapi python-multipart uvicorn

# api 실행
python api.py

# 테스트
curl -X POST "http://localhost:8000/transcribe" \
     -H "accept: application/json" \
     -F "file=@audio.wav" \
     -F "speaker_count=3" \
     -F "language=ko" \
     -F "temperature=0.0" \
     -F "no_speech_threshold=0.6" \
     -F "initial_prompt=다음은 한국어 대화입니다."
```

# 배포 방법 1 GCP
# 현재 디렉토리에서
docker build -t speaker-diarization .
# HUGGING_FACE_TOKEN을 환경변수로 전달
docker run -p 8080:8080 -e HUGGING_FACE_TOKEN=your_token speaker-diarization
# 프로젝트 ID 설정
export PROJECT_ID=your-project-id

# Artifact Registry에 Docker 저장소 생성
gcloud artifacts repositories create speaker-diarization \
    --repository-format=docker \
    --location=asia-northeast3 \
    --description="Speaker Diarization API"

# 이미지에 태그 지정
docker tag speaker-diarization \
    asia-northeast3-docker.pkg.dev/$PROJECT_ID/speaker-diarization/api:v1

# 이미지 푸시
docker push asia-northeast3-docker.pkg.dev/$PROJECT_ID/speaker-diarization/api:v1

# Cloud Run에 배포:
gcloud run deploy speaker-diarization \
  --image asia-northeast3-docker.pkg.dev/$PROJECT_ID/speaker-diarization/api:v1 \
  --platform managed \
  --region asia-northeast3 \
  --memory 4Gi \
  --cpu 2 \
  --port 8080 \
  --min-instances 0 \
  --max-instances 10 \
  --set-env-vars "HUGGING_FACE_TOKEN=your_token" \
  --allow-unauthenticated

<!-- memory 4Gi: 메모리 할당
cpu 2: CPU 코어 수
min-instances 0: Serverless (요청 없을 때 0개)
max-instances 10: 최대 인스턴스 수
allow-unauthenticated: 공개 접근 허용 -->

# GPU 추가 (필요한 경우):
gcloud run deploy speaker-diarization \
  --image asia-northeast3-docker.pkg.dev/$PROJECT_ID/speaker-diarization/api:v1 \
  --platform managed \
  --region asia-northeast3 \
  --memory 4Gi \
  --cpu 2 \
  --port 8080 \
  --min-instances 0 \
  --max-instances 10 \
  --set-env-vars "HUGGING_FACE_TOKEN=your_token" \
  --allow-unauthenticated \
  --gpu-type=nvidia-tesla-t4 \
  --gpu-count=1