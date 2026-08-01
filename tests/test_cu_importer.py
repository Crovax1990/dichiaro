"""Database and idempotency tests for CU imports."""

from pathlib import Path

from backend.models import CertificazioneUnica, Persona, create_engine_session
from backend.parser.cu_importer import import_cu_to_db, import_cus_to_db


CU_DIR = Path(__file__).parent.parent / "data" / "CU"


def test_import_two_cu_for_same_person_and_year(tmp_path):
    engine, SessionLocal = create_engine_session(str(tmp_path / "cu.db"))
    session = SessionLocal()
    paths = sorted(CU_DIR.glob("CUK_T260*.pdf"))

    try:
        first, persona, created = import_cu_to_db(paths[0], session)
        second, same_persona, created_second = import_cu_to_db(paths[1], session)

        assert created is True
        assert created_second is False
        assert persona.id == same_persona.id
        assert session.query(Persona).count() == 1
        assert session.query(CertificazioneUnica).count() == 2
        assert {first.anno_fiscale, second.anno_fiscale} == {2025}
        assert {first.codice_fiscale_sostituto, second.codice_fiscale_sostituto} == {
            "00967720285",
            "01234830469",
        }
        assert round(first.reddito_principale + second.reddito_principale, 2) == 42350.58
    finally:
        session.close()
        engine.dispose()


def test_import_same_file_is_idempotent(tmp_path):
    engine, SessionLocal = create_engine_session(str(tmp_path / "cu.db"))
    session = SessionLocal()
    path = next(CU_DIR.glob("CUK_T260312*.pdf"))

    try:
        first, _, _ = import_cu_to_db(path, session)
        second, _, created = import_cu_to_db(path, session)
        assert first.id == second.id
        assert created is False
        assert session.query(CertificazioneUnica).count() == 1
    finally:
        session.close()
        engine.dispose()


def test_batch_import_isolates_errors(tmp_path):
    engine, SessionLocal = create_engine_session(str(tmp_path / "cu.db"))
    session = SessionLocal()
    valid = next(CU_DIR.glob("CUK_T250*.pdf"))

    try:
        results = import_cus_to_db([valid, tmp_path / "missing.pdf"], session)
        assert results[0]["error"] is None
        assert results[1]["document"] is None
        assert results[1]["error"]
        assert session.query(CertificazioneUnica).count() == 1
    finally:
        session.close()
        engine.dispose()
