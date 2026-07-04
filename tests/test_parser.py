"""Tests for the textual 730 parser."""

import tempfile
import os
from pathlib import Path

from backend.parser.normalizer import normalize_value, _parse_number
from backend.parser.extractor import parse_730, _unwrap_lines, _validate
from backend.parser.importer import import_pdf_to_db


# ── Normalizer ──────────────────────────────────────────────────────

def test_normalize_euro_value():
    assert normalize_value("39043 €") == 39043
    assert normalize_value("  9005 €") == 9005
    assert normalize_value("-349 €") == -349


def test_normalize_percent():
    assert normalize_value("100 %") == 100
    assert normalize_value("50 %") == 50


def test_normalize_italian_number():
    assert normalize_value("39.043") == 39043
    assert normalize_value("21.570,50") == 21570.50


def test_normalize_string():
    assert normalize_value("B507") == "B507"
    assert normalize_value("00967720285") == "00967720285"


def test_normalize_date_string():
    assert normalize_value("02071990") == "02071990"


def test_normalize_none_and_empty():
    assert normalize_value(None) is None
    assert normalize_value("") is None
    assert normalize_value("  ") is None


# ── Parser integration ──────────────────────────────────────────────

def test_parse_2025_pdf():
    pdf_path = Path(__file__).parent.parent.parent / "data" / "DichiarazioneTestuale2025_GBBLCU90L02L117H_25061433554397977.pdf"
    if not pdf_path.exists():
        pdf_path = Path("/home/crovax/workspace/draiver-730/data/DichiarazioneTestuale2025_GBBLCU90L02L117H_25061433554397977.pdf")

    if not pdf_path.exists():
        return  # skip if file not found

    result = parse_730(str(pdf_path))

    assert result["metadata"]["anno"] == 2025
    assert result["metadata"]["codice_fiscale"] == "GBBLCU90L02L117H"
    assert result["metadata"]["cognome"] == "GOBBI"
    assert result["metadata"]["nome"] == "LUCA"

    assert len(result["quadro_c"]) > 0
    assert len(result["quadro_e"]) > 0
    assert len(result["quadro_b"]) > 0

    pl = result["prospetto_liquidazione"]
    assert _pl_val(pl, "50_col_1") == 9005
    assert _pl_val(pl, "59_col_1") == 9354
    assert _pl_val(pl, "60_col_1") == -349

    validation = result["validazione"]
    assert validation["ok"] is True


def test_parse_all_years():
    data_dir = Path("/home/crovax/workspace/draiver-730/data")
    if not data_dir.exists():
        return

    for pdf_path in sorted(data_dir.glob("DichiarazioneTestuale*.pdf")):
        result = parse_730(str(pdf_path))
        assert result["metadata"]["anno"] is not None
        assert result["metadata"]["codice_fiscale"] is not None
        # At minimum, PL should have some entries
        assert len(result["prospetto_liquidazione"]) > 0


# ── Unwrap lines ────────────────────────────────────────────────────

def test_unwrap_continuation():
    lines = [
        "Quadro C, Rigo 1, colonna 3 - Reddito:  39043 €",
        "continuation line",
        "Quadro E, Rigo 1, colonna 2 - Importo:  480 €",
    ]
    result = _unwrap_lines(lines)
    assert len(result) == 2
    assert "continuation line" in result[0]


# ── Validation ──────────────────────────────────────────────────────

def test_validation_pass():
    data = {
        "prospetto_liquidazione": {
            "rigo_16_col_1": {"descrizione": "Imposta lorda", "valore": 10305},
            "rigo_48_col_1": {"descrizione": "Totale detrazioni", "valore": 1300},
            "rigo_50_col_1": {"descrizione": "Imposta netta", "valore": 9005},
        }
    }
    v = _validate(data)
    assert v["ok"] is True


def test_validation_fail():
    data = {
        "prospetto_liquidazione": {
            "rigo_16_col_1": {"descrizione": "Imposta lorda", "valore": 10305},
            "rigo_48_col_1": {"descrizione": "Totale detrazioni", "valore": 1300},
            "rigo_50_col_1": {"descrizione": "Imposta netta", "valore": 9100},
        }
    }
    v = _validate(data)
    assert v["ok"] is False


# ── Helpers ─────────────────────────────────────────────────────────

def _pl_val(pl: dict, suffix: str):
    for k, v in pl.items():
        if k.endswith(suffix) and isinstance(v, dict):
            return v.get("valore")
    return None
