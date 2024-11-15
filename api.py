from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Header
from pydantic import BaseModel
from typing import Dict, Any, Optional
import whisper
from pyannote.audio import Pipeline
from pyannote_whisper.utils import diarize_text
from dotenv import load_dotenv
import os
import tempfile
import json
import torch
import jwt
from datetime import datetime, timedelta
import magic

app = FastAPI()

# 요청 모델
class TranscriptionRequest(BaseModel):
    speaker_count: int = 2  # 기본값 2
    language: str = "ko"    # 기본값 한국어

# 전역 변수로 모델과 파이프라인 초기화
load_dotenv()
auth_token = os.getenv('HUGGING_FACE_TOKEN')
if not auth_token:
    raise ValueError("HUGGING_FACE_TOKEN이 설정되지 않았습니다.")

# 디바이스 선택 로직 수정
def get_device():
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"

# 디바이스 설정
device = get_device()
print(f"Using device: {device}")

# Whisper 모델 초기화 및 디바이스 설정
whisper_model = whisper.load_model("large-v3-turbo")
if device != "cpu":
    whisper_model.to(device)

# Pipeline 초기화 및 디바이스 설정
pipeline = Pipeline.from_pretrained(
    "pyannote/speaker-diarization-3.1",
    use_auth_token=auth_token
)
if device != "cpu":
    pipeline.to(torch.device(device))

def format_results(diarization_results) -> Dict[str, Any]:
    """화자 분리 결과를 JSON 형식으로 변환합니다."""
    results = []
    for segment, speaker, text in diarization_results:
        try:
            speaker_num = int(speaker.split('_')[-1]) if speaker else -1
        except (AttributeError, ValueError):
            speaker_num = -1
        
        if text and text.strip():
            result = {
                "speaker": speaker_num,
                "start": round(segment.start, 2),
                "end": round(segment.end, 2),
                "text": text.strip()
            }
            results.append(result)
    
    return {"results": results}

# JWT 설정
JWT_SECRET = os.getenv("JWT_SECRET", "your_jwt_secret")
TEST_TOKEN = os.getenv("TEST_TOKEN", "test1234")
JWT_ALGORITHM = "HS256"

def verify_jwt_token(token: str) -> bool:
    """JWT 토큰을 검증합니다."""
    try:
        # Bearer 토큰 처리
        if token.startswith("Bearer "):
            token = token.split(" ")[1]
        elif not token:
            return False
            
        # PyJWT의 decode 메서드 사용
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return True
    except Exception as e:  # PyJWT의 모든 예외 처리
        return False

ALLOWED_MIME_TYPES = {
    'audio/wav', 'audio/x-wav',
    'audio/mpeg', 'audio/mp3',
    'audio/m4a', 'audio/mp4', 'audio/x-m4a',
    'audio/ogg',
    'audio/flac',
    'audio/aiff', 'audio/x-aiff',     # AIFF
    'audio/opus',                      # OPUS (일반적으로 audio/ogg로도 인식됨)
    'video/mp4',
    'video/webm',           # WebM 비디오
    'audio/webm',           # WebM 오디오
    'video/x-msvideo',      # AVI
    'video/quicktime',      # MOV
    'video/x-matroska'      # MKV
}

def is_allowed_file(file_content: bytes) -> bool:
    """파일의 실제 MIME 타입을 확인하여 허용된 오디오 파일인지 검증"""
    mime = magic.Magic(mime=True)
    file_mime_type = mime.from_buffer(file_content)
    return file_mime_type in ALLOWED_MIME_TYPES

@app.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    speaker_count: int = Form(default=2),
    language: str = Form(default="ko"),
    temperature: float = Form(default=0.0),
    no_speech_threshold: float = Form(default=0.6),
    initial_prompt: str = Form(default="다음은 한국어 대화입니다."),
    authorization: Optional[str] = Header(None)
):
    """
    오디오 파일을 받아서 화자 분리된 텍스트를 반환합니다.
    
    Args:
        file: 오디오 파일 (wav 형식 권장)
        speaker_count: 화자 수 (기본값: 2)
        language: 언어 코드 (기본값: "ko")
        temperature: 생성 다양성 (기본값: 0.0)
        no_speech_threshold: 무음 감지 임계값 (기본값: 0.6)
        initial_prompt: 초기 프롬프트 (기본값: "다음은 한국어 대화입니다.")
        authorization: JWT 토큰 (기본값: None)
    """
    # 토큰 검증
    if not authorization:
        raise HTTPException(status_code=401, detail="인증 토큰이 필요합니다.")
    
    # 테스트 토큰 확인 또는 JWT 검증
    if authorization != TEST_TOKEN and not verify_jwt_token(authorization):
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다.")

    if not file:
        raise HTTPException(status_code=400, detail="파일이 없습니다.")
    
    # 파일 내용 읽기
    content = await file.read()
    print(f"Request received. file name: {file.filename}, file size: {len(content)}")

    # 파일 형식 검증
    if not is_allowed_file(content):
        raise HTTPException(
            status_code=400, 
            detail=f"지원하지 않는 파일 형식입니다. 지원되는 형식: WAV, MP3, M4A, FLAC, OGG"
        )
    
    try:
        # 임시 파일로 저장
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
            temp_file.write(content)  # 이미 읽은 content 사용
            temp_path = temp_file.name

        # 음성 인식 수행
        asr_result = whisper_model.transcribe(
            temp_path,
            language=language,
            temperature=temperature,
            no_speech_threshold=no_speech_threshold,
            initial_prompt=initial_prompt,
            word_timestamps=True,
            condition_on_previous_text=True,
            fp16=False
        )

        # 화자 분리 수행
        diarization_result = pipeline(
            temp_path,
            min_speakers=speaker_count,
            max_speakers=speaker_count
        )

        # 결과 통합
        final_result = diarize_text(asr_result, diarization_result)
        
        # 임시 파일 삭제
        os.unlink(temp_path)
        
        # 결과 반환
        return format_results(final_result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8088))
    uvicorn.run("api:app", host="0.0.0.0", port=port)