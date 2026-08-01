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
