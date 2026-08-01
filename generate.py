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
