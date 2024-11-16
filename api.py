from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Header
from pydantic import BaseModel
from typing import Dict, Any, Optional
import whisper
from pyannote.audio import Pipeline
from pyannote_whisper.utils import diarize_text
from dotenv import load_dotenv
import os
import tempfile
import torch
import jwt
from datetime import datetime, timedelta
import magic
import subprocess
import uuid
from tasks import process_audio

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

# MIME 타입에 따른 확장자 매핑
MIME_TO_EXT = {
    'audio/wav': '.wav',
    'audio/x-wav': '.wav',
    'audio/mpeg': '.mp3',
    'audio/mp3': '.mp3',
    'audio/m4a': '.m4a',
    'audio/mp4': '.m4a',
    'audio/x-m4a': '.m4a',
    'audio/ogg': '.ogg',
    'audio/flac': '.flac',
    'audio/aiff': '.aiff',
    'audio/x-aiff': '.aiff',
    'audio/opus': '.opus',
    'video/mp4': '.m4a',  # 오디오 전용 mp4는 m4a로 처리
    'video/webm': '.webm',
    'audio/webm': '.webm',
    'video/x-msvideo': '.avi',
    'video/quicktime': '.mov',
    'video/x-matroska': '.mkv'
}

@app.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    speaker_count: int = Form(default=2),
    language: str = Form(default=None),
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
    
    try:
        # 파일 내용 읽기
        content = await file.read()
        
        # 파일 형식 검증
        mime = magic.Magic(mime=True)
        file_mime_type = mime.from_buffer(content)
        
        if not is_allowed_file(content):
            raise HTTPException(
                status_code=400,
                detail=f"지원하지 않는 파일 형식입니다. 감지된 MIME type: {file_mime_type}"
            )

        # 임시 파일 저장
        ext = MIME_TO_EXT.get(file_mime_type, os.path.splitext(file.filename)[1])
        temp_path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}{ext}")
        with open(temp_path, 'wb') as f:
            f.write(content)

        # Celery 태스크 실행
        task = process_audio.delay(
            temp_path,
            speaker_count,
            language,
            temperature,
            no_speech_threshold,
            initial_prompt
        )

        # 태스크 ID 반환
        return {"task_id": task.id}

    except Exception as e:
        # 에러 발생시 임시 파일 삭제 시도
        try:
            os.unlink(temp_path)
        except:
            pass
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/result/{task_id}")
async def get_result(task_id: str, authorization: Optional[str] = Header(None)):
    # 토큰 검증
    if not authorization:
        raise HTTPException(status_code=401, detail="인증 토큰이 필요합니다.")
    
    if authorization != TEST_TOKEN and not verify_jwt_token(authorization):
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다.")

    task = process_audio.AsyncResult(task_id)
    
    if task.state == 'PENDING':
        return {"status": "pending"}
    elif task.state == 'PROGRESS':
        return {"status": "processing", "info": task.info.get('status', '')}
    elif task.state == 'SUCCESS':
        result = task.result
        # 결과를 반환하기 전에 작업 삭제
        task.forget()
        return result
    elif task.state == 'FAILURE':
        error = str(task.result)
        # 실패한 작업도 삭제
        task.forget()
        return {"status": "failed", "error": error}
    else:
        return {"status": task.state}
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8088))
    uvicorn.run("api:app", host="0.0.0.0", port=port)
