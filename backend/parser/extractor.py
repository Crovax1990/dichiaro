"""
Parser for structured textual 730 PDFs.

Format: 3-page PDF where each line follows patterns like:
    Quadro C, Rigo 1, colonna 3 - Reddito:  39043 €
    PL, Rigo 50, colonna 1 - Imposta netta:  9005 €
    Cognome:  GOBBI

Uses a state machine to track current section and regex to extract fields.
"""

from pathlib import Path
import re
import fitz

from backend.parser.normalizer import normalize_value


# ── Regex patterns ──────────────────────────────────────────────────

RE_YEAR = re.compile(r"730\s+(\d{4})")
RE_QUADRO_HEADER = re.compile(r"(Quadro [BCDE])\s*[-–].*")
RE_PL_HEADER = re.compile(r"Prospetto di Liquidazione")
RE_RIGO = re.compile(
    r"(Quadro [BCDE]|PL),\s*Rigo\s*(\d+),\s*colonna\s*(\d+)\s*[-–]\s*(.+?):\s*(.*)"
)
RE_META_LINE = re.compile(r"^(.+?):\s+(.*)$")
RE_CAMPO = re.compile(r"Campo\s+#\w+\s+(?:del record \w+\s*)?:\s*(.*)")
RE_PAGINA = re.compile(r"^Pagina \d+$")

# Lines that start a new section or are metadata markers
SECTION_STARTERS = {
    "Quadro B", "Quadro C", "Quadro D", "Quadro E",
    "Quadro F", "Quadro G", "Quadro K", "Quadro L",
    "Quadro M", "Quadro N", "Quadro T",
    "Prospetto di Liquidazione", "PL,",
    "730 ", "Campo #", "Dati anagrafici",
    "Dati del sostituto",
    "Modello N.", "Codice fiscale",
}

METADATA_KEYS = {
    "codice fiscale del dichiarante": "codice_fiscale",
    "cognome": "cognome",
    "nome": "nome",
    "sesso": "sesso",
    "data di nascita": "data_nascita",
    "comune o stato estero di nascita": "comune_nascita",
    "provincia di nascita": "provincia_nascita",
    "indirizzo e-mail": "email",
    "comune": "comune_residenza",
    "provincia": "provincia_residenza",
    "codice catastale del comune": "codice_catastale",
}

SOSTITUTO_KEYS = {
    "codice fiscale": "sostituto_cf",
    "denominazione": "sostituto_denominazione",
}


# ── Parser ──────────────────────────────────────────────────────────

def parse_730(pdf_path: str | Path) -> dict:
    """Parse a textual 730 PDF and return structured data."""
    doc = fitz.open(str(pdf_path))
    full_text = _get_full_text(doc)
    doc.close()

    lines = _unwrap_lines(full_text.split("\n"))

    result = {
        "metadata": {},
        "quadro_b": [],
        "quadro_c": [],
        "quadro_d": [],
        "quadro_e": [],
        "prospetto_liquidazione": {},
        "validazione": None,
    }

    current_section = "metadata"
    in_sostituto = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Detect year
        if not result["metadata"].get("anno"):
            m = RE_YEAR.search(stripped)
            if m:
                result["metadata"]["anno"] = int(m.group(1))

        # Section headers
        quadro_header = RE_QUADRO_HEADER.match(stripped)
        if quadro_header:
            current_section = _quadro_to_key(quadro_header.group(1))
            continue

        if RE_PL_HEADER.search(stripped):
            current_section = "prospetto_liquidazione"
            continue

        if "Dati del sostituto" in stripped:
            in_sostituto = True
            continue

        # Rigo entries
        rigo_match = RE_RIGO.match(stripped)
        if rigo_match:
            source = rigo_match.group(1)
            rigo = int(rigo_match.group(2))
            colonna = int(rigo_match.group(3))
            descrizione = rigo_match.group(4).strip()
            raw_value = rigo_match.group(5).strip()
            valore = normalize_value(raw_value)

            entry = {
                "rigo": rigo,
                "colonna": colonna,
                "descrizione": descrizione,
                "valore": valore,
                "raw": raw_value,
            }

            if source == "PL" or current_section == "prospetto_liquidazione":
                key = f"rigo_{rigo}_col_{colonna}"
                result["prospetto_liquidazione"][key] = entry
            elif current_section in ("quadro_b", "quadro_c", "quadro_d", "quadro_e"):
                result[current_section].append(entry)
            continue

        # Metadata lines
        if current_section == "metadata":
            # Dati del sostituto sub-section
            if in_sostituto:
                m = RE_META_LINE.match(stripped)
                if m:
                    raw_key = m.group(1).strip().lower().rstrip(":")
                    raw_val = m.group(2).strip()
                    if raw_key in SOSTITUTO_KEYS:
                        result["metadata"][SOSTITUTO_KEYS[raw_key]] = raw_val.rstrip("€").strip()
                    if raw_key not in SOSTITUTO_KEYS and raw_key:
                        in_sostituto = False
                continue

            m = RE_META_LINE.match(stripped)
            if m:
                raw_key = m.group(1).strip().lower()
                raw_val = m.group(2).strip()
                if raw_key in METADATA_KEYS:
                    result["metadata"][METADATA_KEYS[raw_key]] = raw_val
                continue

            campo_m = RE_CAMPO.match(stripped)
            if campo_m:
                continue

            if "Destinazione" in stripped or "Firma" in stripped or "Agenzia Entrate" in stripped:
                continue

    # Cross-validation
    result["validazione"] = _validate(result)

    return result


# ── Helpers ─────────────────────────────────────────────────────────

def _get_full_text(doc) -> str:
    """Extract concatenated text from all pages."""
    parts = []
    for page in doc:
        parts.append(page.get_text("text"))
    return "\n".join(parts)


def _unwrap_lines(lines: list[str]) -> list[str]:
    """
    Join continuation lines (those not starting with a recognized marker)
    to the previous line.
    """
    result = []
    for line in lines:
        stripped = line.strip()
        if not stripped or RE_PAGINA.match(stripped):
            continue

        is_starter = any(
            stripped.startswith(s) or stripped.startswith(s.lower())
            for s in SECTION_STARTERS
        )
        is_rigo = RE_RIGO.match(stripped)
        is_kv = RE_META_LINE.match(stripped)

        if is_starter or is_rigo or is_kv:
            result.append(line)
        elif result:
            result[-1] = result[-1].rstrip() + " " + stripped
        else:
            result.append(line)
    return result


def _quadro_to_key(name: str) -> str:
    """Convert 'Quadro B' to 'quadro_b'."""
    letter = name.split()[-1].lower()
    return f"quadro_{letter}"


def _validate(data: dict) -> dict:
    """Cross-check: Imposta Lorda - Totale Detrazioni == Imposta Netta."""
    pl = data.get("prospetto_liquidazione", {})

    def _get(key_suffix: str):
        for k, v in pl.items():
            if k.endswith(key_suffix) and isinstance(v, dict):
                val = v.get("valore")
                if isinstance(val, (int, float)):
                    return val
        return None

    imposta_lorda = _get("_16_col_1")
    totale_detrazioni = _get("_48_col_1")
    imposta_netta = _get("_50_col_1")

    if imposta_lorda is None or totale_detrazioni is None or imposta_netta is None:
        return {"ok": None, "message": "Dati insufficienti per validazione"}

    calcolata = round(imposta_lorda - totale_detrazioni, 2)
    ok = abs(calcolata - imposta_netta) < 1

    return {
        "ok": ok,
        "imposta_lorda": imposta_lorda,
        "totale_detrazioni": totale_detrazioni,
        "imposta_netta_calcolata": calcolata,
        "imposta_netta_dichiarata": imposta_netta,
    }
