from celery import Celery
import whisper
from pyannote.audio import Pipeline
import torch
from pyannote_whisper.utils import diarize_text
import os
from dotenv import load_dotenv
import subprocess
import tempfile
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Celery 설정
celery_app = Celery('tasks')
celery_app.conf.update(
    broker_url='redis://localhost:6379/0',
    result_backend='redis://localhost:6379/0',
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,
    worker_prefetch_multiplier=1,
    task_ignore_result=False,
    result_expires=None,
)

# 환경변수 로드
load_dotenv()
auth_token = os.getenv('HUGGING_FACE_TOKEN')

def get_device():
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"

def try_diarization(pipeline, file_path: str, speaker_count: int):
    try:
        return pipeline(
            file_path,
            min_speakers=speaker_count,
            max_speakers=speaker_count
        )
    except Exception as e:
        logger.error(f"Original format diarization failed: {str(e)}")
        logger.info("Trying with WAV conversion...")
        
        wav_path = file_path + '.wav'
        try:
            subprocess.run([
                'ffmpeg', '-i', file_path,
                '-acodec', 'pcm_s16le',
                '-ar', '16000',
                '-ac', '1',
                wav_path
            ], check=True)
            
            result = pipeline(
                wav_path,
                min_speakers=speaker_count,
                max_speakers=speaker_count
            )
            
            os.unlink(wav_path)
            return result
            
        except Exception as conv_e:
            try:
                os.unlink(wav_path)
            except:
                pass
            raise conv_e

@celery_app.task(name='tasks.process_audio', bind=True)
def process_audio(self, file_path: str, speaker_count: int, language: str = None,
                 temperature: float = 0.0, no_speech_threshold: float = 0.6,
                 initial_prompt: str = "다음은 한국어 대화입니다."):
    try:
        # 작업 시작 상태 업데이트
        self.update_state(state='PROGRESS', meta={'status': 'initializing'})
        logger.info(f"Starting audio processing task: {self.request.id}")
        
        # 모델 초기화
        device = get_device()
        logger.info(f"Using device: {device}")
        
        # Whisper 모델 초기화
        logger.info("Initializing Whisper model...")
        whisper_model = whisper.load_model("large-v3-turbo")
        if device != "cpu":
            whisper_model.to(device)
        
        # Pipeline 초기화
        logger.info("Initializing Pipeline...")
        pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=auth_token
        )
        if device != "cpu":
            pipeline.to(torch.device(device))
        
        # 파일 존재 확인
        if not os.path.exists(file_path):
            self.update_state(state='FAILURE', meta={'error': 'File not found'})
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Whisper 처리 시작
        self.update_state(state='PROGRESS', meta={'status': 'transcribing'})
        logger.info(f"Processing file: {file_path}")
        
        # 음성 인식
        logger.info("Starting whisper transcription...")
        asr_result = whisper_model.transcribe(
            file_path,
            language=language,
            temperature=temperature,
            no_speech_threshold=no_speech_threshold,
            initial_prompt=initial_prompt,
            word_timestamps=True,
            condition_on_previous_text=True,
            fp16=False
        )
        logger.info("Whisper transcription completed")

        # 화자 분리
        self.update_state(state='PROGRESS', meta={'status': 'diarizing'})
        logger.info("Starting speaker diarization...")
        diarization_result = try_diarization(pipeline, file_path, speaker_count)
        logger.info("Speaker diarization completed")

        # 결과 통합
        self.update_state(state='PROGRESS', meta={'status': 'combining'})
        logger.info("Combining results...")
        final_result = diarize_text(asr_result, diarization_result)
        logger.info("Results combined")

        # 임시 파일 삭제
        os.unlink(file_path)
        logger.info("Temporary file deleted")

        # 결과 포맷팅
        results = []
        for segment, speaker, text in final_result:
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

        logger.info("Task completed successfully")
        return {"results": results, "status": "completed"}

    except Exception as e:
        self.update_state(state='FAILURE', meta={'error': str(e)})
        logger.error(f"Error in process_audio: {str(e)}", exc_info=True)
        try:
            os.unlink(file_path)
        except:
            pass
        raise e 