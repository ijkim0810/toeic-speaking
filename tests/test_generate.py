import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from generate import parse_topic_file, group_words, audio_filename

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


def test_build_manifest_no_duplicate_api_calls_within_run(tmp_path):
    # 같은 영어 문장이 한 번의 실행 안에서 두 토픽에 걸쳐 등장해도 EN 생성은 1회여야 함
    topics = tmp_path / "topics"; topics.mkdir()
    (topics / "a.txt").write_text("He runs. | 그는 달려요.\n", encoding="utf-8")
    (topics / "b.txt").write_text("He runs. | 그는 달린다.\n", encoding="utf-8")
    web = tmp_path / "web"; web.mkdir()

    calls = []
    def fake_tts(text, voice_id, api_key, model="eleven_multilingual_v2"):
        calls.append((voice_id, text))
        return {"audio": b"X", "alignment": {
            "characters": list(text),
            "character_start_times_seconds": [i * 0.1 for i in range(len(text))],
            "character_end_times_seconds": [(i + 1) * 0.1 for i in range(len(text))],
        }}

    build_manifest(str(topics), str(web), "k", "envoice", "kovoice", tts=fake_tts)
    en_calls = [c for c in calls if c == ("envoice", "He runs.")]
    assert len(en_calls) == 1
