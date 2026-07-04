import tempfile
import os
from pathlib import Path
from datetime import date

from backend.models import (
    Base, Persona, Dichiarazione, QuadroC_Lavoro,
    QuadroB_Fabbricati, QuadroE_Oneri, Risultato, create_engine_session,
)


def test_create_tables():
    db_path = Path(tempfile.gettempdir()) / "test_analyzer.db"
    engine, SessionLocal = create_engine_session(str(db_path))
    session = SessionLocal()

    try:
        persona = Persona(
            codice_fiscale="RSSMRA80A01H501U",
            nome="MARIO",
            cognome="ROSSI",
            data_nascita=date(1990, 7, 2),
            sesso="M",
            comune_nascita="TERNI",
            provincia_nascita="TR",
        )
        session.add(persona)
        session.flush()

        dich = Dichiarazione(
            persona_id=persona.id,
            anno_fiscale=2025,
            tipo="730",
            congiunta=False,
        )
        session.add(dich)
        session.flush()

        c1 = QuadroC_Lavoro(
            dichiarazione_id=dich.id,
            rigo=1,
            reddito=39043,
            giorni=365,
            ritenute=9354,
            tipologia="dipendente",
        )
        session.add(c1)

        e1 = QuadroE_Oneri(
            dichiarazione_id=dich.id,
            codice_rigo="E1",
            descrizione="Spese sanitarie",
            importo=500,
            rateizzata=False,
        )
        session.add(e1)

        r = Risultato(
            dichiarazione_id=dich.id,
            imposta_netta=9005,
            ritenute=9354,
            differenza=-349,
            esito="credito",
            reddito_complessivo=39043,
        )
        session.add(r)

        session.commit()

        assert persona.id is not None
        assert dich.id is not None
        assert session.query(Persona).count() == 1
        assert session.query(Dichiarazione).count() == 1
        assert len(dich.quadri_c) == 1
        assert len(dich.quadri_e) == 1
        assert dich.risultato.esito == "credito"
        assert float(dich.risultato.differenza) == -349

    finally:
        session.close()
        os.unlink(db_path)


def test_duplicate_persona_prevented():
    db_path = Path(tempfile.gettempdir()) / "test_analyzer_dup.db"
    engine, SessionLocal = create_engine_session(str(db_path))
    session = SessionLocal()

    try:
        p1 = Persona(codice_fiscale="RSSMRA80A01H501U", nome="MARIO", cognome="ROSSI")
        session.add(p1)
        session.commit()

        import sqlalchemy.exc
        p2 = Persona(codice_fiscale="RSSMRA80A01H501U", nome="MARIO", cognome="ROSSI")
        session.add(p2)
        try:
            session.commit()
            assert False, "Should have raised IntegrityError"
        except sqlalchemy.exc.IntegrityError:
            session.rollback()
    finally:
        session.close()
        os.unlink(db_path)
