#!/bin/bash

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Pyannote-Whisper FastAPI Server 설치를 시작합니다...${NC}"

# 시스템 패키지 설치
echo -e "\n${YELLOW}시스템 패키지 설치 중...${NC}"
sudo apt update
sudo apt install -y ffmpeg libsndfile1-dev libmagic1 sox libsox-fmt-all

# Conda 환경 확인 및 생성
if ! command -v conda &> /dev/null; then
    echo -e "${RED}Conda가 설치되어 있지 않습니다.${NC}"
    exit 1
fi

# Conda 환경 생성
echo -e "\n${YELLOW}Conda 환경 생성 중...${NC}"
conda create -n pyannote python=3.11 -y
eval "$(conda shell.bash hook)"
conda activate pyannote

# Python 패키지 설치
echo -e "\n${YELLOW}Python 패키지 설치 중...${NC}"
pip install pyannote.audio openai-whisper git+https://github.com/keisokoo/pyannote-whisper \
    python-dotenv fastapi python-multipart uvicorn PyJWT python-magic

# numpy 다운그레이드
echo -e "\n${YELLOW}numpy 다운그레이드 중...${NC}"
pip uninstall numpy -y
pip install 'numpy<2.0'

# 환경변수 파일 생성
echo -e "\n${YELLOW}환경변수 파일 생성 중...${NC}"
if [ ! -f .env ]; then
    echo "HUGGING_FACE_TOKEN=your_token_here" > .env
    echo "JWT_SECRET=your_secret_here" >> .env
    echo "TEST_TOKEN=your_test_token_here" >> .env
    echo -e "${GREEN}.env 파일이 생성되었습니다. 토큰 값을 설정해주세요.${NC}"
else
    echo -e "${YELLOW}.env 파일이 이미 존재합니다.${NC}"
fi

# 서비스 파일 생성
echo -e "\n${YELLOW}시스템 서비스 파일 생성 중...${NC}"
sudo tee /etc/systemd/system/fastapi.service > /dev/null << EOL
[Unit]
Description=FastAPI Whisper Service
After=network.target

[Service]
User=$USER
WorkingDirectory=$PWD
ExecStart=/opt/conda/envs/pyannote/bin/python api.py
Restart=always

[Install]
WantedBy=multi-user.target
EOL

# 서비스 활성화
echo -e "\n${YELLOW}서비스 활성화 중...${NC}"
sudo systemctl daemon-reload
sudo systemctl enable fastapi

echo -e "\n${GREEN}설치가 완료되었습니다!${NC}"
echo -e "${YELLOW}다음 단계:${NC}"
echo "1. .env 파일에 토큰 값을 설정해주세요"
echo "2. 'sudo systemctl start fastapi' 명령으로 서비스를 시작할 수 있습니다"
echo "3. 'sudo systemctl status fastapi' 명령으로 서비스 상태를 확인할 수 있습니다" 