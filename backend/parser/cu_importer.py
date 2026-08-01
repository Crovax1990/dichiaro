"""Persist parsed Certificazione Unica documents in the database."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

from sqlalchemy.orm import Session

from backend.models import CertificazioneUnica, Persona
from backend.parser.cu_extractor import parse_cu


_IMPORTER_VERSION = "1"


def import_cu_to_db(
    pdf_path: str | Path,
    session: Session,
    persona_id: int | None = None,
) -> tuple[CertificazioneUnica, Persona, bool]:
    """Parse and import one CU, returning (document, persona, persona_created)."""
    path = Path(pdf_path)
    digest = _sha256(path)

    existing = session.query(CertificazioneUnica).filter_by(hash_file=digest).first()
    if existing:
        return existing, existing.persona, False

    data = parse_cu(path)
    metadata = data.get("metadata", {})
    document_data = data.get("document", {})
    fiscal_year = document_data.get("anno_fiscale") or metadata.get("anno_fiscale")
    cf = (metadata.get("codice_fiscale") or data.get("percipiente", {}).get("codice_fiscale"))
    employer_data = data.get("sostituto", {})
    duplicate_query = session.query(CertificazioneUnica).filter_by(
        anno_fiscale=fiscal_year,
        identificativo_dichiarazione=document_data.get("identificativo_dichiarazione"),
        codice_fiscale_sostituto=employer_data.get("codice_fiscale"),
        numero_modello=document_data.get("numero_modello", 1),
    )
    if document_data.get("identificativo_dichiarazione"):
        existing = duplicate_query.first()
        if existing:
            return existing, existing.persona, False
    if not fiscal_year:
        raise ValueError("Anno fiscale CU non rilevato")
    if not cf:
        raise ValueError("Codice fiscale del percipiente non rilevato")
    cf = cf.upper()

    persona_created = False
    if persona_id is not None:
        persona = session.get(Persona, persona_id)
        if persona is None:
            raise ValueError(f"Persona id={persona_id} non trovata")
        if persona.codice_fiscale.upper() != cf:
            raise ValueError("Il codice fiscale della CU non corrisponde alla Persona scelta")
    else:
        persona = session.query(Persona).filter_by(codice_fiscale=cf).first()
        if persona is None:
            person_data = data.get("percipiente", {})
            persona = Persona(
                codice_fiscale=cf,
                nome=person_data.get("nome") or metadata.get("nome", ""),
                cognome=person_data.get("cognome") or metadata.get("cognome", ""),
                data_nascita=_as_date(person_data.get("data_nascita")),
                sesso=person_data.get("sesso"),
                comune_nascita=person_data.get("comune_nascita"),
                provincia_nascita=person_data.get("provincia_nascita"),
            )
            session.add(persona)
            session.flush()
            persona_created = True

    document = document_data
    employer = employer_data
    summary = _summary(data)
    cu = CertificazioneUnica(
        persona_id=persona.id,
        anno_fiscale=int(fiscal_year),
        anno_modello=document.get("anno_modello"),
        numero_modello=document.get("numero_modello", 1),
        codice_fiscale_sostituto=employer.get("codice_fiscale"),
        denominazione_sostituto=employer.get("denominazione"),
        identificativo_dichiarazione=document.get("identificativo_dichiarazione"),
        data_documento=_as_date(document.get("data_documento")),
        nome_file=path.name,
        hash_file=digest,
        payload_json=json.dumps(data, ensure_ascii=False, default=str),
        testo_originale=data.get("raw_text"),
        parser_version=f"fitz-cu/{_IMPORTER_VERSION}",
        stato=data.get("extraction", {}).get("status", "ok"),
        **summary,
    )
    session.add(cu)
    session.commit()
    return cu, persona, persona_created


def import_cus_to_db(
    pdf_paths: list[str | Path],
    session: Session,
) -> list[dict]:
    """Import a batch while isolating errors and returning one result per file."""
    results = []
    for pdf_path in pdf_paths:
        try:
            digest = _sha256(Path(pdf_path))
            duplicate = session.query(CertificazioneUnica).filter_by(hash_file=digest).first() is not None
            cu, persona, created = import_cu_to_db(pdf_path, session)
            results.append({
                "path": str(pdf_path),
                "document": cu,
                "persona": persona,
                "persona_created": created,
                "duplicate": duplicate,
                "error": None,
            })
        except Exception as exc:
            session.rollback()
            results.append({"path": str(pdf_path), "document": None, "error": str(exc)})
    return results


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _as_date(value) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def _point_value(data: dict, code: str, section: str | None = None):
    for module in data.get("moduli", []):
        for current_section, points in module.get("sezioni", {}).items():
            if section is not None and current_section != section:
                continue
            entry = points.get(code)
            if entry and entry.get("valore") is not None:
                return entry["valore"]
    return None


def _sum_points(data: dict, codes: set[str], section: str | None = "lavoro_dipendente") -> float | None:
    values = [_point_value(data, code, section) for code in codes]
    values = [float(value) for value in values if isinstance(value, (int, float))]
    return round(sum(values), 2) if values else None


def _summary(data: dict) -> dict:
    return {
        "reddito_principale": _point_value(data, "1", "lavoro_dipendente"),
        "ritenute_irpef": _point_value(data, "21", "lavoro_dipendente"),
        "addizionale_regionale": _sum_points(data, {"22", "23", "24"}),
        "addizionale_comunale": _sum_points(data, {"25", "26", "27", "28", "29"}),
        "imposta_lorda": _point_value(data, "361"),
        "totale_detrazioni": _point_value(data, "374"),
        "imposta_netta": _point_value(data, "375"),
        "trattamento_integrativo": _sum_points(data, {"391", "398"}, None),
        "benefit": _sum_points(data, {"474", "475"}, None),
    }
