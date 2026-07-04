# 🏛️ Dichiaro

> **Il tuo 730 non è solo una scadenza. È una storia fiscale che merita di essere capita.**

Ogni anno scarichi il PDF dall'Agenzia delle Entrate e lo archivi in una cartella. Poi quando ti serve confrontare due anni, apri 9 PDF, cerchi i numeri a mano, fai i conti su un foglio Excel. **Dichiaro trasforma quel mucchio di PDF in una dashboard interattiva in 30 secondi.**

---

## ✨ Cosa fa

|     |     |
|-----|-----|
| 📤 **Importa in blocco** | Carica tutti i PDF insieme. Anno, CF, nome e cognome vengono rilevati automaticamente. La persona viene creata in anagrafica se non esiste. |
| 📊 **Riepilogo Annuale** | Reddito, imposta netta, aliquota effettiva, esito (credito/debito), dettaglio immobili, composizione oneri detraibili. |
| 📈 **Trend interannuali** | Evoluzione di reddito, imposte, ritenute e aliquota. Bar chart degli oneri per macrocategoria. Differenza anno su anno con variazioni %. |
| 🔮 **Proiezioni future** | Stima credito/debito per i prossimi 10 anni basata su detrazioni edilizie multi-rate in corso (E41, E42, E43, E61). |
| 🔔 **Alert automatici** | Rileva cali anomali di reddito, detrazioni mancanti rispetto all'anno precedente, variazioni sospette oltre soglia configurabile. |

---

## 🚀 Prova in 30 secondi

```bash
git clone git@github.com:Crovax1990/dichiaro.git
cd dichiaro

# Installa dipendenze
uv sync

# Avvia
PYTHONPATH=. uv run streamlit run frontend/app.py
```

Apri `http://localhost:8501`, carica i tuoi PDF 730 nella sezione **Importa PDF**, clicca **Analizza tutti** e poi **Conferma e Salva**. Fine.

### Docker

```bash
docker compose up
```

---

## 🧠 Come funziona

```
PDF 730 (Agenzia Entrate)
        │
        ▼
┌───────────────────┐
│  extractor.py     │  PyMuPDF (fitz) + state machine + regex
│  parse_730()      │  riconosce Quadri B/C/E, Prospetto Liquidazione
└──────┬────────────┘
       │ dict {metadata, quadri, prospetto_liquidazione, validazione}
       ▼
┌───────────────────┐
│  importer.py      │  auto-detect anno e CF → crea Persona se nuovo
│  import_pdf_to_db │  popola Dichiarazione, Quadri, Risultato
└──────┬────────────┘
       │
       ▼
┌───────────────────┐
│  SQLite +         │  Persona, Dichiarazione, QuadroB/C/E, Risultato
│  SQLAlchemy 2.0   │  validazione: Imposta Lorda - Detrazioni == Imposta Netta
└──────┬────────────┘
       │
       ▼
┌───────────────────┐
│  Streamlit        │  Dashboard: Importa, Riepilogo, Trend, Alert
│  + Plotly         │  Multi-upload con preview e bulk confirm
└───────────────────┘
```

### Il parser

Il formato dei PDF 730 dell'Agenzia delle Entrate è testuale strutturato. Ogni riga segue pattern riconoscibili:

```
Quadro C, Rigo 1, colonna 3 - Reddito:  39043 €
PL, Rigo 50, colonna 1 - Imposta netta:  9005 €
Cognome:  ROSSI
```

Il parser usa una **state machine** per tracciare la sezione corrente (metadata, quadro_b, prospetto_liquidazione, etc.), regex per estrarre i campi, e un validatore incrociato che verifica la coerenza dei totali.

### Anni supportati

Dal **2017 al 2025**. I PDF devono essere nel formato testuale strutturato — tipicamente i file con suffisso `Testuale` scaricabili dal sito dell'Agenzia delle Entrate.

---

## 🛠️ Stack

| Layer | Tecnologia |
|-------|-----------|
| UI | Streamlit + Plotly |
| ORM | SQLAlchemy 2.0 |
| Database | SQLite (locale, zero configurazione) |
| Parsing PDF | PyMuPDF (fitz) |
| Validazione | Cross-check Imposta Lorda - Detrazioni |
| Python | 3.12+ |

---

## 🤝 Contribuire

Hai un'idea? Trovi un bug nel parsing di un quadro specifico? Vuoi aggiungere il supporto per RedditiPF o 730 precompilato?

1. **Forka** il repo
2. **Crea un branch** (`git checkout -b feat/quadro-f`)
3. **Segui la struttura**: parser in `backend/parser/`, modelli in `backend/models/`, UI in `frontend/app.py`
4. **Testa** con `uv run pytest`
5. **Apri una PR** descrivendo cosa hai aggiunto e perché

Leggi [`AGENTS.md`](AGENTS.md) per la documentazione interna dell'architettura e delle convenzioni.

### Cosa manca

- [ ] Quadro D (altri redditi) e Quadro F (fabbricati con canone)
- [ ] Supporto 730 precompilato (formato diverso)
- [ ] Export CSV/PDF del riepilogo
- [ ] Multi-utenza con autenticazione
- [ ] Grafico waterfall del calcolo IRPEF

---

## 📄 Licenza

MIT — usalo, modificalo, contribuisci. L'unica cosa che non puoi fare è incolpare me se l'Agenzia delle Entrate ti manda un accertamento. 😄
