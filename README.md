# Pyannote-Whisper FastAPI Server

음성 파일에서 화자를 분리하고 텍스트로 변환하는 API 서버입니다.

## 빠른 시작 가이드

### 1. 필수 준비사항
- Python 3.11
- Conda
- Hugging Face 토큰 (https://huggingface.co/settings/tokens)

### 2. 자동 설치 스크립트 실행
```bash
# 설치 스크립트 실행
chmod +x install.sh
./install.sh

# Caddy 설정 스크립트 실행 (도메인이 있는 경우)
chmod +x setup_caddy.sh
./setup_caddy.sh
```

### 3. 설정 필요 항목
1. `.env` 파일에 토큰 설정
   - HUGGING_FACE_TOKEN
   - JWT_SECRET
   - TEST_TOKEN
2. DNS 설정 (도메인 사용시)
   - 도메인을 서버 IP로 연결

### 4. 서비스 시작
```bash
sudo systemctl start fastapi
sudo systemctl start caddy  # 도메인 사용시
```

---

<details>
<summary><h2 style="display: inline-block; color: #0366d6;">📖 상세 설치 및 설정 가이드</h2></summary>

이하 내용은 수동 설치 및 설정에 대한 상세 가이드입니다.

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

</details>

<br/>

<details>
<summary><h2 style="display: inline-block; color: #0366d6;">📁 지원하는 파일 형식</h2></summary>

### 모든 기능 지원 (음성 인식 + 화자 분리)
- WAV (audio/wav, audio/x-wav)
- MP3 (audio/mpeg, audio/mp3)
- FLAC (audio/flac)
- OGG (audio/ogg)

### 음성 인식만 지원 (Whisper)
- M4A (audio/m4a, audio/mp4, audio/x-m4a)
- AIFF (audio/aiff, audio/x-aiff)
- OPUS (audio/opus)
- WebM (audio/webm, video/webm)
- MP4 (video/mp4)
- AVI (video/x-msvideo)
- MOV (video/quicktime)
- MKV (video/x-matroska)

각 파일 형식은 실제 파일 MIME 타입을 검사하여 검증됩니다. 파일 확장자 변경으로 우회할 수 없습니다.

**참고**: 화자 분리(Pyannote)가 지원되지 않는 형식의 경우, 자동으로 WAV 형식으로 변환하여 처리합니다. 이 경우 처리 시간이 약간 증가할 수 있습니다.

</details>

<br/>

<details>
<summary><h2 style="display: inline-block; color: #0366d6;">🔍 API 요청 형식</h2></summary>

### POST /transcribe

**Content-Type**: `multipart/form-data`

#### Request Parameters

| 필드 | 타입 | 필수 | 기본값 | 설명 |
|------|------|------|--------|------|
| file | File | ✓ | - | 오디오 파일 |
| speaker_count | Integer | | 2 | 화자 수 |
| language | String | | null | 언어 코드 (null: 자동감지) |
| temperature | Float | | 0.0 | 생성 다양성 (0.0~1.0) |
| no_speech_threshold | Float | | 0.6 | 무음 감지 임계값 |
| initial_prompt | String | | "다음은 한국어 대화입니다." | 초기 프롬프트 |

#### Headers

| 헤더 | 필수 | 설명 |
|------|------|------|
| Authorization | ✓ | JWT 토큰 또는 테스트 토큰 |

#### 예제 요청
```bash
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

#### 응답 형식
```json
{
    "results": [
        {
            "speaker": 0,
            "start": 0.0,
            "end": 2.5,
            "text": "안녕하세요."
        },
        {
            "speaker": 1,
            "start": 2.8,
            "end": 4.2,
            "text": "네, 안녕하세요."
        }
    ]
}
```

</details>

<br/>

<details>
<summary><h2 style="display: inline-block; color: #0366d6;">🌐 지원 언어 코드</h2></summary>

Whisper 모델이 지원하는 언어 코드 목록입니다. `language` 파라미터에 사용할 수 있습니다.
(null이나 빈 값으로 두면 자동으로 언어를 감지합니다)

| 코드 | 언어 | 코드 | 언어 |
|------|------|------|------|
| af | 아프리칸스어 | ar | 아랍어 |
| hy | 아르메니아어 | az | 아제르바이잔어 |
| be | 벨라루스어 | bs | 보스니아어 |
| bg | 불가리아어 | ca | 카탈로니아어 |
| zh | 중국어 | hr | 크로아티아어 |
| cs | 체코어 | da | 덴마크어 |
| nl | 네덜란드어 | en | 영어 |
| et | 에스토니아어 | fi | 핀란드어 |
| fr | 프랑스어 | gl | 갈리시아어 |
| de | 독일어 | el | 그리스어 |
| he | 히브리어 | hi | 힌디어 |
| hu | 헝가리어 | is | 아이슬란드어 |
| id | 인도네시아어 | it | 이탈리아어 |
| ja | 일본어 | kn | 칸나다어 |
| kk | 카자흐어 | ko | 한국어 |
| lv | 라트비아어 | lt | 리투아니아어 |
| mk | 마케도니아어 | ms | 말레이어 |
| ml | 말라얄람어 | mt | 몰타어 |
| mr | 마라티어 | ne | 네팔어 |
| no | 노르웨이어 | fa | 페르시아어 |
| pl | 폴란드어 | pt | 포르투갈어 |
| ro | 루마니아어 | ru | 러시아어 |
| sr | 세르비아어 | sk | 슬로바키아어 |
| sl | 슬로베니아어 | es | 스페인어 |
| sw | 스와힐리어 | sv | 스웨덴어 |
| tl | 타갈로그어 | ta | 타밀어 |
| th | 태국어 | tr | 터키어 |
| uk | 우크라이나어 | ur | 우르두어 |
| vi | 베트남어 | cy | 웨일스어 |
</details>
