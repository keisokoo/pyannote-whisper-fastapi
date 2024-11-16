from celery import Celery
import whisper
from pyannote.audio import Pipeline
import torch
from pyannote_whisper.utils import diarize_text
import os
from dotenv import load_dotenv
import subprocess
import tempfile

# Celery 설정
celery_app = Celery('tasks')
celery_app.conf.update(
    broker_url='redis://localhost:6379/0',
    result_backend='redis://localhost:6379/0',
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    enable_utc=True,
)

# 환경변수 로드
load_dotenv()
auth_token = os.getenv('HUGGING_FACE_TOKEN')

# 디바이스 선택
def get_device():
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"

device = get_device()
print(f"Using device: {device}")

# Whisper 모델 초기화
whisper_model = whisper.load_model("large-v3-turbo")
if device != "cpu":
    whisper_model.to(device)

# Pipeline 초기화
pipeline = Pipeline.from_pretrained(
    "pyannote/speaker-diarization-3.1",
    use_auth_token=auth_token
)
if device != "cpu":
    pipeline.to(torch.device(device))

def try_diarization(file_path: str, speaker_count: int):
    try:
        return pipeline(
            file_path,
            min_speakers=speaker_count,
            max_speakers=speaker_count
        )
    except Exception as e:
        print(f"Original format diarization failed: {str(e)}")
        print("Trying with WAV conversion...")
        
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

@celery_app.task(name='tasks.process_audio')
def process_audio(file_path: str, speaker_count: int, language: str = None,
                 temperature: float = 0.0, no_speech_threshold: float = 0.6,
                 initial_prompt: str = "다음은 한국어 대화입니다."):
    try:
        # 음성 인식
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

        # 화자 분리
        diarization_result = try_diarization(file_path, speaker_count)

        # 결과 통합
        final_result = diarize_text(asr_result, diarization_result)

        # 임시 파일 삭제
        os.unlink(file_path)

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

        return {"results": results}

    except Exception as e:
        # 에러 발생시 임시 파일 삭제 시도
        try:
            os.unlink(file_path)
        except:
            pass
        raise e 