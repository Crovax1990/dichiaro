# dichiarazione730-analyzer

Dashboard locale per gestire e analizzare le dichiarazioni 730 della tua famiglia.

## Cosa fa

- **Importa** i PDF del 730/RedditiPF scaricati dal sito dell'Agenzia delle Entrate
- **Archivia** i dati fiscali anno per anno in un database locale SQLite
- **Visualizza** trend interannuali: reddito, imposte, detrazioni, credito/debito
- **Alert** automatici su detrazioni mancanti, cali anomali, variazioni sospette

## Avvio rapido

```bash
cd dichiarazione730-analyzer

# Installa dipendenze (solo la prima volta)
uv sync

# Avvia l'applicazione
PYTHONPATH=. uv run streamlit run frontend/app.py

# Apri il browser
open http://localhost:8501
```

## Setup Docker

```bash
docker compose up
```

## Utilizzo

1. **Crea una persona** dalla sidebar (te stesso)
2. **Importa un PDF 730** nella sezione "Importa PDF"
3. Verifica i dati estratti e clicca "Conferma e Salva"
4. Esplora **Riepilogo Annuale** e **Trend** per l'analisi
5. Controlla la sezione **Alert** per eventuali anomalie

## Anni supportati

Il parser testuale supporta tutti gli anni dal 2017 al 2025. I PDF devono essere nel formato testuale strutturato (file con suffisso `Testuale` nella cartella `data/`).

Lo stack tecnico: Python 3.12+, Streamlit, SQLAlchemy 2.0 + SQLite, PyMuPDF, Plotly, Docker.
