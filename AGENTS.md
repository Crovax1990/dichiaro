# AGENTS.md — Dichiaro

Dashboard per gestire e analizzare dichiarazioni 730. Stack: Python 3.12+, Streamlit, SQLAlchemy 2.0 + SQLite, PyMuPDF, Plotly.

## Struttura

```
backend/
  models/__init__.py    # SQLAlchemy models (Persona, Dichiarazione, Quadri A-E, Risultato)
  parser/
    extractor.py        # PDF → dict (PyMuPDF + state machine + regex)
    importer.py         # dict → DB (auto-detect anno, CF, persona)
    normalizer.py       # Italian number/string parsing
    registry.py         # Supported years list
  alert/                # (WIP) alert logic
frontend/
  app.py                # Streamlit dashboard (4 pages: import, riepilogo, trend, alert)
scripts/
  reset_and_reimport.py # Drop DB, reimport all PDFs from data/
tests/
  test_parser.py        # Parser integration tests
  test_models.py        # ORM / schema tests
data/                   # PDF 730 (gitignored)
```

## Flusso PDF Import

1. `extractor.parse_730(path)` → `dict` con `metadata`, `quadro_b/c/d/e`, `prospetto_liquidazione`, `validazione`
2. `importer.import_pdf_to_db(path, session)` → auto-rileva anno, CF, nome, cognome dal PDF; crea Persona se CF non esiste; salva tutto
3. Il frontend accetta upload multipli (`accept_multiple_files=True`), analizza in blocco, mostra preview, conferma e salva

## Formato PDF supportato

PDF testuali strutturati dell'Agenzia delle Entrate (file con suffisso `Testuale`). Il parser usa uno state machine:
- `RE_QUADRO_HEADER` identifica sezione (B, C, D, E)
- `RE_RIGO` estrae rigo, colonna, descrizione, valore
- `RE_META_LINE` estrae metadati anagrafici

## Naming convention file PDF

`DichiarazioneTestuale{ANNO}_{CODICEFISCALE}_{progressivo}.pdf`

Es: `DichiarazioneTestuale2025_RSSMRA80A01H501U_25061433554397977.pdf`

## Comandi

```bash
uv sync                          # Installa dipendenze
PYTHONPATH=. uv run streamlit run frontend/app.py   # Avvia app
uv run pytest                    # Test
uv run python scripts/reset_and_reimport.py         # Reimporta tutto
```

## Aggiungere un nuovo quadro

1. Aggiungere modello in `backend/models/__init__.py`
2. Aggiungere relazione in `Dichiarazione`
3. Aggiungere parsing in `extractor.py` (nuova sezione nella state machine)
4. Aggiungere import in `importer.py`
5. Aggiungere visualizzazione in `frontend/app.py`

## Pattern

- **Session management**: `create_engine_session(db_path)` restituisce `(engine, SessionLocal)`, chiamato una volta a inizio app e chiuso a fine
- **Validazione**: cross-check `Imposta Lorda - Totale Detrazioni == Imposta Netta` con tolleranza 1€
- **Numero italiano**: `normalizer.normalize_value()` gestisce `1.234,56` → `1234.56`
- **Ponytail**: codice morto cancellato (`number_parser.py`), helper one-liner inlinati, `_get_full_text` tenuto per chiarezza
