@echo off
chcp 65001 >nul
cd /d "%~dp0web"
start "" http://localhost:8000/
echo TOEIC Speaking 연습 서버 실행 중... 이 창을 닫으면 종료됩니다.
python -m http.server 8000
