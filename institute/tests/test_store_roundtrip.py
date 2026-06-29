import os
import tempfile

from institute.corpus import store


def test_append_and_load_roundtrip():
    recs = [{"a": 1, "b": "x"}, {"a": 2, "b": "y"}]
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "sub", "rows.jsonl")
        store.append_jsonl(path, recs)
        loaded = store.load_jsonl(path)
        assert loaded == recs
        store.append_jsonl(path, [{"a": 3, "b": "z"}])
        assert len(store.load_jsonl(path)) == 3
