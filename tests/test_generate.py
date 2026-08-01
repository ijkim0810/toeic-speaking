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
