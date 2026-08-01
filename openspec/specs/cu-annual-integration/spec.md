# CU Annual Integration

## Purpose

Definisce il riepilogo annuale delle Certificazioni Uniche e il confronto con i dati del Quadro C del 730, mantenendo la provenienza dei documenti.

## Requirements

### Requirement: Il sistema deve aggregare le CU per persona e anno fiscale

Il sistema SHALL produrre un riepilogo annuale raggruppato per Persona e anno fiscale, mostrando numero di CU, sostituti presenti e somme delle sole metriche aggregabili, tra cui redditi certificati e ritenute.

#### Scenario: Aggregazione delle due CU del 2025
- **WHEN** la Persona ha una CU 2025 Engineering e una CU 2025 Tagetik
- **THEN** il riepilogo 2025 mostra due CU, due sostituti e i totali aggregati dei redditi e delle ritenute

#### Scenario: Anno senza CU multiple
- **WHEN** la Persona ha una sola CU per un anno fiscale
- **THEN** il riepilogo mostra una CU e usa gli stessi campi aggregabili senza richiedere un caso speciale

### Requirement: L’aggregazione deve mantenere la provenienza dei dati

Il sistema SHALL mantenere ogni CU come sorgente consultabile e SHALL permettere di risalire dal totale annuale al documento, sostituto, modulo e punto che lo compongono. L’aggregazione SHALL NOT modificare i payload originali.

#### Scenario: Consultazione del dettaglio annuale
- **WHEN** l’utente apre il dettaglio di un totale annuale CU
- **THEN** può distinguere i valori provenienti da Engineering da quelli provenienti da Tagetik

#### Scenario: Aggiornamento di una sorgente
- **WHEN** una CU viene reimportata con un payload aggiornato
- **THEN** il riepilogo viene ricalcolato dalle sorgenti senza duplicare o fondere irreversibilmente i documenti

### Requirement: Il sistema deve confrontare CU e 730 senza confonderne la provenienza

Il sistema SHALL confrontare i totali CU aggregati con i dati del Quadro C del 730 per la stessa Persona e anno fiscale. Il confronto SHALL esplicitare differenza e stato e SHALL lasciare separati i documenti CU e la dichiarazione 730.

#### Scenario: Totali CU e Quadro C coerenti
- **WHEN** il totale dei redditi CU coincide con il reddito da lavoro dipendente riportato nel Quadro C entro la tolleranza configurata
- **THEN** il confronto viene marcato coerente e mostra le fonti utilizzate

#### Scenario: Totali CU e Quadro C differenti
- **WHEN** i totali CU e Quadro C non coincidono
- **THEN** il sistema mostra differenza e warning senza sovrascrivere né correggere automaticamente la CU o il 730

#### Scenario: CU senza 730
- **WHEN** esistono CU per un anno ma non esiste una Dichiarazione 730 corrispondente
- **THEN** il riepilogo CU è comunque disponibile e il confronto indica 730 assente

### Requirement: L’interfaccia deve supportare analisi e importazione multipla CU

L’interfaccia SHALL riconoscere i PDF CU durante l’upload, mostrare un’anteprima con anno fiscale, percipiente, sostituto, reddito principale e warning, e permettere la conferma di più documenti nello stesso anno senza raggrupparli in un unico documento.

#### Scenario: Anteprima di più CU
- **WHEN** l’utente carica insieme le due CU relative al 2025
- **THEN** l’anteprima mostra due righe separate e indica che appartengono allo stesso anno fiscale

#### Scenario: Duplicato in anteprima
- **WHEN** l’utente carica un PDF già importato
- **THEN** l’anteprima lo segnala come duplicato e la conferma non crea una nuova sorgente equivalente
