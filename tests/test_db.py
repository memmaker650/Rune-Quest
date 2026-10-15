from orbes.db import Database


def test_scores_sorted_and_limited():
    db = Database(":memory:")
    for name, score in [("a", 50), ("b", 300), ("c", 120)]:
        db.add_score(name, score, 1)
    top = db.top_scores(2)
    assert [r["player"] for r in top] == ["b", "c"]


def test_best_score():
    db = Database(":memory:")
    assert db.best_score() == 0
    db.add_score("a", 50, 1)
    db.add_score("b", 300, 2)
    assert db.best_score() == 300


def test_settings_roundtrip_and_overwrite():
    db = Database(":memory:")
    assert db.get_setting("x", "d") == "d"
    db.set_setting("x", 1)
    db.set_setting("x", 2)
    assert db.get_setting("x") == "2"


def test_schema_version_is_set():
    db = Database(":memory:")
    assert db.conn.execute("PRAGMA user_version").fetchone()[0] == 1


def test_persists_on_disk(tmp_path):
    path = tmp_path / "orbes.db"
    db = Database(path)
    db.add_score("z", 10, 1)
    db.close()
    assert Database(path).top_scores()[0]["player"] == "z"
