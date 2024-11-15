#!/bin/bash

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 도메인 입력 받기
echo -e "${YELLOW}도메인을 입력해주세요 (예: api.yourdomain.com):${NC}"
read domain

if [ -z "$domain" ]; then
    echo -e "${RED}도메인이 입력되지 않았습니다.${NC}"
    exit 1
fi

echo -e "${GREEN}$domain 으로 Caddy를 설정합니다...${NC}"

# Caddy 설치
echo -e "\n${YELLOW}Caddy 설치 중...${NC}"
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install -y caddy

# Caddy 설정 파일 생성
echo -e "\n${YELLOW}Caddy 설정 파일 생성 중...${NC}"
sudo tee /etc/caddy/Caddyfile > /dev/null << EOL
$domain {
    reverse_proxy localhost:8088
    
    request_body {
        max_size 1GB
    }
}
EOL

# Caddy 서비스 재시작
echo -e "\n${YELLOW}Caddy 서비스 재시작 중...${NC}"
sudo systemctl restart caddy
sudo systemctl enable caddy

# 상태 확인
echo -e "\n${YELLOW}Caddy 상태 확인 중...${NC}"
sudo systemctl status caddy

echo -e "\n${GREEN}Caddy 설정이 완료되었습니다!${NC}"
echo -e "${YELLOW}다음 단계:${NC}"
echo "1. DNS 설정에서 $domain을 이 서버의 IP로 연결해주세요"
echo "2. 'sudo systemctl status caddy' 명령으로 서비스 상태를 확인할 수 있습니다"
echo "3. 'sudo journalctl -u caddy -f' 명령으로 로그를 확인할 수 있습니다" 