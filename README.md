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
<summary><h2 style="display: inline-block; color: #0366d6;">📝 작업 결과 관리</h2></summary>

- 작업 처리 제한 시간: 3시간
- 작업 결과는 클라이언트에게 전달된 즉시 삭제됩니다
- 조회되지 않은 작업 결과는 3시간 후 자동으로 만료됩니다
- 한 번 조회된 작업 ID로 재조회 시 `{"status": "pending"}`이 반환됩니다
</details>

<br/>

<details>
<summary><h2 style="display: inline-block; color: #0366d6;">📖 상세 설치 및 설정 가이드</h2></summary>

이하 내용은 수동 설치 및 설정에 대한 상세 가이드입니다.

## 서버 배포 가이드

### 1. GCP Compute Engine 설정

```shell
# Conda 환경 설정
conda create -n pyannote python=3.11
conda activate pyannote

# 시스템 패키지 설치
sudo apt update
sudo apt install -y ffmpeg libsndfile1-dev libmagic1 sox libsox-fmt-all redis-server

# Python 패키지 설치
pip install pyannote.audio openai-whisper git+https://github.com/keisokoo/pyannote-whisper \
    python-dotenv fastapi python-multipart uvicorn PyJWT python-magic celery[redis] redis

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

Redis 서비스 확인:
```shell
sudo systemctl status redis-server
```

FastAPI 서비스 파일 생성:
```shell
sudo vi /etc/systemd/system/fastapi.service
```

FastAPI 서비스 파일 내용:
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

Celery 워커 서비스 파일 생성:
```shell
sudo vi /etc/systemd/system/celery.service
```

Celery 서비스 파일 내용:
```ini
[Unit]
Description=Celery Worker Service
After=network.target redis-server.service

[Service]
Type=simple
User=sokoo
WorkingDirectory=/home/sokoo/pyannote-whisper-fastapi
Environment=PYTHONPATH=/home/sokoo/pyannote-whisper-fastapi
ExecStart=/opt/conda/envs/pyannote/bin/celery -A tasks worker --loglevel=info
Restart=always
RestartSec=10s

# 추가할 설정
TimeoutStopSec=10
KillMode=mixed
KillSignal=SIGTERM

[Install]
WantedBy=multi-user.target
```

서비스 관리:
```shell
# 서비스 파일 리로드
sudo systemctl daemon-reload

# 서비스 시작
sudo systemctl start fastapi
sudo systemctl start celery

# 서비스 자동 시작 설정
sudo systemctl enable fastapi
sudo systemctl enable celery

# 상태 확인
sudo systemctl status fastapi
sudo systemctl status celery

# 로그 확인
sudo journalctl -u fastapi -f
sudo journalctl -u celery -f

# 서비스 재시작
sudo systemctl restart fastapi
sudo systemctl restart celery
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

오디오 파일을 업로드하고 처리를 시작합니다.

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
    "task_id": "1234-5678-90ab-cdef"
}
```

### GET /result/{task_id}

처리 상태와 결과를 확인합니다.

#### Headers
| 헤더 | 필수 | 설명 |
|------|------|------|
| Authorization | ✓ | JWT 토큰 또는 테스트 토큰 |

#### 응답 형식

1. 대기 중:
```json
{
    "status": "pending"
}
```

2. 처리 중:
```json
{
    "status": "processing",
    "info": "transcribing"  // 현재 진행 중인 단계
}
```

가능한 info 값:
- "initializing": 초기화 중
- "transcribing": 음성 인식 중
- "diarizing": 화자 분리 중
- "combining": 결과 통합 중

3. 처리 완료:
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
    ],
    "status": "completed"
}
```

4. 에러 발생:
```json
{
    "status": "failed",
    "error": "에러 메시지"
}
```

#### 예제 요청
```bash
curl -X GET "http://localhost:8088/result/1234-5678-90ab-cdef" \
     -H "Authorization: your_token_here"
```

### 📘 TypeScript Interfaces

#### Request Types
```typescript
// POST /transcribe 요청 파라미터
interface TranscribeRequest {
  file: File;  // multipart/form-data
  speaker_count?: number;  // default: 2
  language?: string;      // default: null (자동감지)
  temperature?: number;   // default: 0.0
  no_speech_threshold?: number;  // default: 0.6
  initial_prompt?: string;  // default: "다음은 한국어 대화입니다."
}

// Headers
interface RequestHeaders {
  Authorization: string;  // JWT 토큰 또는 테스트 토큰
}
```

#### Response Types
```typescript
// POST /transcribe 응답
interface TranscribeResponse {
  task_id: string;
}

// GET /result/{task_id} 응답
type ResultResponse = 
  | PendingResponse
  | ProcessingResponse
  | CompletedResponse
  | FailedResponse;

// 대기 중
interface PendingResponse {
  status: "pending";
}

// 처리 중
interface ProcessingResponse {
  status: "processing";
  info: "initializing" | "transcribing" | "diarizing" | "combining";
}

// 처리 완료
interface CompletedResponse {
  status: "completed";
  results: Array<{
    speaker: number;
    start: number;
    end: number;
    text: string;
  }>;
}

// 에러 발생
interface FailedResponse {
  status: "failed";
  error: string;
}
```

#### 사용 예시
```typescript
// API 호출 예시
async function transcribeAudio(file: File, options?: Partial<TranscribeRequest>) {
  const formData = new FormData();
  formData.append("file", file);
  
  if (options?.speaker_count) {
    formData.append("speaker_count", options.speaker_count.toString());
  }
  // ... 다른 옵션들 추가

  const response = await fetch("/transcribe", {
    method: "POST",
    headers: {
      Authorization: "Bearer your_token_here"
    },
    body: formData
  });

  const result: TranscribeResponse = await response.json();
  return result;
}

// 결과 조회 예시
async function getResult(taskId: string) {
  const response = await fetch(`/result/${taskId}`, {
    headers: {
      Authorization: "Bearer your_token_here"
    }
  });

  const result: ResultResponse = await response.json();
  
  switch (result.status) {
    case "completed":
      return result.results;  // 처리 완료
    case "processing":
      console.log(`Processing: ${result.info}`);  // 처리 중
      break;
    case "failed":
      throw new Error(result.error);  // 에러 발생
  }
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
