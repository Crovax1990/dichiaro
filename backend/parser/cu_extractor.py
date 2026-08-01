"""Parser for ordinary, text-based Italian Certificazione Unica PDFs."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import fitz

from backend.parser.cu_registry import (
    model_year_from_filename,
    point_definition,
    section_for_text,
)
from backend.parser.normalizer import normalize_value


_RE_CF = re.compile(r"\b[A-Z0-9]{16}\b", re.IGNORECASE)
_RE_ID = re.compile(
    r"Identificativo dichiarazione:\s*([\d]+)\s*-\s*([\d]+)\s+del\s+(\d{1,2}/\d{1,2}/\d{4})",
    re.IGNORECASE,
)
_RE_SUBJECT = re.compile(
    r"Soggetto:\s*(.*?)\s*\(\s*([A-Z0-9]{16})\s*\)", re.IGNORECASE
)
_RE_MODEL = re.compile(r"CERTIFICAZIONE\s*UNICA\s*(\d{4})", re.IGNORECASE)
_RE_FISCAL_YEAR = re.compile(r"RELATIVA\s+ALL[’']ANNO\s+(\d{4})", re.IGNORECASE)
_RE_POINT = re.compile(r"^\d{1,3}$")


def parse_cu(pdf_path: str | Path) -> dict:
    """Extract a structured representation from a text-based CU PDF."""
    path = Path(pdf_path)
    doc = fitz.open(str(path))
    pages = [page.get_text("text") for page in doc]
    full_text = "\n".join(pages)

    model_year = _detect_model_year(full_text, path.name)
    metadata = _extract_metadata(full_text, doc[0] if doc.page_count else None, path.name)
    fiscal_year = _detect_fiscal_year(full_text, model_year)
    metadata.update({"anno": fiscal_year, "anno_fiscale": fiscal_year})
    metadata["anno_modello"] = model_year

    modules: dict[int, dict] = {}
    unmapped: list[dict] = []
    page_sections: list[dict] = []

    for page_number, page in enumerate(doc, start=1):
        section = section_for_text(pages[page_number - 1], page_number)
        page_sections.append({"pagina": page_number, "sezione": section})
        if page_number == 1:
            continue

        anchors = _point_anchors(page)
        values = _value_spans(page)
        assigned: dict[tuple[str, str], list[dict]] = {}

        for value in values:
            point = _point_for_value(value, anchors)
            if point is None:
                unmapped.append(_provenance(value, section, page_number))
                continue
            assigned.setdefault((section, point["code"]), []).append(value)

        for (point_section, code), spans in assigned.items():
            raw = " ".join(span["text"].strip() for span in spans).strip()
            definition = point_definition(code)
            entry = {
                "codice": code,
                "etichetta": definition.label,
                "valore": _normalize_point(raw, definition.kind),
                "raw": raw,
                "tipo": definition.kind,
                "pagina": page_number,
                "bbox": _union_bbox(spans),
            }
            if definition.aggregate:
                entry["aggregabile"] = definition.aggregate
            modules.setdefault(1, {"numero": 1, "sezioni": {}})
            modules[1]["sezioni"].setdefault(point_section, {})[code] = entry

    doc.close()

    result = {
        "schema_version": "cu-1",
        "document": {
            "file_name": path.name,
            "anno_modello": model_year,
            "anno_fiscale": fiscal_year,
            "numero_modello": 1,
            "identificativo_dichiarazione": metadata.get("identificativo_dichiarazione"),
            "data_documento": metadata.get("data_documento"),
        },
        "metadata": metadata,
        "percipiente": metadata.get("percipiente", {}),
        "sostituto": metadata.get("sostituto", {}),
        "moduli": list(modules.values()),
        "unmapped": unmapped,
        "page_sections": page_sections,
        "raw_text": full_text,
        "extraction": {
            "parser": "fitz-cu",
            "ocr_used": False,
            "status": "ok",
            "warnings": [],
        },
    }
    result["validazione"] = _validate(result)
    result["extraction"]["status"] = result["validazione"]["status"]
    result["extraction"]["warnings"].extend(result["validazione"].get("warnings", []))
    return result


# ── Document metadata ───────────────────────────────────────────────


def _detect_model_year(text: str, filename: str) -> int | None:
    match = _RE_MODEL.search(text.replace("\n", " "))
    if match:
        return int(match.group(1))
    return model_year_from_filename(filename)


def _detect_fiscal_year(text: str, model_year: int | None) -> int | None:
    match = _RE_FISCAL_YEAR.search(" ".join(text.split()))
    if match:
        return int(match.group(1))
    return model_year - 1 if model_year else None


def _extract_metadata(text: str, first_page, filename: str) -> dict:
    metadata: dict = {"file_name": filename}
    subject = _RE_SUBJECT.search(text)
    if subject:
        subject_name = " ".join(subject.group(1).split())
        metadata["codice_fiscale"] = subject.group(2).upper()
        parts = subject_name.split()
        metadata["cognome"] = parts[-1].upper() if parts else ""
        metadata["nome"] = parts[0].upper() if len(parts) > 1 else subject_name.upper()

    declaration = _RE_ID.search(text)
    if declaration:
        metadata["identificativo_dichiarazione"] = (
            f"{declaration.group(1)}-{declaration.group(2)}"
        )
        metadata["data_documento"] = _parse_slash_date(declaration.group(3))

    if first_page is not None:
        metadata.update(_frontespizio_metadata(first_page))

    # CU 2025 in the sample has a compact first page without the printed form
    # labels.  Its values retain the same layout, but these fallbacks also work
    # when only the text order is available.
    if not metadata.get("sostituto", {}).get("codice_fiscale"):
        after_id = text.split("Identificativo dichiarazione:", 1)[-1]
        employer_cf = re.search(r"\b\d{11}\b", after_id)
        if employer_cf:
            metadata.setdefault("sostituto", {})["codice_fiscale"] = employer_cf.group(0)
            lines = [line.strip() for line in after_id.splitlines() if line.strip()]
            try:
                metadata["sostituto"]["denominazione"] = lines[lines.index(employer_cf.group(0)) + 1]
            except (ValueError, IndexError):
                pass

    metadata.setdefault("sostituto", {})
    metadata.setdefault("percipiente", {})
    if metadata.get("codice_fiscale"):
        metadata["percipiente"].setdefault("codice_fiscale", metadata["codice_fiscale"])
    if metadata.get("nome"):
        metadata["percipiente"].setdefault("nome", metadata["nome"])
    if metadata.get("cognome"):
        metadata["percipiente"].setdefault("cognome", metadata["cognome"])
    return metadata


def _frontespizio_metadata(page) -> dict:
    """Read the stable two-column front page layout used by CU 2025/2026."""
    spans = _data_spans(page, include_y_before=40)

    def box(x0: float, y0: float, x1: float, y1: float) -> str | None:
        matching = [
            s for s in spans
            if x0 <= s["bbox"][0] < x1 and y0 <= s["bbox"][1] < y1
        ]
        if not matching:
            return None
        return " ".join(s["text"].strip() for s in sorted(matching, key=lambda s: s["bbox"][0]))

    birth = box(140, 325, 230, 360)
    result = {
        "sostituto": {
            "codice_fiscale": box(100, 145, 230, 175),
            "denominazione": box(240, 145, 410, 175),
            "comune": box(100, 180, 190, 215),
            "provincia": box(300, 180, 345, 215),
            "cap": box(340, 180, 390, 215),
            "indirizzo": box(390, 180, 530, 215),
            "email": box(230, 220, 430, 250),
            "codice_attivita": box(450, 220, 530, 250),
        },
        "percipiente": {
            "codice_fiscale": box(100, 290, 240, 320),
            "cognome": box(240, 290, 340, 320),
            "nome": box(390, 290, 490, 320),
            "sesso": box(100, 325, 140, 360),
            "data_nascita": _parse_compact_date(birth),
            "comune_nascita": box(220, 325, 340, 360),
            "provincia_nascita": box(340, 325, 410, 360),
            "comune_residenza": box(100, 365, 320, 395),
            "provincia_residenza": box(410, 365, 465, 395),
            "codice_comune": box(465, 365, 530, 395),
        },
    }
    return _drop_none(result)


# ── Point/value extraction ──────────────────────────────────────────


def _spans(page) -> list[dict]:
    result = []
    for block in page.get_text("dict").get("blocks", []):
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = span.get("text", "").strip()
                if text:
                    result.append({
                        "text": text,
                        "bbox": tuple(span["bbox"]),
                        "size": span.get("size", 0),
                        "font": span.get("font", ""),
                    })
    return result


def _data_spans(page, include_y_before: float = 40) -> list[dict]:
    return [
        span for span in _spans(page)
        if span["font"].startswith("Courier")
        and span["size"] >= 9
        and span["bbox"][1] >= include_y_before
    ]


def _value_spans(page) -> list[dict]:
    return _data_spans(page, include_y_before=40)


def _point_anchors(page) -> list[dict]:
    anchors = []
    for span in _spans(page):
        text = span["text"]
        if (
            span["font"].startswith("Futura")
            and 4.5 <= span["size"] <= 5.5
            and _RE_POINT.fullmatch(text)
            and span["bbox"][1] > 35
        ):
            anchors.append({"code": text, "x": span["bbox"][0], "y": span["bbox"][1]})
    return anchors


def _point_for_value(value: dict, anchors: list[dict]) -> dict | None:
    x0, y0, _, _ = value["bbox"]
    same_row = [anchor for anchor in anchors if abs(anchor["y"] - y0) <= 4]
    same_row.sort(key=lambda anchor: anchor["x"])
    for index, anchor in enumerate(same_row):
        right = same_row[index + 1]["x"] if index + 1 < len(same_row) else 600
        if anchor["x"] - 3 <= x0 < right - 1:
            return anchor
    return None


def _provenance(span: dict, section: str, page_number: int) -> dict:
    return {"sezione": section, "raw": span["text"], "pagina": page_number, "bbox": span["bbox"]}


def _union_bbox(spans: list[dict]) -> list[float]:
    return [
        min(s["bbox"][0] for s in spans),
        min(s["bbox"][1] for s in spans),
        max(s["bbox"][2] for s in spans),
        max(s["bbox"][3] for s in spans),
    ]


# ── Values and validation ───────────────────────────────────────────


def _normalize_point(raw: str, kind: str):
    compact = re.sub(r"\s+", " ", raw).strip()
    if kind == "date":
        return _parse_compact_date(compact) or compact
    if kind == "boolean":
        return compact.upper() in {"X", "SI", "SÌ", "1", "TRUE"}
    if kind in {"money", "integer", "number"}:
        value = normalize_value(compact)
        if kind == "integer" and isinstance(value, float):
            return int(value)
        return value
    return compact


def _parse_compact_date(value: str | None) -> str | None:
    if not value:
        return None
    digits = re.sub(r"\D", "", value)
    if len(digits) != 8:
        return None
    day, month, year = int(digits[:2]), int(digits[2:4]), int(digits[4:])
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def _parse_slash_date(value: str) -> str:
    day, month, year = (int(part) for part in value.split("/"))
    return date(year, month, day).isoformat()


def _all_point_entries(data: dict):
    for module in data.get("moduli", []):
        for section, points in module.get("sezioni", {}).items():
            for code, entry in points.items():
                yield section, code, entry


def _find_point(data: dict, code: str):
    for _, point_code, entry in _all_point_entries(data):
        if point_code == code and entry.get("valore") is not None:
            return entry["valore"]
    return None


def _validate(data: dict) -> dict:
    warnings: list[str] = []
    metadata = data.get("metadata", {})
    if not metadata.get("codice_fiscale"):
        warnings.append("Codice fiscale del percipiente non rilevato")
    if not data.get("document", {}).get("anno_fiscale"):
        warnings.append("Anno fiscale non rilevato")

    imposta_lorda = _find_point(data, "361")
    totale_detrazioni = _find_point(data, "374")
    imposta_netta = _find_point(data, "375")
    check = None
    if all(isinstance(value, (int, float)) for value in (imposta_lorda, totale_detrazioni, imposta_netta)):
        calculated = round(imposta_lorda - totale_detrazioni, 2)
        check = {
            "imposta_lorda": imposta_lorda,
            "totale_detrazioni": totale_detrazioni,
            "imposta_netta_calcolata": calculated,
            "imposta_netta_dichiarata": imposta_netta,
            "ok": abs(calculated - imposta_netta) < 1,
        }
        if not check["ok"]:
            warnings.append("Totali imposta lorda, detrazioni e imposta netta non coerenti")

    if len(data.get("raw_text", "").strip()) < 200:
        return {"status": "ocr_required", "warnings": warnings + ["Testo PDF insufficiente"], "controllo_totali": check}
    status = "invalid" if not metadata.get("codice_fiscale") else ("warning" if warnings else "ok")
    return {"status": status, "warnings": warnings, "controllo_totali": check}


def _drop_none(value):
    if isinstance(value, dict):
        return {key: _drop_none(item) for key, item in value.items() if item is not None}
    if isinstance(value, list):
        return [_drop_none(item) for item in value]
    return value
