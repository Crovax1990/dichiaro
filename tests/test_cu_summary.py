"""Tests for CU annual aggregation and 730 reconciliation."""

from pathlib import Path

from backend.models import Dichiarazione, QuadroC_Lavoro, create_engine_session
from backend.parser.cu_importer import import_cus_to_db
from backend.parser.cu_summary import compare_cu_with_730, summarize_cu


CU_DIR = Path(__file__).parent.parent / "data" / "CU"


def test_summary_keeps_two_cu_sources_and_totals(tmp_path):
    engine, SessionLocal = create_engine_session(str(tmp_path / "cu.db"))
    session = SessionLocal()
    paths = sorted(CU_DIR.glob("CUK_T260*.pdf"))

    try:
        results = import_cus_to_db(paths, session)
        persona_id = results[0]["persona"].id
        payloads_before = {
            document.id: document.payload_json
            for document in results[0]["persona"].certificazioni_uniche
        }
        summary = summarize_cu(session, persona_id, 2025)

        assert summary["numero_cu"] == 2
        assert len(summary["sostituti"]) == 2
        assert summary["totali"]["reddito_principale"] == 42350.58
        assert len(summary["fonti"]) == 2
        assert all(source["valori"]["reddito_principale"] for source in summary["fonti"])
        payloads_after = {
            document.id: document.payload_json
            for document in results[0]["persona"].certificazioni_uniche
        }
        assert payloads_after == payloads_before
    finally:
        session.close()
        engine.dispose()


def test_compare_cu_with_730_and_missing_730(tmp_path):
    engine, SessionLocal = create_engine_session(str(tmp_path / "cu.db"))
    session = SessionLocal()
    paths = sorted(CU_DIR.glob("CUK_T260*.pdf"))

    try:
        results = import_cus_to_db(paths, session)
        persona = results[0]["persona"]
        missing = compare_cu_with_730(session, persona.id, 2025)
        assert missing["stato"] == "730_assente"

        declaration = Dichiarazione(persona_id=persona.id, anno_fiscale=2025, tipo="730")
        session.add(declaration)
        session.flush()
        session.add(QuadroC_Lavoro(
            dichiarazione_id=declaration.id,
            rigo=1,
            reddito=42350.58,
            ritenute=7175.18,
        ))
        session.commit()

        comparison = compare_cu_with_730(session, persona.id, 2025)
        assert comparison["stato"] == "coerente"
        assert comparison["differenza"] == 0
        assert comparison["riepilogo_cu"]["numero_cu"] == 2
    finally:
        session.close()
        engine.dispose()
