"""Import parsed textual 730 data into the database."""

from pathlib import Path
from sqlalchemy.orm import Session

from backend.models import (
    Persona, Dichiarazione, QuadroC_Lavoro, QuadroB_Fabbricati,
    QuadroE_Oneri, Risultato,
)
from backend.parser.extractor import parse_730

# Utilizzo codes mapping
UTILIZZO_MAP = {
    1: "Abitazione principale",
    2: "Abitazione principale (pertinenza)",
    3: "Abitazione a disposizione",
    4: "Abitazione tenuta a disposizione",
    5: "Abitazione principale",
    9: "Altro",
    10: "Abitazione locata (libero mercato)",
    11: "Abitazione locata (canone concordato)",
}


def import_pdf_to_db(
    pdf_path: str | Path,
    session: Session,
    persona_id: int | None = None,
    anno: int | None = None,
) -> tuple[Dichiarazione, Persona, bool]:
    """
    Parse a textual 730 PDF and import its data into the database.

    Auto-detects anno and persona from PDF metadata if not provided.
    Creates persona record if CF not found (ponytail: single upsert, add conflict handling if needed).

    Returns (dichiarazione, persona, persona_created).
    """
    data = parse_730(pdf_path)
    meta = data.get("metadata", {})

    actual_anno = anno or meta.get("anno")
    cf = meta.get("codice_fiscale")
    nome = meta.get("nome", "")
    cognome = meta.get("cognome", "")

    persona_created = False
    if persona_id:
        persona = session.get(Persona, persona_id)
        if not persona:
            raise ValueError(f"Persona id={persona_id} not found")
    elif cf:
        persona = session.query(Persona).filter_by(codice_fiscale=cf).first()
        if not persona:
            persona = Persona(codice_fiscale=cf, nome=nome or "", cognome=cognome or "")
            session.add(persona)
            session.flush()
            persona_created = True
    else:
        raise ValueError("No persona_id provided and no CF found in PDF metadata")

    dich = Dichiarazione(
        persona_id=persona.id,
        anno_fiscale=actual_anno,
        tipo="730",
        congiunta=False,
    )
    session.add(dich)
    session.flush()

    # Quadro B — Fabbricati
    for entry in data.get("quadro_b", []):
        qb = QuadroB_Fabbricati(
            dichiarazione_id=dich.id,
            rigo=entry["rigo"],
            rendita=_num(entry, "Rendita"),
            utilizzo=str(entry.get("valore")) if entry.get("colonna") == 2 and entry.get("valore") is not None else None,
            giorni_possesso=_num(entry, "Giorni"),
            percentuale=_num(entry, "Percentuale"),
        )
        session.add(qb)

    # Quadro C — Lavoro dipendente
    for entry in data.get("quadro_c", []):
        qc = QuadroC_Lavoro(
            dichiarazione_id=dich.id,
            rigo=entry["rigo"],
            reddito=_num(entry, "Reddito") if entry.get("colonna") == 3 else 0,
            ritenute=_num(entry, "Ritenute IRPEF") if entry.get("colonna") == 1 else 0,
            giorni=_num(entry, "Lavoro dipendente") if "Lavoro dipendente" in entry.get("descrizione", "") else None,
            tipologia="dipendente",
        )
        if qc.ritenute or qc.reddito:
            session.add(qc)

    # Quadro E — Oneri (solo voci con "Importo" nella descrizione)
    for entry in data.get("quadro_e", []):
        desc = entry.get("descrizione", "")
        if "importo" not in desc.lower():
            continue
        qe = QuadroE_Oneri(
            dichiarazione_id=dich.id,
            codice_rigo=f"E{entry['rigo']}" if entry.get("colonna") not in (1, 8) else f"E{entry['rigo']}.col{entry['colonna']}",
            descrizione=desc,
            importo=entry.get("valore") if isinstance(entry.get("valore"), (int, float)) else 0,
        )
        if qe.importo:
            session.add(qe)

    # Risultato
    pl = data.get("prospetto_liquidazione", {})
    r = Risultato(
        dichiarazione_id=dich.id,
        imposta_netta=_pl(pl, "50_col_1"),
        ritenute=_pl(pl, "59_col_1"),
        differenza=_pl(pl, "60_col_1"),
        esito="credito" if (_pl(pl, "60_col_1") or 0) < 0 else "debito",
        reddito_complessivo=_pl(pl, "11_col_1"),
        reddito_imponibile=_pl(pl, "14_col_1"),
        imposta_lorda=_pl(pl, "16_col_1"),
        detrazione_lavoro_dipendente=_pl(pl, "25_col_1"),
        detrazione_oneri=_pl(pl, "28_col_1"),
        detrazione_recupero_edilizio=_pl(pl, "29_col_1"),
        detrazione_risparmio_energetico=_pl(pl, "31_col_1"),
        addiz_regionale_dovuta=_pl(pl, "72_col_1"),
        addiz_regionale_certificazione=_pl(pl, "73_col_1"),
        addiz_comunale_dovuta=_pl(pl, "75_col_1"),
        addiz_comunale_certificazione=_pl(pl, "76_col_1"),
        acconto_irpef_prima_rata=_pl(pl, "78_col_1"),
        acconto_irpef_seconda_rata=_pl(pl, "79_col_1"),
    )
    session.add(r)

    session.commit()
    return dich, persona, persona_created


def _pl(pl: dict, suffix: str) -> float:
    for k, v in pl.items():
        if k.endswith(suffix) and isinstance(v, dict):
            val = v.get("valore")
            return float(val) if isinstance(val, (int, float)) else 0
    return 0


def _num(entry: dict, keyword: str) -> float:
    if keyword.lower() in entry.get("descrizione", "").lower():
        val = entry.get("valore")
        return float(val) if isinstance(val, (int, float)) else 0
    return 0



