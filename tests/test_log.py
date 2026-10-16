import logging
from datetime import date, datetime

from RuneQuest import db
from RuneQuest.log import DailyFileHandler, log_file_for, remove_old_logs


def test_log_file_name_uses_date():
    assert log_file_for("x", date(2026, 10, 16)).name == "RuneQuest_20261016.log"


def test_remove_old_logs_keeps_last_seven_days(tmp_path):
    today = date(2026, 10, 16)
    for name in ["RuneQuest_20261016.log", "RuneQuest_20261009.log",   # hoy y hace 7 días
                 "RuneQuest_20261008.log", "RuneQuest_20250101.log",   # más de 7 días
                 "RuneQuest_notadate.log", "otro.log"]:
        (tmp_path / name).write_text("x")
    removed = remove_old_logs(tmp_path, today)
    assert sorted(p.name for p in removed) == ["RuneQuest_20250101.log", "RuneQuest_20261008.log"]
    assert sorted(p.name for p in tmp_path.iterdir()) == [
        "RuneQuest_20261009.log", "RuneQuest_20261016.log", "RuneQuest_notadate.log", "otro.log"]


def test_daily_handler_switches_file_at_midnight(tmp_path):
    handler = DailyFileHandler(tmp_path)
    handler.day = date(2026, 10, 15)             # simulamos que la app arrancó ayer
    record = logging.LogRecord("t", logging.INFO, __file__, 1, "hola", None, None)
    record.created = datetime(2026, 10, 16, 0, 0, 5).timestamp()
    handler.emit(record)
    handler.close()
    assert (tmp_path / "RuneQuest_20261016.log").read_text().strip() == "hola"


def test_legacy_database_is_copied_once(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "_data_dir", lambda name: tmp_path / name)
    legacy = tmp_path / "Orbes" / db.LEGACY_DB_NAME
    legacy.parent.mkdir()
    old = db.Database(legacy); old.add_score("Ana", 500, 2); old.close()

    path = db.default_db_path()
    assert path == tmp_path / "RuneQuest" / db.DB_NAME
    new = db.Database(path)
    assert new.best_score() == 500
    new.add_score("Ana", 900, 3); new.close()
    db.default_db_path()                         # la segunda vez no machaca la nueva
    assert db.Database(path).best_score() == 900
    assert legacy.exists()                       # la antigua se conserva


def test_orbes_db_in_new_folder_is_renamed(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "_data_dir", lambda name: tmp_path / name)
    (tmp_path / "RuneQuest").mkdir()
    old = db.Database(tmp_path / "RuneQuest" / db.LEGACY_DB_NAME); old.add_score("Ana", 700, 2)
    old.close()
    path = db.default_db_path()
    assert path.name == "RuneQuest_database.db"
    assert db.Database(path).best_score() == 700
