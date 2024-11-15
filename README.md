# Pyannote-Whisper FastAPI Server

음성 파일에서 화자를 분리하고 텍스트로 변환하는 API 서버입니다.

## 로컬 개발 환경 설정

### 1. 가상환경 설정
```shell
# Python 3.11로 새 가상환경 생성
python3.11 -m venv pyannote-env
source pyannote-env/bin/activate

# 필요한 패키지 설치
pip install pyannote.audio openai-whisper git+https://github.com/keisokoo/pyannote-whisper \
    python-dotenv fastapi python-multipart uvicorn PyJWT python-magic

# OS별 추가 설치
## macOS
brew install libmagic

# numpy 버전 다운그레이드 (필수)
pip uninstall numpy
pip install 'numpy<2.0'
```

### 2. 환경 변수 설정
`.env` 파일 생성:
```shell
HUGGING_FACE_TOKEN=<your_hugging_face_token>
JWT_SECRET=<your_jwt_secret>
TEST_TOKEN=<your_test_token>
```

### 3. 서버 실행
```shell
python api.py
```

### 4. API 테스트
```shell
curl -X POST "http://localhost:8088/transcribe" \
     -H "accept: application/json" \
     -H "Authorization: your_token_here" \
     -F "file=@audio.wav" \
     -F "speaker_count=3" \
     -F "language=ko" \
     -F "temperature=0.0" \
     -F "no_speech_threshold=0.6" \
     -F "initial_prompt=다음은 한국어 대화입니다."
```

## 서버 배포 가이드

### 1. GCP Compute Engine 설정

```shell
# Conda 환경 설정
conda create -n pyannote python=3.11
conda activate pyannote

# 시스템 패키지 설치
sudo apt update
sudo apt install -y ffmpeg libsndfile1-dev libmagic1 sox libsox-fmt-all

# Python 패키지 설치
pip install pyannote.audio openai-whisper git+https://github.com/keisokoo/pyannote-whisper \
    python-dotenv fastapi python-multipart uvicorn PyJWT python-magic

# numpy 다운그레이드
pip uninstall numpy
pip install 'numpy<2.0'

# 환경변수 설정
vi .env
HUGGING_FACE_TOKEN=<your_hugging_face_token>
JWT_SECRET=<your_jwt_secret>
TEST_TOKEN=<your_test_token>
```

### 2. 방화벽 설정
```shell
# VPC 방화벽 규칙 생성
gcloud compute firewall-rules create allow-fastapi \
    --direction=INGRESS \
    --priority=1000 \
    --network=default \
    --action=ALLOW \
    --rules=tcp:8088 \
    --source-ranges=0.0.0.0/0 \
    --target-tags=http-server
```

### 3. 고정 IP 설정
```shell
# 외부 IP 생성
gcloud compute addresses create pyannote-whisper-ip \
    --region asia-northeast3

# IP 목록 확인
gcloud compute addresses list

# 인스턴스에 IP 할당
gcloud compute instances delete-access-config 인스턴스이름 \
    --access-config-name "External NAT"

gcloud compute instances add-access-config 인스턴스이름 \
    --access-config-name "External NAT" \
    --address 외부아이피
```

### 4. Caddy 설정

```shell
# Caddy 설치
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install caddy

# Caddy 설정
sudo vi /etc/caddy/Caddyfile
```

Caddyfile 내용:
```
api.yourdomain.com {
    reverse_proxy localhost:8088
    
    request_body {
        max_size 1GB
    }
}
```

```shell
# Caddy 서비스 시작
sudo systemctl restart caddy
sudo systemctl enable caddy

# 상태 확인
sudo systemctl status caddy
```

### 5. 서비스 설정

서비스 파일 생성:
```shell
sudo vi /etc/systemd/system/fastapi.service
```

서비스 파일 내용:
```ini
[Unit]
Description=FastAPI Whisper Service
After=network.target

[Service]
User=sokoo
WorkingDirectory=/home/sokoo/pyannote-whisper-fastapi
ExecStart=/opt/conda/envs/pyannote/bin/python api.py
Restart=always

[Install]
WantedBy=multi-user.target
```

서비스 관리:
```shell
# 서비스 시작
sudo systemctl start fastapi
sudo systemctl enable fastapi

# 상태 확인
sudo systemctl status fastapi

# 로그 확인
sudo journalctl -u fastapi -f

# 서비스 재시작
sudo systemctl restart fastapi
```

## 지원하는 파일 형식
- WAV (audio/wav, audio/x-wav)
- MP3 (audio/mpeg, audio/mp3)
- M4A (audio/m4a, audio/mp4, audio/x-m4a)
- FLAC (audio/flac)
- OGG (audio/ogg)

각 파일 형식은 실제 파일 MIME 타입을 검사하여 검증됩니다. 파일 확장자 변경으로 우회할 수 없습니다.