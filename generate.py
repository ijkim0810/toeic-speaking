import base64
import hashlib
import json
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
