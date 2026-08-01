## ADDED Requirements

### Requirement: Il sistema deve riconoscere e identificare una CU PDF

Il sistema SHALL riconoscere una Certificazione Unica ordinaria testuale e SHALL estrarre almeno anno modello, anno fiscale, codice fiscale del percipiente, dati anagrafici, codice fiscale e denominazione del sostituto, identificativo della dichiarazione, data del documento e numero del modulo.

#### Scenario: Riconoscimento della CU relativa al 2024
- **WHEN** l’utente analizza `CUK_T250312122938164960007164_GBBLCU90L02L117H.pdf`
- **THEN** il sistema identifica il documento come CU modello 2025 relativa all’anno fiscale 2024 e associa percipiente e sostituto presenti nel PDF

#### Scenario: Riconoscimento della CU relativa al 2025
- **WHEN** l’utente analizza una delle due CU modello 2026 presenti in `data/CU/`
- **THEN** il sistema identifica l’anno fiscale 2025 senza confonderlo con l’anno di emissione o con la data del documento

### Requirement: Il sistema deve estrarre i punti CU in un JSON canonico

Il sistema SHALL produrre un JSON versionato che conservi i punti riconosciuti per modulo e sezione. Ogni valore SHALL includere, quando disponibile, codice punto, etichetta, valore normalizzato, valore originale, tipo dato, pagina e coordinate del PDF.

#### Scenario: Estrazione dei dati fiscali principali
- **WHEN** una CU contiene reddito, giorni, ritenute, detrazioni e imposta netta
- **THEN** il JSON conserva i punti corrispondenti con numeri italiani convertiti in numeri JSON e con il testo originale ancora disponibile

#### Scenario: Conservazione dei dati non mappati
- **WHEN** il parser incontra un testo o un punto non ancora definito dal registry annuale
- **THEN** il sistema conserva il contenuto in `unmapped` e nel testo originale senza interrompere l’estrazione degli altri punti

### Requirement: Il parser deve normalizzare i tipi senza perdere i valori raw

Il sistema SHALL convertire importi italiani, interi, date, codici e flag in tipi strutturati appropriati e SHALL conservare il valore raw per ogni campo estratto.

#### Scenario: Normalizzazione di un importo italiano
- **WHEN** il PDF contiene `28.713,06`
- **THEN** il valore normalizzato è `28713.06` e il valore raw resta `28.713,06`

#### Scenario: Normalizzazione di un codice
- **WHEN** il PDF contiene un codice fiscale, CAP o codice comune con zeri iniziali
- **THEN** il codice viene conservato come stringa e non convertito in numero

### Requirement: Il sistema deve validare l’estrazione senza perdere documenti parziali

Il sistema SHALL produrre stato, warning e messaggi di validazione per ogni documento. Quando i punti necessari sono presenti, SHALL controllare la coerenza tra imposta lorda, detrazioni e imposta netta; un warning o errore di validazione SHALL conservare comunque il payload estratto.

#### Scenario: Validazione positiva dei totali
- **WHEN** una CU contiene imposta lorda, totale detrazioni e imposta netta coerenti entro la tolleranza prevista
- **THEN** il documento viene marcato valido e il risultato della validazione viene incluso nel JSON

#### Scenario: Testo insufficiente per il parsing
- **WHEN** un PDF non contiene testo sufficiente per l’estrazione testuale
- **THEN** il documento viene marcato `ocr_required` o con errore esplicito e non viene trattato come CU vuota valida

### Requirement: Il sistema deve importare ogni CU come documento autonomo

Il sistema SHALL salvare ogni PDF CU in un’entità dedicata collegata alla Persona e SHALL permettere più documenti per la stessa persona e lo stesso anno fiscale. L’importazione SHALL essere idempotente per lo stesso file e identificativo della certificazione.

#### Scenario: Due CU per lo stesso anno
- **WHEN** vengono importate le CU 2025 di Engineering e Tagetik per la stessa persona
- **THEN** il database contiene due documenti CU distinti con lo stesso anno fiscale e sostituti differenti

#### Scenario: Reimportazione dello stesso file
- **WHEN** lo stesso PDF viene importato una seconda volta
- **THEN** il sistema non crea una seconda riga equivalente e restituisce lo stato di documento già importato

#### Scenario: Persona non ancora presente
- **WHEN** il codice fiscale della CU non esiste in `Persona`
- **THEN** il sistema crea la Persona dai dati anagrafici della CU prima di salvare il documento
