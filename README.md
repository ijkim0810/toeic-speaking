# TOEIC Speaking 섀도잉 연습 도구

원어민 음성(일레븐랩스)으로 문장을 듣고 따라 말하는 섀도잉 연습 웹앱(PWA).
한글 뜻 1회 → 영어 N회(노래방식 단어 하이라이트) → 간격 → 다음 문장.

## 폴더
- `topics/<Part>/<Task>.txt` — 연습 문장. 한 줄 = `영어 | 한글`. 폴더=Part, 파일=Task.
- `generate.py` — 문장을 일레븐랩스로 mp3 + 단어 타임스탬프로 변환 → `web/`. 이미 만든 문장은 재호출 안 함.
- `web/` — 실제 앱(정적 PWA). GitHub Pages로 배포됨.

## 문장 추가/수정
1. `topics/` 아래 `.txt` 편집 (새 Part는 폴더, 새 Task는 파일 추가).
2. `python generate.py` 실행 (바뀐 문장만 새로 생성).
3. `git add -A && git commit -m "..." && git push` → 폰 앱이 다음 실행 시 자동 업데이트.

## 실행 (로컬)
`연습시작.bat` 더블클릭, 또는 `python -m http.server 8000 --directory web` 후 http://localhost:8000

## 설정
- API 키는 `.env` 의 `ELEVENLABS_API_KEY` (git 추적 제외).
- 음성: 영어 Brian, 한국어 Yona (`generate.py` 상단 상수).
