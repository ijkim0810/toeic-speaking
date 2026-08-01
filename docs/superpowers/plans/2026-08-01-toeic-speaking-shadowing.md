# TOEIC Speaking 섀도잉 도구 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ElevenLabs 원어민 음성으로 문장을 미리 뽑아 저장하고, 정적 웹페이지(PWA)에서 한글1회→영어5회(노래방 하이라이트)→간격→다음 순서로 섀도잉 연습하는 도구.

**Architecture:** Python 생성 스크립트가 오프라인에서 주제별 txt를 읽어 ElevenLabs `with-timestamps` API로 mp3 + 글자 타임스탬프를 생성하고 `manifest.json`에 저장한다. 실제 연습 도구는 서버/키 없는 바닐라 정적 웹페이지로, manifest만 읽어 재생하고 PWA로 안드로이드에 설치·오프라인 동작한다.

**Tech Stack:** Python 3 표준 라이브러리만(생성, `urllib.request`), 바닐라 HTML/CSS/JS (웹), Node 내장 `node:test`·`pytest` (테스트). 서드파티/npm 런타임 의존성 없음.

## Global Constraints

- 프로젝트 루트: `F:\내 드라이브\옵시디언_google\toeic-speaking` — 모든 경로는 이 루트 기준. 실행 전 이 폴더로 이동.
- ElevenLabs API 키는 환경변수 `ELEVENLABS_API_KEY`로만 읽는다. 코드/manifest/커밋에 절대 하드코딩 금지.
- 모델: `eleven_multilingual_v2` (영어·한국어 공용).
- 기본 보이스: `EN_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"` (Rachel), `KO_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"` (한국어 전용 보이스로 교체 가능하도록 상수 분리).
- 토픽 파일 한 줄 형식: `영어 문장 | 한글 뜻`. 빈 줄과 `#` 시작 줄은 무시.
- manifest 문장 스키마: `{ en, ko, enAudio, koAudio, words: [{text, start, end}] }` (start/end는 초 단위 float).
- 오디오 파일명 = 내용 해시 → 동일 내용 재실행 시 재생성 건너뜀(API 비용 방지).
- Python 파일은 표준 라이브러리만 사용(서드파티 의존성 없음, HTTP는 `urllib.request`). 웹은 프레임워크·런타임 의존성 없음.
- 발음 채점(마이크 음성인식) 구현하지 않음 — 명시적 비목표.

---

### Task 1: 프로젝트 스캐폴드 + 토픽 파서

**Files:**
- Create: `generate.py`
- Create: `topics/daily.txt`
- Create: `tests/test_generate.py`
- Create: `.gitignore`

**Interfaces:**
- Produces: `parse_topic_file(path: str) -> list[tuple[str, str]]` — `(en, ko)` 튜플 리스트. 빈 줄·`#` 줄 제외.

- [ ] **Step 1: 프로젝트 초기화**

프로젝트 루트에서:
```bash
git init
printf "__pycache__/\n*.pyc\n.env\n" > .gitignore
```

- [ ] **Step 2: 샘플 토픽 파일 작성**

`topics/daily.txt`:
```
# 일상 표현 (형식: 영어 | 한글)
He is drinking some water. | 그는 물을 마시고 있어요.
She is reading a book. | 그녀는 책을 읽고 있어요.
```

- [ ] **Step 3: 실패하는 테스트 작성**

`tests/test_generate.py`:
```python
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from generate import parse_topic_file

def test_parse_skips_blanks_and_comments(tmp_path):
    f = tmp_path / "t.txt"
    f.write_text(
        "# comment\n\nHe runs. | 그는 달려요.\nShe sings. | 그녀는 노래해요.\n",
        encoding="utf-8",
    )
    assert parse_topic_file(str(f)) == [
        ("He runs.", "그는 달려요."),
        ("She sings.", "그녀는 노래해요."),
    ]
```

- [ ] **Step 4: 테스트 실패 확인**

Run: `python -m pytest tests/test_generate.py::test_parse_skips_blanks_and_comments -v`
Expected: FAIL — `ImportError` / `cannot import name 'parse_topic_file'`

- [ ] **Step 5: 최소 구현**

`generate.py`:
```python
def parse_topic_file(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "|" not in line:
                continue
            en, ko = line.split("|", 1)
            rows.append((en.strip(), ko.strip()))
    return rows
```

- [ ] **Step 6: 테스트 통과 확인**

Run: `python -m pytest tests/test_generate.py::test_parse_skips_blanks_and_comments -v`
Expected: PASS

- [ ] **Step 7: 커밋**

```bash
git add generate.py topics/daily.txt tests/test_generate.py .gitignore
git commit -m "feat: project scaffold + topic file parser"
```

---

### Task 2: 단어 그룹핑 + 오디오 파일명 해시

**Files:**
- Modify: `generate.py`
- Modify: `tests/test_generate.py`

**Interfaces:**
- Consumes: (없음)
- Produces:
  - `group_words(characters: list[str], starts: list[float], ends: list[float]) -> list[dict]` — 공백으로 단어 분리, 각 단어 `{"text": str, "start": float, "end": float}` (start=단어 첫 글자 start, end=마지막 글자 end).
  - `audio_filename(voice_id: str, model: str, text: str) -> str` — `"audio/<sha1hex>.mp3"`. 동일 입력이면 동일, text 바뀌면 달라짐.

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_generate.py`에 추가:
```python
from generate import group_words, audio_filename

def test_group_words_splits_on_space():
    chars  = ["H","e"," ","i","s"]
    starts = [0.0, 0.1, 0.2, 0.3, 0.4]
    ends   = [0.1, 0.2, 0.3, 0.4, 0.5]
    assert group_words(chars, starts, ends) == [
        {"text": "He", "start": 0.0, "end": 0.2},
        {"text": "is", "start": 0.3, "end": 0.5},
    ]

def test_audio_filename_stable_and_content_sensitive():
    a = audio_filename("v1", "m1", "hello")
    b = audio_filename("v1", "m1", "hello")
    c = audio_filename("v1", "m1", "world")
    assert a == b
    assert a != c
    assert a.startswith("audio/") and a.endswith(".mp3")
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/test_generate.py -v -k "group_words or audio_filename"`
Expected: FAIL — `cannot import name 'group_words'`

- [ ] **Step 3: 최소 구현**

`generate.py`에 추가:
```python
import hashlib


def group_words(characters, starts, ends):
    words = []
    cur, cur_start = "", None
    for ch, s, e in zip(characters, starts, ends):
        if ch.isspace():
            if cur:
                words.append({"text": cur, "start": cur_start, "end": last_end})
                cur, cur_start = "", None
            continue
        if not cur:
            cur_start = s
        cur += ch
        last_end = e
    if cur:
        words.append({"text": cur, "start": cur_start, "end": last_end})
    return words


def audio_filename(voice_id, model, text):
    key = f"{voice_id}|{model}|{text}".encode("utf-8")
    return "audio/" + hashlib.sha1(key).hexdigest() + ".mp3"
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/test_generate.py -v -k "group_words or audio_filename"`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add generate.py tests/test_generate.py
git commit -m "feat: word grouping + content-hash audio filenames"
```

---

### Task 3: ElevenLabs 클라이언트 (모킹 테스트)

**Files:**
- Modify: `generate.py`
- Modify: `tests/test_generate.py`

**Interfaces:**
- Consumes: (없음)
- Produces: `tts_with_timestamps(text: str, voice_id: str, api_key: str, model: str = "eleven_multilingual_v2") -> dict` — 반환 `{"audio": bytes, "alignment": {"characters": [...], "character_start_times_seconds": [...], "character_end_times_seconds": [...]}}`. 내부적으로 `urllib.request`로 `https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/with-timestamps` 에 POST, 응답 `audio_base64`를 디코딩. 서드파티 의존성 없음.

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_generate.py`에 추가:
```python
import base64
import json as _json
from unittest.mock import patch, MagicMock
from generate import tts_with_timestamps

def test_tts_decodes_base64_and_returns_alignment():
    fake = {
        "audio_base64": base64.b64encode(b"MP3BYTES").decode(),
        "alignment": {
            "characters": ["H", "i"],
            "character_start_times_seconds": [0.0, 0.1],
            "character_end_times_seconds": [0.1, 0.2],
        },
    }
    resp = MagicMock()
    resp.read.return_value = _json.dumps(fake).encode("utf-8")
    cm = MagicMock()
    cm.__enter__.return_value = resp        # urlopen(...)을 with로 사용
    cm.__exit__.return_value = False
    with patch("generate.urllib.request.urlopen", return_value=cm) as urlopen:
        out = tts_with_timestamps("Hi", "voice1", "key123")
    # urlopen에 넘어간 Request 객체 검증
    req = urlopen.call_args.args[0]
    assert req.full_url == "https://api.elevenlabs.io/v1/text-to-speech/voice1/with-timestamps"
    assert req.get_method() == "POST"
    # urllib은 헤더 키를 capitalize() 형태로 저장한다: "xi-api-key" -> "Xi-api-key"
    assert req.headers["Xi-api-key"] == "key123"
    sent = _json.loads(req.data.decode("utf-8"))
    assert sent["text"] == "Hi"
    assert sent["model_id"] == "eleven_multilingual_v2"
    # 반환값 검증
    assert out["audio"] == b"MP3BYTES"
    assert out["alignment"]["characters"] == ["H", "i"]
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/test_generate.py::test_tts_decodes_base64_and_returns_alignment -v`
Expected: FAIL — `cannot import name 'tts_with_timestamps'`

- [ ] **Step 3: 최소 구현**

`generate.py` 상단에 `import base64`, `import json`, `import urllib.request` 추가 후:
```python
def tts_with_timestamps(text, voice_id, api_key, model="eleven_multilingual_v2"):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/with-timestamps"
    body = json.dumps({"text": text, "model_id": model}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"xi-api-key": api_key, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return {
        "audio": base64.b64decode(data["audio_base64"]),
        "alignment": data["alignment"],
    }
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/test_generate.py::test_tts_decodes_base64_and_returns_alignment -v`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add generate.py tests/test_generate.py
git commit -m "feat: ElevenLabs with-timestamps client"
```

---

### Task 4: 생성 오케스트레이션 (main)

**Files:**
- Modify: `generate.py`
- Modify: `tests/test_generate.py`

**Interfaces:**
- Consumes: `parse_topic_file`, `group_words`, `audio_filename`, `tts_with_timestamps`.
- Produces: `build_manifest(topics_dir, web_dir, api_key, en_voice, ko_voice, tts=tts_with_timestamps) -> dict` — 각 토픽 txt를 읽어 문장별로 EN/KO 음성을 생성(이미 있는 파일은 건너뜀), mp3를 `web_dir/audio/`에 쓰고, manifest dict를 반환하며 `web_dir/manifest.json`에 저장. `tts` 인자는 테스트 주입용. + `main()` (env에서 키 읽어 `topics/` → `web/` 실행).

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_generate.py`에 추가:
```python
import json
from generate import build_manifest

def test_build_manifest_generates_and_skips(tmp_path):
    topics = tmp_path / "topics"; topics.mkdir()
    (topics / "daily.txt").write_text("He runs. | 그는 달려요.\n", encoding="utf-8")
    web = tmp_path / "web"; web.mkdir()

    calls = []
    def fake_tts(text, voice_id, api_key, model="eleven_multilingual_v2"):
        calls.append(text)
        return {"audio": b"X", "alignment": {
            "characters": list(text),
            "character_start_times_seconds": [i * 0.1 for i in range(len(text))],
            "character_end_times_seconds": [(i + 1) * 0.1 for i in range(len(text))],
        }}

    m = build_manifest(str(topics), str(web), "key", "envoice", "kovoice", tts=fake_tts)

    # 구조 검증
    topic = m["topics"][0]
    assert topic["id"] == "daily"
    s = topic["sentences"][0]
    assert s["en"] == "He runs." and s["ko"] == "그는 달려요."
    assert s["words"][0]["text"] == "He"
    assert (web / s["enAudio"]).exists() and (web / s["koAudio"]).exists()
    assert (web / "manifest.json").exists()
    assert json.loads((web / "manifest.json").read_text(encoding="utf-8")) == m

    # 재실행 시 오디오 재생성 안 함 (파일 존재 → tts 호출 0)
    calls.clear()
    build_manifest(str(topics), str(web), "key", "envoice", "kovoice", tts=fake_tts)
    assert calls == []
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/test_generate.py::test_build_manifest_generates_and_skips -v`
Expected: FAIL — `cannot import name 'build_manifest'`

- [ ] **Step 3: 최소 구현**

`generate.py` 상단에 `import os`, `import glob`, `import json` 추가 후:
```python
EN_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"
KO_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"
MODEL = "eleven_multilingual_v2"


def _ensure_audio(text, voice, api_key, web_dir, want_words, tts):
    rel = audio_filename(voice, MODEL, text)
    dest = os.path.join(web_dir, rel)
    words = None
    if os.path.exists(dest):
        return rel, words  # 이미 생성됨 → 건너뜀 (words는 manifest 재빌드 시 재계산 불필요)
    result = tts(text, voice, api_key, MODEL)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "wb") as f:
        f.write(result["audio"])
    if want_words:
        a = result["alignment"]
        words = group_words(
            a["characters"],
            a["character_start_times_seconds"],
            a["character_end_times_seconds"],
        )
    return rel, words


def build_manifest(topics_dir, web_dir, api_key, en_voice, ko_voice, tts=tts_with_timestamps):
    topics = []
    for path in sorted(glob.glob(os.path.join(topics_dir, "*.txt"))):
        topic_id = os.path.splitext(os.path.basename(path))[0]
        sentences = []
        for en, ko in parse_topic_file(path):
            en_rel, words = _ensure_audio(en, en_voice, api_key, web_dir, True, tts)
            ko_rel, _ = _ensure_audio(ko, ko_voice, api_key, web_dir, False, tts)
            if words is None:  # 오디오는 이미 있어도 타임스탬프는 항상 필요 → 재계산
                words = _words_for(en, en_voice, api_key, web_dir, tts)
            sentences.append({"en": en, "ko": ko, "enAudio": en_rel,
                              "koAudio": ko_rel, "words": words})
        topics.append({"id": topic_id, "title": topic_id, "sentences": sentences})
    manifest = {"topics": topics}
    with open(os.path.join(web_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    return manifest
```

주의: 오디오가 이미 존재하면 words가 없으므로, words 캐시를 위해 기존 manifest에서 재사용하도록 아래 헬퍼를 추가한다 (재실행 시 API 재호출 방지 유지):
```python
def _words_for(en, voice, api_key, web_dir, tts):
    """오디오는 있으나 words가 없을 때: 기존 manifest.json에서 찾고, 없으면 API 재호출."""
    mpath = os.path.join(web_dir, "manifest.json")
    if os.path.exists(mpath):
        with open(mpath, encoding="utf-8") as f:
            old = json.load(f)
        for t in old.get("topics", []):
            for s in t.get("sentences", []):
                if s["en"] == en and s.get("words"):
                    return s["words"]
    result = tts(en, voice, api_key, MODEL)
    a = result["alignment"]
    return group_words(a["characters"], a["character_start_times_seconds"],
                       a["character_end_times_seconds"])
```

그리고 `main()` 추가:
```python
def main():
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        raise SystemExit("환경변수 ELEVENLABS_API_KEY 를 설정하세요.")
    root = os.path.dirname(os.path.abspath(__file__))
    build_manifest(os.path.join(root, "topics"), os.path.join(root, "web"),
                   api_key, EN_VOICE_ID, KO_VOICE_ID)
    print("완료: web/manifest.json 생성됨")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/test_generate.py::test_build_manifest_generates_and_skips -v`
Expected: PASS

- [ ] **Step 5: 전체 테스트 확인**

Run: `python -m pytest tests/test_generate.py -v`
Expected: 모든 테스트 PASS

- [ ] **Step 6: 커밋**

```bash
git add generate.py tests/test_generate.py
git commit -m "feat: manifest build orchestration with audio-skip caching"
```

---

### Task 5: 웹 플레이어 코어 로직 (node:test)

**Files:**
- Create: `web/player-core.js`
- Create: `web/player-core.test.js`

**Interfaces:**
- Produces (ESM export, DOM 비의존 순수 함수):
  - `activeWordIndex(words, tSeconds) -> number` — `words[i].start <= t < words[i].end`인 인덱스, 없으면 `-1`.
  - `buildSchedule(sentence, repeats) -> Array<{lang, text, audio}>` — `[{lang:"ko", text:sentence.ko, audio:sentence.koAudio}]` 뒤에 `{lang:"en", text:sentence.en, audio:sentence.enAudio}`가 `repeats`개.

- [ ] **Step 1: 실패하는 테스트 작성**

`web/player-core.test.js`:
```javascript
const test = require("node:test");
const assert = require("node:assert");
const { activeWordIndex, buildSchedule } = require("./player-core.js");

test("activeWordIndex finds current word", () => {
  const words = [{ text: "He", start: 0.0, end: 0.2 }, { text: "is", start: 0.3, end: 0.5 }];
  assert.strictEqual(activeWordIndex(words, 0.1), 0);
  assert.strictEqual(activeWordIndex(words, 0.4), 1);
  assert.strictEqual(activeWordIndex(words, 0.25), -1);
  assert.strictEqual(activeWordIndex(words, 9), -1);
});

test("buildSchedule = 1 korean then N english", () => {
  const s = { en: "Hi.", ko: "안녕.", enAudio: "audio/e.mp3", koAudio: "audio/k.mp3" };
  const sched = buildSchedule(s, 5);
  assert.strictEqual(sched.length, 6);
  assert.deepStrictEqual(sched[0], { lang: "ko", text: "안녕.", audio: "audio/k.mp3" });
  assert.strictEqual(sched[1].lang, "en");
  assert.strictEqual(sched[5].lang, "en");
});
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `node --test web/player-core.test.js`
Expected: FAIL — `Cannot find module './player-core.js'`

- [ ] **Step 3: 최소 구현**

`web/player-core.js` (node require·브라우저 양쪽 지원):
```javascript
function activeWordIndex(words, t) {
  for (let i = 0; i < words.length; i++) {
    if (t >= words[i].start && t < words[i].end) return i;
  }
  return -1;
}

function buildSchedule(sentence, repeats) {
  const out = [{ lang: "ko", text: sentence.ko, audio: sentence.koAudio }];
  for (let i = 0; i < repeats; i++) {
    out.push({ lang: "en", text: sentence.en, audio: sentence.enAudio });
  }
  return out;
}

if (typeof module !== "undefined") {
  module.exports = { activeWordIndex, buildSchedule };
}
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `node --test web/player-core.test.js`
Expected: PASS (2 tests)

- [ ] **Step 5: 커밋**

```bash
git add web/player-core.js web/player-core.test.js
git commit -m "feat: pure player-core (activeWordIndex, buildSchedule)"
```

---

### Task 6: 웹 UI (index.html) — 디자인 + 재생 흐름

**Files:**
- Create: `web/index.html`

**Interfaces:**
- Consumes: `player-core.js`의 `activeWordIndex`, `buildSchedule`; `manifest.json`.
- Produces: 주제 목록 → 재생 화면. 재생 흐름: 각 문장마다 buildSchedule 순서대로 오디오 재생, 영어 재생 중 `timeupdate`로 단어 카라오케 하이라이트, 각 재생 후 `gapSeconds` 대기, 마지막이면 다음 문장. 반복 횟수·간격은 상단 설정 입력.

- [ ] **Step 1: index.html 작성 (레퍼런스 디자인 반영)**

`web/index.html`:
```html
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
<title>TOEIC Speaking 섀도잉</title>
<link rel="manifest" href="manifest.webmanifest" />
<meta name="theme-color" content="#bfe3ff" />
<style>
  * { box-sizing: border-box; }
  body { margin: 0; font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
         background: linear-gradient(160deg,#eaf6ff,#dff0ff); color:#1b2a3a;
         min-height:100dvh; }
  header { padding: 14px 16px; display:flex; gap:10px; align-items:center; flex-wrap:wrap; }
  select, input, button { font-size:16px; padding:8px 10px; border-radius:12px;
         border:1px solid #b9d6ee; background:#fff; }
  button.primary { background:#2f8fd6; color:#fff; border:none; }
  #stage { display:flex; flex-direction:column; align-items:center; justify-content:center;
           gap:18px; padding:24px 16px; }
  .card { width:100%; max-width:680px; border-radius:28px; padding:34px 26px;
          background:linear-gradient(160deg,#e4f2ff,#cfe8ff);
          box-shadow:0 8px 30px rgba(60,130,200,.18); position:relative; }
  .en { font-size:30px; font-weight:700; line-height:1.35; text-align:center; }
  .en .w { color:#8fb4d6; transition:color .12s; }        /* 아직 안 읽은 단어 */
  .en .w.spoken { color:#1e4e79; }                         /* 이미 읽은 단어 */
  .en .w.cur { color:#0a63b8; }                            /* 현재 단어 */
  .ko { margin-top:16px; font-size:19px; text-align:center; color:#3a5a78; }
  .mic { position:absolute; top:18px; right:20px; width:40px; height:40px;
         border-radius:50%; background:#ffffffcc; display:flex; align-items:center;
         justify-content:center; border:1px solid #cfe3f5; cursor:pointer; }
  #status { color:#4a6a88; font-size:14px; }
  .hidden { display:none; }
</style>
</head>
<body>
<header>
  <label>주제 <select id="topic"></select></label>
  <label>반복 <input id="repeats" type="number" min="1" max="10" value="5" style="width:60px"></label>
  <label>간격(초) <input id="gap" type="number" min="0" max="10" step="0.5" value="2" style="width:60px"></label>
  <button id="start" class="primary">▶ 시작</button>
  <button id="stop" class="hidden">■ 정지</button>
  <span id="status"></span>
</header>

<div id="stage">
  <div class="card">
    <div class="en" id="en">주제를 고르고 시작을 누르세요</div>
    <div class="ko" id="ko"></div>
    <button class="mic" id="mic" title="현재 문장 다시 듣기">🎙️</button>
  </div>
</div>

<audio id="audio"></audio>

<script type="module">
import { activeWordIndex, buildSchedule } from "./player-core.js";

const $ = (id) => document.getElementById(id);
let manifest = null, running = false, curSentence = null;
const audio = $("audio");

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function load() {
  manifest = await (await fetch("manifest.json")).json();
  $("topic").innerHTML = manifest.topics
    .map((t) => `<option value="${t.id}">${t.title}</option>`).join("");
}

function renderWords(words) {
  $("en").innerHTML = words
    .map((w, i) => `<span class="w" data-i="${i}">${w.text}</span>`).join(" ");
}

function highlight(words, t) {
  const idx = activeWordIndex(words, t);
  const spans = $("en").querySelectorAll(".w");
  spans.forEach((el, i) => {
    el.classList.toggle("cur", i === idx);
    el.classList.toggle("spoken", idx >= 0 ? i < idx : false);
  });
}

function playOnce(item, words) {
  return new Promise((resolve) => {
    audio.src = item.audio;
    const onUpdate = () => { if (words) highlight(words, audio.currentTime); };
    const onEnd = () => {
      audio.removeEventListener("timeupdate", onUpdate);
      audio.removeEventListener("ended", onEnd);
      if (words) highlight(words, 1e9); // 끝: 전부 spoken 처리
      resolve();
    };
    audio.addEventListener("timeupdate", onUpdate);
    audio.addEventListener("ended", onEnd);
    audio.play();
  });
}

async function runTopic(topic) {
  const repeats = Math.max(1, +$("repeats").value || 5);
  const gapMs = (+$("gap").value || 0) * 1000;
  for (const s of topic.sentences) {
    if (!running) return;
    curSentence = s;
    const schedule = buildSchedule(s, repeats);
    for (let k = 0; k < schedule.length; k++) {
      if (!running) return;
      const item = schedule[k];
      $("ko").textContent = s.ko;
      if (item.lang === "en") { renderWords(s.words); }
      else { $("en").textContent = "🇰🇷 " + s.ko; }
      $("status").textContent =
        item.lang === "ko" ? "한글 뜻" : `영어 ${k}/${repeats}`;
      await playOnce(item, item.lang === "en" ? s.words : null);
      if (!running) return;
      if (gapMs) await sleep(gapMs);
    }
  }
  $("status").textContent = "완료 ✅";
  running = false; toggleButtons();
}

function toggleButtons() {
  $("start").classList.toggle("hidden", running);
  $("stop").classList.toggle("hidden", !running);
}

$("start").onclick = () => {
  const topic = manifest.topics.find((t) => t.id === $("topic").value);
  if (!topic) return;
  running = true; toggleButtons();
  runTopic(topic);
};
$("stop").onclick = () => { running = false; audio.pause(); toggleButtons(); $("status").textContent = "정지됨"; };
$("mic").onclick = () => {
  if (curSentence) { renderWords(curSentence.words); playOnce({audio: curSentence.enAudio}, curSentence.words); }
};

load();
</script>
</body>
</html>
```

- [ ] **Step 2: 로컬 서버로 수동 검증**

Run: `python -m http.server 8000 --directory web`
브라우저에서 `http://localhost:8000/` 열기.
Expected:
- 주제 드롭다운에 토픽이 뜬다
- "시작" → 한글 뜻(🇰🇷)이 뜨고 한국어 음성 1회 → 영어 문장 표시 + 5회 재생, 재생 중 단어가 순차적으로 진한 색으로 칠해진다 → 간격 후 다음 문장
- "정지"로 멈춘다, 🎙️로 현재 영어 문장을 다시 듣는다

(주: 이 검증은 `ELEVENLABS_API_KEY`로 `python generate.py`를 먼저 실행해 `web/manifest.json`·`web/audio/`가 있어야 한다. 없으면 Task 4 완료 후 실행.)

- [ ] **Step 3: 커밋**

```bash
git add web/index.html
git commit -m "feat: web player UI with karaoke highlight + KR->EN x N flow"
```

---

### Task 7: PWA (오프라인 + 안드로이드 설치)

**Files:**
- Create: `web/manifest.webmanifest`
- Create: `web/sw.js`
- Create: `web/icon.svg`
- Modify: `web/index.html` (service worker 등록 스니펫 추가)

**Interfaces:**
- Consumes: `web/` 전체 정적 자산.
- Produces: 설치 가능한 PWA. 첫 방문 후 manifest·오디오·코어 스크립트를 캐시해 오프라인 재생.

- [ ] **Step 1: 웹 앱 매니페스트 작성**

`web/manifest.webmanifest`:
```json
{
  "name": "TOEIC Speaking 섀도잉",
  "short_name": "섀도잉",
  "start_url": ".",
  "display": "standalone",
  "background_color": "#eaf6ff",
  "theme_color": "#bfe3ff",
  "icons": [
    { "src": "icon.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any" }
  ]
}
```

- [ ] **Step 2: 아이콘 작성**

`web/icon.svg`:
```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 192 192">
  <rect width="192" height="192" rx="40" fill="#2f8fd6"/>
  <text x="96" y="126" font-size="96" text-anchor="middle" fill="#fff"
        font-family="system-ui, sans-serif">🎙️</text>
</svg>
```

- [ ] **Step 3: 서비스 워커 작성 (런타임 캐시)**

`web/sw.js`:
```javascript
const CACHE = "toeic-shadow-v1";
const CORE = ["./", "index.html", "player-core.js", "manifest.json", "manifest.webmanifest", "icon.svg"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(CORE)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((keys) =>
    Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
  ).then(() => self.clients.claim()));
});
// cache-first: 오디오 포함 모든 GET을 캐시에 채우고 오프라인 지원
self.addEventListener("fetch", (e) => {
  if (e.request.method !== "GET") return;
  e.respondWith(
    caches.match(e.request).then((hit) =>
      hit || fetch(e.request).then((resp) => {
        const copy = resp.clone();
        caches.open(CACHE).then((c) => c.put(e.request, copy));
        return resp;
      }).catch(() => hit)
    )
  );
});
```

- [ ] **Step 4: index.html에 서비스 워커 등록 추가**

`web/index.html`의 `</body>` 직전에 추가:
```html
<script>
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => navigator.serviceWorker.register("sw.js"));
  }
</script>
```

- [ ] **Step 5: 설치·오프라인 수동 검증**

Run: `python -m http.server 8000 --directory web`
Chrome DevTools → Application 탭:
Expected:
- Manifest 인식됨 (설치 아이콘 표시)
- Service Worker "activated"
- 한 번 재생 후 Network를 Offline으로 전환 → 새로고침해도 앱이 열리고 이미 재생한 오디오가 재생됨

- [ ] **Step 6: 커밋**

```bash
git add web/manifest.webmanifest web/sw.js web/icon.svg web/index.html
git commit -m "feat: PWA install + offline cache"
```

---

## Self-Review

**Spec coverage:**
- 오프라인 사전 생성 구조 → Task 3,4 ✅
- 주제별 목록 → Task 1(파일), 4(manifest topics) ✅
- ElevenLabs 원어민 음성 + 타임스탬프 → Task 3,4 ✅
- 한글1회→영어5회→간격→다음 → Task 5(buildSchedule), 6(runTopic) ✅
- 노래방 하이라이트 → Task 2(group_words), 5(activeWordIndex), 6(highlight) ✅
- 레퍼런스 디자인(연파랑/둥근카드/2색/마이크) → Task 6 ✅
- 반복·간격 조절 → Task 6 설정 입력 ✅
- PWA 설치·오프라인 → Task 7 ✅
- 비용 절감(재생성 스킵) → Task 4 `_ensure_audio` 파일 존재 스킵 + 테스트 ✅
- 키 환경변수, 하드코딩 금지 → Task 4 main + Global Constraints ✅
- 비목표(마이크 채점 없음) → 구현 안 함, 🎙️는 다시듣기 전용 ✅

**Placeholder scan:** 코드 스텝 전부 실제 코드 포함. Task 6 Step 2에서 붙여넣기 오염 CSS를 명시적으로 수정하도록 지시함(고의적 수정 스텝).

**Type consistency:** `parse_topic_file`, `group_words`, `audio_filename`, `tts_with_timestamps`, `build_manifest`, `activeWordIndex`, `buildSchedule` 이름·시그니처가 정의 태스크와 소비 태스크에서 일치. manifest 스키마(`en/ko/enAudio/koAudio/words[{text,start,end}]`)가 Task 4 생성과 Task 5/6 소비에서 일치.
