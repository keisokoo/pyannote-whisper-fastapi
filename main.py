from typing import Dict, Any, Tuple, List
import whisper
from pyannote.audio import Pipeline
from pyannote_whisper.utils import diarize_text
from pyannote.core import Segment
from dotenv import load_dotenv
import os
import json
import torch

def load_whisper_model(model_name: str = "large-v3-turbo") -> whisper.Whisper:
    """Whisper 모델을 로드합니다."""
    # MPS 사용 가능 여부 확인
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    print(f"Using device: {device}")
    
    model = whisper.load_model(model_name)
    if device == "mps":
        model.to(device)
    return model

def get_pipeline(auth_token: str) -> Pipeline:
    """화자 분리 파이프라인을 초기화합니다."""
    # MPS 사용 가능 여부 확인
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    
    pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.1",
        use_auth_token=auth_token
    )
    if device == "mps":
        pipeline.to(torch.device(device))
    return pipeline

def transcribe_audio(
    model: whisper.Whisper,
    audio_path: str,
    options: Dict[str, Any] = None
) -> Dict[str, Any]:
    """오디오 파일을 텍스트로 변환합니다."""
    default_options = {
        "language": "ko",
        "temperature": 0,
        "no_speech_threshold": 0.6,
        "initial_prompt": "다음은 한국어 대화입니다.",
        "word_timestamps": True,
        "condition_on_previous_text": True,
        "fp16": False,
        "device": "mps" if torch.backends.mps.is_available() else "cpu"
    }
    
    if options:
        default_options.update(options)
    
    return model.transcribe(audio_path, **default_options)

def perform_diarization(
    pipeline: Pipeline,
    audio_path: str,
    speaker_count: Tuple[int, int] = (3, 3)
) -> Any:  # pyannote.core.Annotation 타입이지만 라이브러리에서 명시적으로 제공하지 않음
    """화자 분리를 수행합니다."""
    return pipeline(
        audio_path,
        min_speakers=speaker_count[0],
        max_speakers=speaker_count[1]
    )

def format_results(diarization_results) -> Dict[str, List[Dict[str, Any]]]:
    """
    화자 분리 결과를 JSON 형식으로 변환합니다.
    
    Returns:
        Dict[str, List[Dict[str, Any]]]: {
            "results": [
                {
                    "speaker": int,      # 화자 번호 (0부터 시작)
                    "start": float,      # 시작 시간 (초)
                    "end": float,        # 종료 시간 (초)
                    "text": str          # 발화 내용
                },
                ...
            ]
        }
    """
    results = []
    for segment, speaker, text in diarization_results:
        # speaker가 None이거나 빈 문자열인 경우 -1로 처리
        try:
            speaker_num = int(speaker.split('_')[-1]) if speaker else -1
        except (AttributeError, ValueError):
            speaker_num = -1
        
        # 텍스트가 있는 경우만 결과에 추가
        if text and text.strip():
            result = {
                "speaker": speaker_num,
                "start": round(segment.start, 2),
                "end": round(segment.end, 2),
                "text": text.strip()
            }
            results.append(result)
    
    return {"results": results}

def main(audio_path: str = "audio.wav") -> None:
    """메인 실행 함수"""
    # 환경 설정
    load_dotenv()
    auth_token = os.getenv('HUGGING_FACE_TOKEN')
    if not auth_token:
        raise ValueError("HUGGING_FACE_TOKEN이 설정되지 않았습니다.")

    # 모델과 파이프라인 초기화
    model = load_whisper_model()
    pipeline = get_pipeline(auth_token)

    # 음성 인식 수행
    asr_result = transcribe_audio(model, audio_path)

    # 화자 분리 수행
    diarization_result = perform_diarization(pipeline, audio_path)

    # 결과 통합
    final_result = diarize_text(asr_result, diarization_result)
    
    # JSON 형식으로 변환
    json_result = format_results(final_result)
    
    # JSON 문자열로 출력
    print(json.dumps(json_result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()