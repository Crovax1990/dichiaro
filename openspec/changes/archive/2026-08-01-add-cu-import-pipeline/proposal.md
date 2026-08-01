## Why

Dichiaro oggi importa i 730 ma non le Certificazioni Uniche (CU), impedendo di ricostruire tutti i redditi della stessa persona quando esistono più sostituti d’imposta nello stesso anno. I PDF CU presenti in `data/CU/` sono testuali e mostrano già il caso reale di due CU per il 2025: serve una pipeline specifica che conservi ogni certificazione autonomamente e produca un riepilogo annuale confrontabile con il 730.

## What Changes

- Aggiungere il parsing dei PDF CU ordinari testuali con PyMuPDF.
- Rilevare modello, anno fiscale, percipiente, sostituto d’imposta, numero modulo e dati dei punti CU.
- Conservare tutti i dati estratti in un JSON versionato con valore normalizzato, valore originale, etichetta, pagina e warning.
- Aggiungere l’entità database `CertificazioneUnica`, separata da `Dichiarazione`, senza unicità sull’anno fiscale.
- Rendere l’importazione idempotente tramite hash del file e identificativo della certificazione.
- Supportare più CU per persona e anno, inclusi più sostituti d’imposta.
- Aggregare redditi, ritenute e addizionali CU nel riepilogo annuale senza fondere le CU sorgenti.
- Confrontare i totali CU con i dati del Quadro C del 730.
- Aggiungere anteprima, warning sui duplicati e importazione multipla nell’interfaccia.
- Aggiungere un registry versionato per le differenze tra CU 2025, CU 2026 e versioni future.
- Aggiungere test sui tre PDF CU disponibili e sui casi di più CU nello stesso anno.

## Capabilities

### New Capabilities

- `cu-import`: estrazione, validazione, persistenza e importazione idempotente delle Certificazioni Uniche PDF.
- `cu-annual-integration`: aggregazione annuale delle CU e confronto con le dichiarazioni 730 senza perdere la provenienza dei documenti.

### Modified Capabilities

<!-- Nessuna specifica esistente in openspec/specs/ viene modificata. -->

## Impact

- Nuovi moduli in `backend/parser/` per estrazione, registry e import CU.
- Nuovi modelli e relazioni in `backend/models/__init__.py`.
- Aggiornamenti a `frontend/app.py` per upload, anteprima e riepilogo CU.
- Nuovi test in `tests/` e fixture basate sui PDF presenti in `data/CU/`.
- Nessuna nuova dipendenza necessaria per i PDF testuali; l’OCR resta fuori scope finché non saranno presenti CU scansionate.
- Il database SQLite esistente dovrà accettare lo schema CU senza introdurre vincoli che impediscano più documenti per anno.
