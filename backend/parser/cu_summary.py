"""Annual CU aggregation and comparison with 730 Quadro C data."""

from __future__ import annotations

from sqlalchemy.orm import Session

from backend.models import CertificazioneUnica, Dichiarazione, QuadroC_Lavoro


AGGREGATE_COLUMNS = (
    "reddito_principale",
    "ritenute_irpef",
    "addizionale_regionale",
    "addizionale_comunale",
    "imposta_lorda",
    "totale_detrazioni",
    "imposta_netta",
    "trattamento_integrativo",
    "benefit",
)


def summarize_cu(session: Session, persona_id: int, anno_fiscale: int) -> dict:
    """Return a provenance-preserving summary for one person and tax year."""
    documents = (
        session.query(CertificazioneUnica)
        .filter_by(persona_id=persona_id, anno_fiscale=anno_fiscale)
        .order_by(CertificazioneUnica.id)
        .all()
    )
    totals = {column: 0.0 for column in AGGREGATE_COLUMNS}
    sources = []
    warnings = []
    for document in documents:
        source = {
            "id": document.id,
            "file_name": document.nome_file,
            "sostituto": document.denominazione_sostituto,
            "codice_fiscale_sostituto": document.codice_fiscale_sostituto,
            "anno_fiscale": document.anno_fiscale,
            "stato": document.stato,
            "identificativo_dichiarazione": document.identificativo_dichiarazione,
            "valori": {},
        }
        for column in AGGREGATE_COLUMNS:
            value = getattr(document, column)
            if isinstance(value, (int, float)):
                totals[column] += value
                source["valori"][column] = value
        if document.stato != "ok":
            warnings.append(f"{document.nome_file}: stato {document.stato}")
        sources.append(source)

    return {
        "persona_id": persona_id,
        "anno_fiscale": anno_fiscale,
        "numero_cu": len(documents),
        "sostituti": sorted({
            value for value in (
                document.denominazione_sostituto for document in documents
            ) if value
        }),
        "totali": {key: round(value, 2) for key, value in totals.items()},
        "fonti": sources,
        "warning": warnings,
    }


def compare_cu_with_730(
    session: Session,
    persona_id: int,
    anno_fiscale: int,
    tolerance: float = 1.0,
) -> dict:
    """Compare CU income with the 730 Quadro C without changing either source."""
    summary = summarize_cu(session, persona_id, anno_fiscale)
    declared = (
        session.query(Dichiarazione)
        .filter_by(persona_id=persona_id, anno_fiscale=anno_fiscale, tipo="730")
        .order_by(Dichiarazione.id)
        .first()
    )
    cu_income = summary["totali"]["reddito_principale"]
    if declared is None:
        return {
            "stato": "730_assente",
            "anno_fiscale": anno_fiscale,
            "totale_cu": cu_income,
            "totale_730": None,
            "differenza": None,
            "riepilogo_cu": summary,
        }

    quadro_c = session.query(QuadroC_Lavoro).filter_by(dichiarazione_id=declared.id).all()
    declared_income = round(sum((entry.reddito or 0) for entry in quadro_c), 2)
    difference = round(cu_income - declared_income, 2)
    return {
        "stato": "coerente" if abs(difference) <= tolerance else "differente",
        "anno_fiscale": anno_fiscale,
        "totale_cu": cu_income,
        "totale_730": declared_income,
        "differenza": difference,
        "tolleranza": tolerance,
        "dichiarazione_730_id": declared.id,
        "riepilogo_cu": summary,
    }
