# Dichiaro

Dashboard per gestire e analizzare le tue dichiarazioni 730. Importa i PDF, visualizza trend e ricevi alert automatici.

## Cosa fa

- **Importa** i PDF del 730/RedditiPF scaricati dal sito dell'Agenzia delle Entrate — upload multiplo, anno e persona rilevati automaticamente
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

1. Vai su **Importa PDF** e carica uno o più PDF del 730
2. Clicca **Analizza tutti** — anno e persona (CF, nome, cognome) vengono rilevati automaticamente dal PDF
3. Se il CF non esiste già in anagrafica, la persona viene creata automaticamente
4. Verifica il riepilogo e clicca **Conferma e Salva tutti**
5. Esplora **Riepilogo Annuale** e **Trend** per l'analisi
6. Controlla la sezione **Alert** per eventuali anomalie

## Anni supportati

Il parser testuale supporta tutti gli anni dal 2017 al 2025. I PDF devono essere nel formato testuale strutturato (file con suffisso `Testuale` nella cartella `data/`).

Lo stack tecnico: Python 3.12+, Streamlit, SQLAlchemy 2.0 + SQLite, PyMuPDF, Plotly, Docker.
