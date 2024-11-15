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
curl -X POST "http://localhost:8088/transcribe" \
     -H "accept: application/json" \
     -F "file=@audio.wav" \
     -F "speaker_count=3" \
     -F "language=ko" \
     -F "temperature=0.0" \
     -F "no_speech_threshold=0.6" \
     -F "initial_prompt=다음은 한국어 대화입니다."
```

# 배포 VM Compute engine

conda create -n pyannote python=3.11
conda activate pyannote


pip install pyannote.audio openai-whisper git+https://github.com/keisokoo/pyannote-whisper python-dotenv fastapi python-multipart uvicorn

sudo apt update
sudo apt install -y ffmpeg libsndfile1-dev

pip uninstall numpy
pip install 'numpy<2.0'

vi .env
환경변수 추가

python api.py

VPC 방화벽 규칙 생성 (콘솔에서):
gcloud compute firewall-rules create allow-fastapi \
    --direction=INGRESS \
    --priority=1000 \
    --network=default \
    --action=ALLOW \
    --rules=tcp:8088 \
    --source-ranges=0.0.0.0/0 \
    --target-tags=http-server


# 외부아이피 고정
gcloud compute addresses create pyannote-whisper-ip \
    --region asia-northeast3

gcloud compute addresses list

gcloud compute instances delete-access-config 인스턴스이름 \
    --access-config-name "External NAT"

gcloud compute instances add-access-config 인스턴스이름 \
    --access-config-name "External NAT" \
    --address 외부아이피

    
# nginx 설치
sudo apt install nginx

# nginx 설정
sudo nano /etc/nginx/sites-available/도메인명

server {
    listen 80;
    server_name 도메인명;

    location / {
        proxy_pass http://localhost:8088;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}

# 설정 활성화
sudo ln -s /etc/nginx/sites-available/도메인명 /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx


sudo vi /etc/systemd/system/fastapi.service
```
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

# 서비스 시작
sudo systemctl start fastapi
sudo systemctl enable fastapi  # 부팅 시 자동 시작

# 상태 확인
sudo systemctl status fastapi

# 로그 확인
sudo journalctl -u fastapi -f


curl -X POST "http://도메인주소/transcribe" \
  -H "accept: application/json" \
  -F "file=@audio.wav" \
  -F "speaker_count=3" \
  -F "language=ko" \
  -F "temperature=0.0" \
  -F "no_speech_threshold=0.6" \
  -F "initial_prompt=다음은 한국어 대화입니다."