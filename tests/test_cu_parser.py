"""Tests for CU extraction and persistence."""

from pathlib import Path

import fitz

from backend.parser.cu_extractor import parse_cu


CU_DIR = Path(__file__).parent.parent / "data" / "CU"


def _point(data: dict, code: str, section: str | None = None):
    for module in data["moduli"]:
        for current_section, points in module["sezioni"].items():
            if section and current_section != section:
                continue
            if code in points:
                return points[code]["valore"]
    return None


def test_parse_cu_2025_relative_to_2024():
    data = parse_cu(next(CU_DIR.glob("CUK_T250*.pdf")))

    assert data["document"]["anno_modello"] == 2025
    assert data["document"]["anno_fiscale"] == 2024
    assert data["metadata"]["codice_fiscale"] == "GBBLCU90L02L117H"
    assert data["sostituto"]["codice_fiscale"] == "00967720285"
    assert data["percipiente"]["data_nascita"] == "1990-07-02"
    assert _point(data, "1", "lavoro_dipendente") == 39043.09
    assert _point(data, "21", "lavoro_dipendente") == 9353.90
    assert data["validazione"]["status"] == "ok"
    assert data["validazione"]["controllo_totali"]["ok"] is True


def test_parse_two_cu_2026_for_same_fiscal_year():
    documents = [parse_cu(path) for path in sorted(CU_DIR.glob("CUK_T260*.pdf"))]

    assert len(documents) == 2
    assert {data["document"]["anno_fiscale"] for data in documents} == {2025}
    assert {data["sostituto"]["codice_fiscale"] for data in documents} == {
        "00967720285",
        "01234830469",
    }
    assert sorted(_point(data, "1", "lavoro_dipendente") for data in documents) == [
        13637.52,
        28713.06,
    ]


def test_cu_values_keep_raw_and_provenance():
    data = parse_cu(next(CU_DIR.glob("CUK_T260312*.pdf")))
    point = next(
        points["1"]
        for module in data["moduli"]
        for section, points in module["sezioni"].items()
        if section == "lavoro_dipendente"
    )

    assert point["valore"] == 28713.06
    assert point["raw"] == "28.713,06"
    assert point["pagina"] == 2
    assert len(point["bbox"]) == 4


def test_short_pdf_is_marked_ocr_required(tmp_path):
    path = tmp_path / "short.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "not enough structured CU text")
    doc.save(path)
    doc.close()

    data = parse_cu(path)
    assert data["extraction"]["status"] == "ocr_required"
    assert data["validazione"]["status"] == "ocr_required"
