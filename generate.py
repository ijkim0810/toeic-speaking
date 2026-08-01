import base64
import glob
import hashlib
import json
import os
import urllib.request


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


EN_VOICE_ID = "nPczCjzI2devNBz1zQrb"   # Brian (미국 남성)
KO_VOICE_ID = "wNzr5UkgSu9yW9YkgI5h"   # Yona (한국어 여성, 원어민)
MODEL = "eleven_multilingual_v2"


def _ensure_audio(text, voice, api_key, web_dir, want_words, tts):
    """오디오(영어면 단어 타임스탬프 사이드카도)를 확보. 이미 있으면 API 재호출 없이 재사용.

    영어 문장의 단어 타임스탬프는 mp3 옆에 `<hash>.mp3.words.json`으로 함께 저장한다.
    덕분에 재실행·중복 문장·중단 후 재개 어느 경우에도 이미 생성된 문장은 API를 다시
    부르지 않는다 (manifest.json은 실행 끝에만 쓰이므로 그것에 의존하면 안 됨)."""
    rel = audio_filename(voice, MODEL, text)
    dest = os.path.join(web_dir, rel)
    words_path = dest + ".words.json"
    if os.path.exists(dest) and (not want_words or os.path.exists(words_path)):
        if want_words:
            with open(words_path, encoding="utf-8") as f:
                return rel, json.load(f)
        return rel, None
    result = tts(text, voice, api_key, MODEL)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "wb") as f:
        f.write(result["audio"])
    words = None
    if want_words:
        a = result["alignment"]
        words = group_words(
            a["characters"],
            a["character_start_times_seconds"],
            a["character_end_times_seconds"],
        )
        with open(words_path, "w", encoding="utf-8") as f:
            json.dump(words, f, ensure_ascii=False)
    return rel, words


def build_manifest(topics_dir, web_dir, api_key, en_voice, ko_voice, tts=tts_with_timestamps):
    topics = []
    for path in sorted(glob.glob(os.path.join(topics_dir, "*.txt"))):
        topic_id = os.path.splitext(os.path.basename(path))[0]
        sentences = []
        for en, ko in parse_topic_file(path):
            en_rel, words = _ensure_audio(en, en_voice, api_key, web_dir, True, tts)
            ko_rel, _ = _ensure_audio(ko, ko_voice, api_key, web_dir, False, tts)
            sentences.append({"en": en, "ko": ko, "enAudio": en_rel,
                              "koAudio": ko_rel, "words": words})
        topics.append({"id": topic_id, "title": topic_id, "sentences": sentences})
    manifest = {"topics": topics}
    with open(os.path.join(web_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    return manifest


def _load_dotenv(root):
    """프로젝트 루트의 .env가 있으면 환경변수로 로드 (KEY=VALUE 형식)."""
    path = os.path.join(root, ".env")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def main():
    root = os.path.dirname(os.path.abspath(__file__))
    _load_dotenv(root)
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        raise SystemExit("환경변수 ELEVENLABS_API_KEY 를 설정하세요.")
    build_manifest(os.path.join(root, "topics"), os.path.join(root, "web"),
                   api_key, EN_VOICE_ID, KO_VOICE_ID)
    print("완료: web/manifest.json 생성됨")


if __name__ == "__main__":
    main()
