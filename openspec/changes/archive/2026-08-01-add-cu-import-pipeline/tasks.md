## 1. Contratto dati e registry CU

- [x] 1.1 Definire lo schema JSON versionato della CU con documento, percipiente, sostituto, moduli, punti, `unmapped` ed estrazione.
- [x] 1.2 Creare `backend/parser/cu_registry.py` con sezioni, codici punto, etichette e tipi per CU 2025 e CU 2026.
- [x] 1.3 Definire quali punti sono aggregabili nel riepilogo annuale e quali restano disponibili solo a livello di documento.

## 2. Parser PDF CU

- [x] 2.1 Creare `backend/parser/cu_extractor.py` con API `parse_cu(pdf_path)` e lettura PyMuPDF del testo e delle coordinate.
- [x] 2.2 Implementare il riconoscimento di modello, anno fiscale, numero modulo, identificativo dichiarazione, percipiente e sostituto.
- [x] 2.3 Implementare l’associazione dei valori ai codici punto usando sezioni, parole e coordinate invece di numeri di pagina fissi.
- [x] 2.4 Riutilizzare il normalizzatore esistente per importi italiani e aggiungere la gestione di date, flag, codici e valori raw.
- [x] 2.5 Conservare punti e testo non riconosciuti in `unmapped` e produrre stato, warning e metadati di provenienza.
- [x] 2.6 Implementare la validazione dei dati identificativi e dei totali fiscali disponibili, inclusa la relazione imposta lorda/detrazioni/imposta netta.
- [x] 2.7 Segnalare `ocr_required` quando il testo estratto è insufficiente senza introdurre OCR nella prima versione.

## 3. Modello e persistenza

- [x] 3.1 Aggiungere il modello SQLAlchemy `CertificazioneUnica` collegato a `Persona` con anno fiscale, anno modello, sostituto, identificativo, file, hash, payload e stato.
- [x] 3.2 Aggiungere indici e vincoli di deduplicazione basati su hash e identificativo senza imporre unicità su persona e anno fiscale.
- [x] 3.3 Verificare la creazione delle nuove tabelle con SQLite e la compatibilità con i dati 730 già presenti.
- [x] 3.4 Aggiungere una procedura minima di upgrade del database esistente per creare le tabelle CU senza alterare le tabelle 730.

## 4. Importer e idempotenza

- [x] 4.1 Creare `backend/parser/cu_importer.py` con importazione di una CU e restituzione di documento, persona e stato.
- [x] 4.2 Creare o riutilizzare la Persona dal codice fiscale della CU e validare i dati obbligatori prima del commit.
- [x] 4.3 Implementare deduplicazione per hash del file e identificativo/sostituto/modulo e rendere il reimport non distruttivo.
- [x] 4.4 Aggiungere importazione batch delle CU con risultati individuali, warning e errori isolati per file.

## 5. Test del parsing e dell’importazione

- [x] 5.1 Aggiungere test di parsing per la CU 2025 relativa al 2024 presente in `data/CU/`.
- [x] 5.2 Aggiungere test di parsing per entrambe le CU 2026 relative al 2025 e verificare sostituti, redditi e anno fiscale.
- [x] 5.3 Aggiungere test per numeri italiani, date, codici stringa, flag e conservazione dei valori raw.
- [x] 5.4 Aggiungere test per punti non mappati, warning e testo insufficiente.
- [x] 5.5 Aggiungere test database per più CU della stessa persona e anno, reimport idempotente e Persona creata automaticamente.

## 6. Riepilogo e integrazione con il 730

- [x] 6.1 Implementare un servizio di riepilogo che raggruppi le CU per persona e anno fiscale e calcoli solo metriche aggregabili.
- [x] 6.2 Restituire dal riepilogo numero CU, sostituti, dettaglio per documento e totali di redditi, ritenute e addizionali.
- [x] 6.3 Implementare il confronto tra totale CU e dati del Quadro C del 730 con tolleranza, differenza e stato.
- [x] 6.4 Verificare che aggregazione e confronto non modifichino payload CU, dichiarazioni 730 o quadri esistenti.
- [x] 6.5 Aggiungere test sul caso reale di due CU 2025 e sul caso CU senza 730 corrispondente.

## 7. Interfaccia e verifica finale

- [x] 7.1 Aggiornare l’upload frontend per distinguere automaticamente PDF 730 e PDF CU.
- [x] 7.2 Aggiungere anteprima CU con anno fiscale, percipiente, sostituto, reddito principale, warning e stato duplicato.
- [x] 7.3 Permettere la conferma multipla di CU dello stesso anno mantenendo una riga per documento.
- [x] 7.4 Aggiungere nel riepilogo annuale il conteggio CU, i sostituti, i totali aggregati e il confronto con il 730.
- [x] 7.5 Eseguire `uv run pytest` e una prova end-to-end sui tre PDF in `data/CU/`, verificando due documenti distinti per il 2025.
