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
export HUGGING_FACE_TOKEN=<your_hugging_face_token>
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