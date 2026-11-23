import logging
import os
from datetime import date, datetime

from RuneQuest import db
from RuneQuest.log import DailyFileHandler, log_file_for, remove_old_logs


def test_log_file_name_uses_date():
    assert log_file_for("x", date(2026, 10, 16)).name == "RuneQuest_20261016.log"


def test_remove_old_logs_keeps_the_ten_most_recent_files(tmp_path):
    days = [date(2026, 1, 1), date(2026, 3, 5), date(2026, 3, 6)] + \
        [date(2026, 10, d) for d in range(1, 11)]             # 13 logs, no seguidos
    for day in days:
        log_file_for(tmp_path, day).write_text("x")
    for name in ("RuneQuest_notadate.log", "RuneQuest_20261340.log", "otro.log"):
        (tmp_path / name).write_text("x")                     # no son logs diarios: no se tocan
    removed = remove_old_logs(tmp_path)
    assert [p.name for p in removed] == ["RuneQuest_20260101.log", "RuneQuest_20260305.log",
                                         "RuneQuest_20260306.log"]
    kept = sorted(p.name for p in tmp_path.glob("RuneQuest_2026????.log")
                  if p.name != "RuneQuest_20261340.log")
    assert kept == [f"RuneQuest_202610{d:02d}.log" for d in range(1, 11)]
    for name in ("RuneQuest_notadate.log", "RuneQuest_20261340.log", "otro.log"):
        assert (tmp_path / name).exists()


def test_old_logs_far_apart_are_kept_if_among_the_last_ten(tmp_path):
    for year in range(2020, 2026):                            # 6 logs, uno por año
        log_file_for(tmp_path, date(year, 1, 1)).write_text("x")
    assert remove_old_logs(tmp_path) == []


def test_daily_handler_switches_file_at_midnight(tmp_path):
    handler = DailyFileHandler(tmp_path)
    handler.day = date(2026, 10, 15)             # simulamos que la app arrancó ayer
    record = logging.LogRecord("t", logging.INFO, __file__, 1, "hola", None, None)
    record.created = datetime(2026, 10, 16, 0, 0, 5).timestamp()
    handler.emit(record)
    handler.close()
    assert (tmp_path / "RuneQuest_20261016.log").read_text().strip() == "hola"


def _data_dirs(monkeypatch, tmp_path):
    """Carpeta de datos nueva (paths.data_dir) y antiguas (platformdirs) dentro de tmp_path."""
    new = tmp_path / "com.SkullWithGasMask" / "RuneQuest"
    monkeypatch.setattr(db.paths, "data_dir", lambda: new)
    monkeypatch.setattr(db, "_data_dir", lambda name: tmp_path / "old" / name)
    return new, tmp_path / "old" / "RuneQuest"


def test_database_moves_from_the_previous_folder_once(tmp_path, monkeypatch):
    new, old_dir = _data_dirs(monkeypatch, tmp_path)
    old_dir.mkdir(parents=True)
    old = db.Database(old_dir / db.DB_NAME); old.add_score("Ana", 500, 2); old.close()

    path = db.default_db_path()
    assert path == new / "RuneQuest_database.db"
    fresh = db.Database(path)
    assert fresh.best_score() == 500
    fresh.add_score("Ana", 900, 3); fresh.close()
    db.default_db_path()                         # la segunda vez no machaca la nueva
    assert db.Database(path).best_score() == 900
    assert (old_dir / db.DB_NAME).exists()       # la antigua se conserva


def test_very_old_orbes_db_is_also_migrated(tmp_path, monkeypatch):
    new, old_dir = _data_dirs(monkeypatch, tmp_path)
    old_dir.mkdir(parents=True)
    old = db.Database(old_dir / db.LEGACY_DB_NAME); old.add_score("Ana", 700, 2); old.close()
    path = db.default_db_path()
    assert path.name == "RuneQuest_database.db"
    assert db.Database(path).best_score() == 700


def test_setup_logging_leaves_exactly_ten_including_today(tmp_path):
    """Regresión: la limpieza se hacía antes de crear el fichero de hoy y quedaban 11."""
    from RuneQuest.log import KEEP_FILES, PACKAGE, setup_logging
    for d in range(1, 13):                                    # 12 logs antiguos
        log_file_for(tmp_path, date(2025, 1, d)).write_text("x")
    logger = logging.getLogger(PACKAGE)
    saved = logger.handlers[:]
    logger.handlers.clear()
    try:
        setup_logging(log_dir=tmp_path)
        names = sorted(p.name for p in tmp_path.glob("RuneQuest_*.log"))
        assert len(names) == KEEP_FILES == 10
        assert names[-1] == log_file_for(tmp_path, date.today()).name
    finally:
        for h in logger.handlers:
            h.close()
        logger.handlers[:] = saved


def test_midnight_switch_leaves_exactly_ten(tmp_path):
    """Regresión: al pasar la medianoche también quedaban 11."""
    from datetime import timedelta
    today = date.today()
    for back in range(1, 11):                                 # 10 logs: de hace 10 días a ayer
        log_file_for(tmp_path, today - timedelta(days=back)).write_text("x")
    handler = DailyFileHandler(tmp_path)
    # Como si hubiera arrancado ayer: escribiendo en el fichero de ayer y sin fichero de hoy
    # (al crearse, el manejador abre el de hoy; en la vida real a medianoche aún no existe)
    handler.close()
    log_file_for(tmp_path, today).unlink()
    yesterday = today - timedelta(days=1)
    handler.baseFilename = os.path.abspath(log_file_for(tmp_path, yesterday))
    handler.day = yesterday                                   # arrancó ayer...
    record = logging.LogRecord("t", logging.INFO, __file__, 1, "nuevo día", None, None)
    record.created = datetime.combine(today, datetime.min.time()).timestamp() + 5  # ...00:00:05
    handler.emit(record)
    handler.close()
    names = sorted(p.name for p in tmp_path.glob("RuneQuest_*.log"))
    assert len(names) == 10
    assert names[-1] == log_file_for(tmp_path, today).name
    assert log_file_for(tmp_path, today - timedelta(days=10)).name not in names
