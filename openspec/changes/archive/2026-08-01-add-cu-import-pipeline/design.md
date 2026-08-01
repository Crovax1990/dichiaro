## Context

Dichiaro oggi tratta i PDF 730 testuali in `backend/parser/` e persiste i dati in modelli SQLAlchemy su SQLite. Le CU presenti in `data/CU/` sono PDF ordinari testuali di 11 pagine: una CU riguarda il 2024 e due CU riguardano il 2025 della stessa persona, emesse da sostituti diversi. La CU 2026 certifica quindi l’anno fiscale 2025; l’anno del modello e l’anno fiscale devono restare distinti.

La CU non è una dichiarazione 730 e non deve essere rappresentata come un nuovo `Dichiarazione`: è una fonte autonoma di reddito, potenzialmente multipla per persona e anno. Il modello PDF usa codici di punto (ad esempio 1, 6, 21, 361, 374, 375), mentre l’ordine del testo estratto da PDF separa spesso etichette e valori.

## Goals / Non-Goals

**Goals:**

- Estrarre CU ordinarie testuali con PyMuPDF senza introdurre OCR.
- Riconoscere anno fiscale, anno modello, percipiente, sostituto, identificativo dichiarazione, modulo e punti valorizzati.
- Conservare tutti i dati in un payload JSON versionato, mantenendo valore raw, valore normalizzato, etichetta e provenienza.
- Salvare ogni PDF come documento indipendente e permettere più documenti per persona e anno.
- Rendere l’importazione idempotente e diagnosticabile.
- Esporre un riepilogo annuale aggregato e un confronto con il Quadro C del 730.
- Isolare le differenze tra versioni CU tramite un registry per anno/modello.

**Non-Goals:**

- Parsing di CU scansionate o OCR nella prima versione.
- Supporto iniziale a ogni variante della CU (annullamento, sostitutiva, lavoro autonomo, locazioni brevi) oltre alla conservazione dei dati non mappati.
- Calcolo fiscale sostitutivo del 730.
- Fusione automatica delle CU nel modello `QuadroC_Lavoro`.
- Vincoli di unicità basati soltanto su persona e anno fiscale.

## Decisions

### 1. Entità dedicata per il documento CU

Aggiungere `CertificazioneUnica` collegata a `Persona`, con campi relazionali per identificazione e riepilogo e campi testuali per `payload_json`, testo originale, hash, versione parser e stato. Non usare `Dichiarazione.tipo="CU"` come modello principale: i quadri del 730 non rappresentano tutte le sezioni CU.

La chiave di deduplicazione sarà composta da hash del file e, quando disponibile, identificativo dichiarazione, sostituto e numero modulo. Non esisterà una chiave unica su `persona_id + anno_fiscale`.

### 2. JSON canonico più colonne essenziali

Il JSON sarà la rappresentazione completa e versionata dell’estrazione. Ogni punto valorizzato conterrà codice, etichetta, valore normalizzato, valore raw, tipo, pagina e coordinate quando disponibili. Le colonne relazionali conserveranno almeno persona, anno fiscale, anno modello, sostituto, identificativo, nome file, hash e stato, così i riepiloghi non dovranno interrogare ogni volta il JSON.

I campi vuoti non saranno inventati: saranno assenti dai punti valorizzati, mentre il registry manterrà la definizione dei punti noti. Testo o punti non riconosciuti resteranno in una sezione `unmapped` e nel testo originale.

### 3. Parsing per codici punto e coordinate, non per pagina fissa

Il parser userà `page.get_text("words")`/`page.get_text("dict")`, sezioni riconosciute e coordinate per associare valori alle etichette. I numeri dei punti e il contesto della sezione saranno la chiave logica. I numeri di pagina saranno solo metadati di provenienza, perché la disposizione può variare tra anni.

Il registry conterrà le definizioni per CU 2025 e CU 2026 e sarà estendibile per modelli futuri. L’anno fiscale sarà estratto dal contenuto/registry quando possibile, con il nome file solo come fallback segnalato da warning.

### 4. Importazione separata dall’aggregazione

`parse_cu()` produrrà un dizionario JSON senza effetti sul database. Un importer distinto creerà la persona se necessario, controllerà duplicati, salverà il documento e manterrà errori e warning. Un servizio di riepilogo raggrupperà le CU per persona e anno fiscale senza modificare o cancellare le righe sorgenti.

Il riepilogo annuale sommerà solo campi compatibili, come redditi, ritenute e addizionali, e mostrerà numero CU e sostituti. Le CU saranno confrontate con il 730 come fonti diverse; non saranno automaticamente trasformate in righe Quadro C.

### 5. Validazione conservativa

Saranno validati codice fiscale, anno, numeri italiani, date e coerenza dei totali disponibili, inclusa la relazione tra imposta lorda, detrazioni e imposta netta quando i punti sono presenti. Un errore di un campo non farà perdere il documento completo: l’importazione potrà risultare `warning` o `invalid` con motivazione e payload conservato.

### 6. Nessuna nuova dipendenza per la prima versione

I PDF disponibili hanno testo selezionabile e PyMuPDF è già una dipendenza. L’OCR sarà escluso dal percorso principale e il parser segnalerà `ocr_required` solo quando il testo estratto sarà insufficiente.

## Risks / Trade-offs

- **[Rischio]** L’ordine del testo PDF non corrisponde sempre all’ordine visivo dei campi. → **Mitigazione:** usare parole, coordinate, codici punto, sezioni e test sui PDF reali; conservare raw e coordinate.
- **[Rischio]** I punti e le sezioni cambiano tra modelli annuali. → **Mitigazione:** registry versionato per anno/modello e punti sconosciuti conservati senza scartarli.
- **[Rischio]** Più CU possono contenere conguagli o valori non sommabili. → **Mitigazione:** aggregare solo metriche dichiarate aggregabili e mantenere sempre il dettaglio per documento/sostituto.
- **[Rischio]** SQLite esistente non ha migrazioni formali. → **Mitigazione:** aggiungere modelli con `create_all` per installazioni nuove e una migrazione/upgrade esplicita per database esistenti prima dell’import.
- **[Rischio]** Il riconoscimento del modello dal testo può fallire su intestazioni grafiche. → **Mitigazione:** usare contenuto dei punti, intestazione disponibile, nome file come fallback e warning esplicito.
- **[Trade-off]** Il JSON completo è meno efficiente delle colonne per query arbitrarie. → **Mitigazione:** estrarre in colonne solo identificativi e metriche annuali; non introdurre una tabella generica per ogni punto finché non serve.

## Migration Plan

1. Aggiungere modello e tabelle CU senza alterare le righe 730 esistenti.
2. Creare le nuove tabelle sul database locale e verificare che i dati preesistenti siano leggibili.
3. Eseguire un’importazione in preview dei tre PDF presenti.
4. Confermare l’importazione e verificare che esistano due documenti distinti per il 2025.
5. Attivare il riepilogo annuale e il confronto con il 730.
6. In caso di rollback, disabilitare importer e viste CU e rimuovere solo le righe CU importate; non modificare Persona, Dichiarazione o Quadri 730.

## Open Questions

- Le CU sostitutive e annullate richiederanno in seguito un campo esplicito di stato/versione collegato alla CU originaria.
- Va verificato durante l’implementazione quali punti CU siano aggregabili nel riepilogo e quali debbano restare esclusivamente per documento.
- L’eventuale collegamento esplicito tra una CU e una riga `QuadroC_Lavoro` può essere aggiunto dopo aver osservato i casi di riconciliazione reali.
