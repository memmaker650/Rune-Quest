from RuneQuest.db import Database


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
    assert db.conn.execute("PRAGMA user_version").fetchone()[0] == 3


def test_persists_on_disk(tmp_path):
    path = tmp_path / "orbes.db"
    db = Database(path)
    db.add_score("z", 10, 1)
    db.close()
    assert Database(path).top_scores()[0]["player"] == "z"


STATE = {"score": 1234, "level": 3, "taps": 7, "rains": 1, "best_chain": 9, "mode": "fast",
         "rows": 14, "cols": 8, "balls": [[13, 0, 2], [13, 1, 0], [12, 0, 5]]}


def test_saved_game_round_trip():
    db = Database(":memory:")
    assert db.load_game() is None and not db.has_saved_game()
    db.save_game(STATE)
    assert db.has_saved_game()
    assert db.load_game() == STATE
    db.save_game({**STATE, "score": 2000})       # solo hay una partida guardada
    assert db.conn.execute("SELECT COUNT(*) FROM EstadoPartida").fetchone()[0] == 1
    assert db.load_game()["score"] == 2000
    db.delete_game()
    assert db.load_game() is None


def test_v1_database_gets_estado_partida_table(tmp_path):
    import sqlite3
    from RuneQuest.db import SCHEMA_V1

    path = tmp_path / "v1.db"
    conn = sqlite3.connect(path); conn.executescript(SCHEMA_V1)
    conn.execute("INSERT INTO scores (player, score, level) VALUES ('Ana', 10, 1)")
    conn.commit(); conn.close()
    db = Database(path)
    assert db.conn.execute("PRAGMA user_version").fetchone()[0] == 3
    assert db.best_score() == 10                 # los datos v1 se conservan
    db.save_game(STATE)
    assert db.load_game() == STATE


def test_corrupt_saved_game_is_discarded():
    db = Database(":memory:")
    db.save_game(STATE)
    db.conn.execute("UPDATE EstadoPartida SET bolas = 'no es json'")
    assert db.load_game() is None
    assert not db.has_saved_game()


def test_v2_saved_game_gets_classic_mode(tmp_path):
    import json
    import sqlite3
    from RuneQuest.db import SCHEMA_V1, SCHEMA_V2

    path = tmp_path / "v2.db"
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA_V1)
    conn.executescript(SCHEMA_V2)
    conn.execute("INSERT INTO EstadoPartida (id, puntuacion, nivel, filas, columnas, bolas) "
                 "VALUES (1, 50, 1, 14, 8, ?)", (json.dumps([[13, 0, 1]]),))
    conn.commit(); conn.close()
    db = Database(path)
    assert db.load_game()["mode"] == "classic"   # partidas guardadas antes de los modos
