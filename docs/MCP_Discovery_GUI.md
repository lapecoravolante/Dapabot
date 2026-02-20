# GUI MCP Discovery - Manuale Utente

## Panoramica

Il **MCP Discovery Dialog** è un'interfaccia grafica avanzata che permette di esplorare e utilizzare risorse e prompt dai server MCP configurati in Dapabot.

## Caratteristiche Principali

### 🔍 Discovery Completo
- **Risorse**: Esplora file, documenti, API endpoints e altre risorse esposte dai server MCP
- **Prompt**: Scopri template di prompt con i loro argomenti e descrizioni

### 📌 Quick Access
- **Elementi Recenti**: Accesso rapido alle ultime 5 risorse e prompt utilizzati
- **Pulsanti Quick Access**: Nella chat principale per accesso immediato

### 🔎 Ricerca Full-Text
- Cerca risorse per nome, descrizione o URI
- Cerca prompt per nome o descrizione
- Filtraggio in tempo reale

### ✓ Gestione Selezione
- Allega multiple risorse al prossimo messaggio
- Imposta un prompt come messaggio di sistema
- Visualizzazione chiara della selezione corrente

## Come Usare

### 1. Aprire il Dialog

Ci sono due modi per aprire il dialog MCP Discovery:

**Metodo 1: Pulsante nella Chat**
```python
# Il pulsante "🔍 MCP Discovery" appare nella sidebar della chat
# Cliccalo per aprire il dialog
```

**Metodo 2: Programmaticamente**
```python
from src.mcp import mostra_dialog_mcp_discovery

# Apri il dialog
st.session_state.mcp_discovery_open = True
mostra_dialog_mcp_discovery()
```

### 2. Selezionare un Server

1. Nella colonna di sinistra, vedrai la lista dei server MCP configurati
2. Clicca su un server per visualizzarne risorse e prompt
3. Il server selezionato rimane attivo mentre navighi tra i tabs

### 3. Esplorare Risorse

**Tab "📄 Risorse":**

1. Usa la barra di ricerca per filtrare le risorse
2. Clicca su una risorsa per vedere i dettagli:
   - URI completo
   - Descrizione
   - Tipo MIME
3. Clicca sul pulsante **📎** per allegare la risorsa al prossimo messaggio

**Esempio:**
```
📄 documento.pdf
   URI: file:///path/to/documento.pdf
   Descrizione: Documento di progetto
   Tipo: application/pdf
   [📎] ← Clicca per allegare
```

### 4. Esplorare Prompt

**Tab "💬 Prompt":**

1. Usa la barra di ricerca per filtrare i prompt
2. Clicca su un prompt per vedere:
   - Descrizione completa
   - Lista degli argomenti (obbligatori e opzionali)
3. Clicca sul pulsante **✨** per usare il prompt come messaggio di sistema

**Esempio:**
```
💬 code_review
   Descrizione: Analizza e rivedi codice
   Argomenti:
   - ✓ code (obbligatorio): Il codice da rivedere
   - ○ language (opzionale): Linguaggio di programmazione
   [✨] ← Clicca per usare
```

### 5. Gestire la Selezione

**Visualizzazione Selezione Corrente:**

Nella parte inferiore del dialog vedrai:

```
✓ Selezione corrente
──────────────────────
Risorse allegate (2):
📄 documento.pdf [❌]
📄 config.json [❌]

Prompt come messaggio di sistema:
💬 code_review (da github-server) [❌]
```

**Azioni disponibili:**
- **❌** accanto a ogni elemento: Rimuovi dalla selezione
- **🗑️ Pulisci selezione**: Rimuovi tutto
- **✓ Applica e chiudi**: Chiudi il dialog mantenendo la selezione

### 6. Usare gli Elementi Recenti

**Sezione "📌 Usati di recente":**

Nella colonna di sinistra, sotto la lista dei server:

```
📌 Usati di recente
──────────────────────
Risorse              Prompt
📄 documento.pdf     💬 code_review
📄 config.json       💬 debug_helper
📄 readme.md         💬 summarize
```

Clicca su un elemento recente per aggiungerlo rapidamente alla selezione.

### 7. Inviare il Messaggio

Dopo aver chiuso il dialog:

1. La selezione rimane attiva
2. Nella chat vedrai un indicatore compatto:
   ```
   ✓ Selezione MCP attiva
   📎 2 risorsa/e allegata/e
   💬 Prompt: code_review
   ```
3. Scrivi il tuo messaggio normalmente
4. All'invio:
   - Le risorse vengono allegate automaticamente
   - Il prompt viene usato come messaggio di sistema
   - La selezione viene pulita automaticamente

## Funzionalità Avanzate

### Aggiornamento Cache

Il pulsante **🔄 Aggiorna cache** forza il ricaricamento di risorse e prompt dai server MCP. Utile quando:
- Hai aggiunto nuove risorse al server
- Hai modificato i prompt disponibili
- Vuoi assicurarti di avere i dati più recenti

### Ricerca Intelligente

La ricerca full-text cerca in:
- Nome dell'elemento
- Descrizione completa
- URI (solo per risorse)
- Nomi degli argomenti (solo per prompt)

**Esempio:**
```
Ricerca: "pdf"
Trova:
- Risorse con nome "documento.pdf"
- Risorse con descrizione "File PDF di progetto"
- Risorse con URI "file:///docs/report.pdf"
```

## Integrazione nel Codice

### Ottenere la Selezione

```python
from src.mcp import get_selected_mcp_resources, get_selected_mcp_prompt

# Ottieni risorse selezionate
resources = get_selected_mcp_resources()
for resource in resources:
    print(f"Risorsa: {resource['name']}")
    print(f"URI: {resource['uri']}")

# Ottieni prompt selezionato
prompt = get_selected_mcp_prompt()
if prompt:
    print(f"Prompt: {prompt['name']}")
    print(f"Server: {prompt['server']}")
    print(f"Argomenti: {prompt['arguments']}")
```

### Pulire la Selezione

```python
from src.mcp import clear_mcp_selection

# Dopo l'invio del messaggio
clear_mcp_selection()
```

### Mostrare Quick Access

```python
from src.mcp import mostra_quick_access_buttons

# Nella sidebar della chat
with st.sidebar:
    mostra_quick_access_buttons()
```

## Best Practices

### 1. Organizzazione Server
- Configura server MCP con nomi descrittivi
- Raggruppa risorse correlate nello stesso server
- Usa descrizioni chiare per risorse e prompt

### 2. Uso delle Risorse
- Allega solo le risorse necessarie per il contesto
- Usa la ricerca per trovare rapidamente ciò che serve
- Controlla i tipi MIME per assicurarti della compatibilità

### 3. Uso dei Prompt
- Leggi attentamente gli argomenti richiesti
- Usa prompt specifici per task specifici
- Combina prompt con risorse per contesto completo

### 4. Performance
- La cache rende le ricerche successive istantanee
- Aggiorna la cache solo quando necessario
- I recenti sono limitati a 5 per tipo per performance

## Troubleshooting

### Il dialog non mostra server
**Problema**: "Nessun server MCP configurato"
**Soluzione**: Vai nella sezione MCP e configura almeno un server attivo

### Errore nel caricamento risorse/prompt
**Problema**: "Errore nel caricamento risorse: ..."
**Soluzione**: 
1. Verifica che il server MCP sia in esecuzione
2. Controlla la configurazione del server
3. Prova ad aggiornare la cache

### La ricerca non trova nulla
**Problema**: Nessun risultato per la query
**Soluzione**:
1. Verifica l'ortografia
2. Prova termini più generici
3. Pulisci la ricerca per vedere tutti gli elementi

### Selezione non applicata
**Problema**: Gli elementi selezionati non vengono usati
**Soluzione**:
1. Assicurati di cliccare "✓ Applica e chiudi"
2. Verifica che l'indicatore "✓ Selezione MCP attiva" sia visibile
3. Controlla che la selezione non sia stata pulita accidentalmente

## Esempi d'Uso

### Esempio 1: Code Review con Contesto

1. Apri MCP Discovery
2. Seleziona server "github"
3. Tab Risorse: Allega `src/main.py`
4. Tab Prompt: Usa `code_review`
5. Chiudi e scrivi: "Rivedi questo codice per sicurezza"

### Esempio 2: Analisi Documenti

1. Apri MCP Discovery
2. Seleziona server "filesystem"
3. Tab Risorse: Allega `report.pdf` e `data.csv`
4. Tab Prompt: Usa `analyze_documents`
5. Chiudi e scrivi: "Confronta i dati nel report con il CSV"

### Esempio 3: Quick Access

1. Usa elementi recenti per accesso rapido
2. Clicca su risorsa recente per allegarla
3. Clicca su prompt recente per usarlo
4. Scrivi il messaggio e invia

## Limitazioni Note

- Massimo 5 elementi nei recenti per tipo
- La ricerca è case-insensitive ma richiede match esatto delle parole
- Le risorse molto grandi potrebbero richiedere tempo per il caricamento
- Un solo prompt può essere attivo alla volta

## Roadmap Future

- [ ] Supporto per preview delle risorse
- [ ] Auto-completion per argomenti dei prompt
- [ ] Salvataggio di selezioni favorite
- [ ] Export/import di configurazioni
- [ ] Statistiche di utilizzo