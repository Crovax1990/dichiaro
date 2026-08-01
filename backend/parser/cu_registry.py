"""Versioned metadata for Italian Certificazione Unica PDF fields."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CUPoint:
    label: str
    kind: str = "number"
    aggregate: str | None = None


MODEL_YEARS = {2025, 2026}

# The visual CU keeps the same point codes across many sections.  The section
# is therefore part of the JSON key; these definitions cover the fields used by
# the dashboard and provide useful labels for the remaining extracted points.
POINTS: dict[str, CUPoint] = {
    "1": CUPoint("Redditi di lavoro dipendente e assimilati", "money", "redditi"),
    "2": CUPoint("Redditi di lavoro dipendente a tempo determinato", "money"),
    "3": CUPoint("Redditi di pensione", "money"),
    "4": CUPoint("Altri redditi assimilati", "money"),
    "5": CUPoint("Assegni periodici corrisposti dal coniuge", "money"),
    "6": CUPoint("Giorni per lavoro dipendente", "integer"),
    "7": CUPoint("Giorni per pensione", "integer"),
    "8": CUPoint("Data di inizio rapporto", "date"),
    "9": CUPoint("Data di cessazione rapporto", "date"),
    "10": CUPoint("In forza al 31/12", "boolean"),
    "11": CUPoint("Periodi particolari", "string"),
    "12": CUPoint("Redditi erogati in franchi", "money"),
    "13": CUPoint("Compensi corrisposti agli addetti alle corse ippiche", "money"),
    "21": CUPoint("Ritenute Irpef", "money", "ritenute_irpef"),
    "22": CUPoint("Addizionale regionale all'Irpef", "money", "addizionale_regionale"),
    "23": CUPoint("Addizionale regionale trattenuta nell'anno", "money", "addizionale_regionale"),
    "24": CUPoint("Addizionale regionale rapporti cessati", "money", "addizionale_regionale"),
    "25": CUPoint("Addizionale comunale - saldo", "money", "addizionale_comunale"),
    "26": CUPoint("Addizionale comunale - acconto", "money", "addizionale_comunale"),
    "27": CUPoint("Addizionale comunale - saldo anno corrente", "money", "addizionale_comunale"),
    "28": CUPoint("Addizionale comunale rapporti cessati", "money", "addizionale_comunale"),
    "29": CUPoint("Addizionale comunale - acconto anno successivo", "money", "addizionale_comunale"),
    "30": CUPoint("Ritenute Irpef sospese", "money"),
    "31": CUPoint("Addizionale regionale sospesa", "money"),
    "32": CUPoint("Addizionale regionale sospesa per trattenute", "money"),
    "35": CUPoint("Addizionale comunale sospesa a saldo", "money"),
    "36": CUPoint("Addizionale comunale sospesa in acconto", "money"),
    "61": CUPoint("Saldo Irpef trattenuto", "money"),
    "62": CUPoint("Saldo Irpef rimborsato", "money"),
    "71": CUPoint("Addizionale regionale trattenuta", "money"),
    "72": CUPoint("Addizionale regionale rimborsata", "money"),
    "81": CUPoint("Addizionale comunale trattenuta", "money"),
    "82": CUPoint("Addizionale comunale rimborsata", "money"),
    "361": CUPoint("Imposta lorda", "money"),
    "362": CUPoint("Detrazioni per carichi di famiglia", "money"),
    "367": CUPoint("Detrazioni per lavoro dipendente", "money"),
    "368": CUPoint("Ulteriore detrazione", "money"),
    "369": CUPoint("Totale detrazioni per oneri", "money"),
    "374": CUPoint("Totale detrazioni", "money"),
    "375": CUPoint("Imposta netta", "money"),
    "376": CUPoint("Credito per imposte pagate all'estero", "money"),
    "390": CUPoint("Codice trattamento", "string"),
    "391": CUPoint("Trattamento integrativo erogato", "money", "trattamento_integrativo"),
    "392": CUPoint("Trattamento integrativo non erogato", "money"),
    "397": CUPoint("Codice trattamento", "string"),
    "398": CUPoint("Trattamento integrativo erogato", "money", "trattamento_integrativo"),
    "411": CUPoint("Previdenza complementare", "boolean"),
    "415": CUPoint("Data iscrizione al fondo", "date"),
    "431": CUPoint("Totale oneri deducibili", "money"),
    "438": CUPoint("Somme restituite nell'anno", "money"),
    "449": CUPoint("Reddito di riferimento", "money"),
    "451": CUPoint("Ritenute frontalieri", "money"),
    "474": CUPoint("Benefit base", "money", "benefit"),
    "475": CUPoint("Benefit con figli fiscalmente a carico", "money", "benefit"),
    "481": CUPoint("Totale redditi assoggettati a ritenuta", "money", "redditi"),
    "482": CUPoint("Totale ritenute Irpef", "money", "ritenute_irpef"),
    "483": CUPoint("Totale ritenute Irpef sospese", "money"),
    "493": CUPoint("Data di inizio periodo", "date"),
    "494": CUPoint("Data di cessazione periodo", "date"),
    "511": CUPoint("Compensi arretrati con detrazioni", "money"),
    "512": CUPoint("Compensi arretrati senza detrazioni", "money"),
    "513": CUPoint("Totale ritenute operate", "money", "ritenute_irpef"),
}

# Page headings are used only to name sections in the JSON.  Values are still
# located by point anchors and coordinates, so a page number is not a parser key.
SECTION_HINTS = (
    ("ANNOTAZIONI", "annotazioni"),
    ("TRATTAMENTO DI FINE RAPPORTO", "tfr"),
    ("ONERI DEDUCIBILI", "oneri_deducibili"),
    ("PREVIDENZA COMPLEMENTARE", "previdenza_complementare"),
    ("PREMI DI RISULTATO", "premi_di_risultato"),
    ("TIPOLOGIE REDDITUALI", "tipologie_reddituali"),
    ("ONERI DETRAIBILI", "oneri_detraibili"),
    ("DETRAZIONI", "detrazioni_crediti"),
    ("LAVORO DIPENDENTE", "lavoro_dipendente"),
    ("CONTRIBUTI", "contributi"),
    ("ALTRI DATI", "altri_dati"),
)

AGGREGATE_FIELDS = {
    "redditi": "redditi",
    "ritenute_irpef": "ritenute_irpef",
    "addizionale_regionale": "addizionale_regionale",
    "addizionale_comunale": "addizionale_comunale",
    "trattamento_integrativo": "trattamento_integrativo",
    "benefit": "benefit",
}


def point_definition(code: str) -> CUPoint:
    """Return a known definition or a safe generic one."""
    return POINTS.get(code, CUPoint(f"Punto CU {code}"))


def model_year_from_filename(filename: str) -> int | None:
    """Extract the model year from the common CUK_TYY filename convention."""
    import re

    match = re.search(r"CUK_T(\d{2})", filename.upper())
    return 2000 + int(match.group(1)) if match else None


def section_for_text(text: str, page_number: int) -> str:
    # A page can mention later sections in its footer.  Use the first major
    # heading, which corresponds to the visual section currently being read.
    upper = " ".join(text.upper().split())
    matches = [(upper.index(hint), section) for hint, section in SECTION_HINTS if hint in upper]
    if matches:
        return min(matches)[1]
    return "frontespizio" if page_number == 1 else f"pagina_{page_number}"
