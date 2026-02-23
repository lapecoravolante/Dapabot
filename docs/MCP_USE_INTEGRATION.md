# Integrazione mcp-use con LangChain - Riepilogo

## Modifiche Implementate

### 1. Dipendenze (`pyproject.toml`)
- ✅ **Aggiunto**: `mcp-use>=0.1.0`
- ✅ **Rimosso**: `langchain-mcp-adapters>=0.1.0`
- ✅ **Rimosso**: `mcp>=1.0.0` (SDK nativo non più necessario)
- ✅ **Mantenuto**: `fastmcp>=3.0.0` (per server MCP custom)

### 2. Nuovo Adapter Module (`src/mcp/langchain_adapter.py`)
Creato nuovo modulo che:
- Wrappa `LangChainAdapter` di `mcp-use`
- Converte tools, risorse e prompt async → sync per compatibilità
- Fornisce metodi separati: `create_all()`, `create_tools()`, `create_resources()`, `create_prompts()`
- Gestisce cache e conteggi

### 3. MCPClientManager Riscritto (`src/mcp/client.py`)
Completamente riscritto per usare `mcp-use`:
- Sostituito `MultiServerMCPClient` con `MCPClient` di mcp-use
- Rimossi metodi SDK nativi (`_create_native_session`, `list_available_resources`, `list_available_prompts`)
- Aggiunto `get_all_as_langchain_tools()` - metodo unificato per tools+risorse+prompt
- Aggiunto `get_preview_info()` - per ottenere conteggi prima dell'attivazione
- Mantenuta retrocompatibilità con configurazioni esistenti nel DB

### 4. Tools Loading Aggiornato (`src/gui_utils.py`)
Modificata funzione `_carica_tools_nei_provider()`:
- Usa `get_all_as_langchain_tools()` invece di `get_tools()`
- Carica automaticamente tools + risorse + prompt in un'unica chiamata
- Messaggio di errore aggiornato per riflettere il caricamento unificato

### 5. GUI Discovery Riscritta (`src/mcp/gui_mcp_discovery.py`)
Completamente riscritta per mostrare tutto:
- **3 Tabs**: Tools 🔧, Risorse 📄, Prompt 💬
- Preview completo di cosa offre ogni server PRIMA dell'attivazione
- Ricerca unificata per nome/descrizione
- Mostra schema argomenti per ogni elemento
- Riepilogo con metriche (conteggi per tipo)
- Funzioni di compatibilità mantenute per non rompere codice esistente

### 6. GUI MCP Config Aggiornata (`src/mcp/gui_mcp.py`)
Aggiunto pulsante preview:
- Pulsante 🔍 accanto a ogni server attivo nella lista
- Apre il dialog di discovery pre-popolato con il server selezionato
- Permette di esplorare tools/risorse/prompt prima di usarli

## Vantaggi della Nuova Architettura

1. **Unificazione**: Un solo client (`mcp-use`) invece di due sistemi separati
2. **Completezza**: Tools, risorse E prompt passati al modello
3. **Semplicità**: Meno codice, meno dipendenze, più manutenibile
4. **Preview**: Utente vede cosa offre ogni server prima di attivarlo
5. **Performance**: Cache unificata, meno chiamate di rete
6. **Retrocompatibilità**: Configurazioni esistenti continuano a funzionare

## Struttura File Modificati

```
pyproject.toml                    # Dipendenze aggiornate
src/mcp/
├── langchain_adapter.py          # NUOVO - wrapper adapter
├── client.py                     # Riscritto con mcp-use
├── gui_mcp_discovery.py          # Riscritto con 3 tabs
└── gui_mcp.py                    # Aggiunto pulsante preview
src/gui_utils.py                  # Aggiornato caricamento tools
```

## Installazione

Per installare le nuove dipendenze:

```bash
uv sync
```

Oppure:

```bash
pip install mcp-use
```

## Testing

### Test 1: Verifica Installazione
```bash
python -c "from mcp_use import MCPClient; from mcp_use.agents.adapters import LangChainAdapter; print('✅ mcp-use installato correttamente')"
```

### Test 2: Configurazione Server MCP
1. Avvia l'applicazione: `streamlit run dapabot.py`
2. Nella sidebar, vai su "🔌 MCP"
3. Aggiungi un server di test (es. `@openbnb/mcp-server-airbnb`)
4. Configuralo come server locale:
   - Comando: `npx`
   - Args: `-y @openbnb/mcp-server-airbnb --ignore-robots-txt`
5. Selezionalo nel multiselect per attivarlo
6. Salva la configurazione

### Test 3: Preview Discovery
1. Nella lista server, clicca sul pulsante 🔍 accanto al server attivo
2. Verifica che si apra il dialog con 3 tabs
3. Esplora i tabs:
   - **Tools**: Dovrebbe mostrare i tools disponibili
   - **Risorse**: Dovrebbe mostrare le risorse disponibili
   - **Prompt**: Dovrebbe mostrare i prompt disponibili
4. Verifica che la ricerca funzioni in ogni tab
5. Verifica che il riepilogo mostri i conteggi corretti

### Test 4: Modalità Agentica
1. Nella sidebar, abilita "Modalità Agentica"
2. Abilita il toggle "MCP"
3. Clicca "Carica Tools"
4. Verifica il messaggio di successo con conteggio tools+risorse+prompt
5. Invia un messaggio che richiede l'uso di un tool MCP
6. Verifica che l'agent:
   - Riconosca i tools disponibili
   - Chiami il tool corretto
   - Usi risorse/prompt se necessario
   - Ritorni una risposta basata sui risultati

### Test 5: Cache e Performance
1. Apri il preview di un server
2. Chiudi e riapri → dovrebbe essere istantaneo (cache)
3. Clicca "🔄 Ricarica" → dovrebbe ricaricare i dati
4. Verifica che non ci siano rallentamenti

## Troubleshooting

### Errore: "Import mcp_use could not be resolved"
**Soluzione**: Installa mcp-use con `uv sync` o `pip install mcp-use`

### Errore: "No tools/resources/prompts found"
**Possibili cause**:
1. Server MCP non configurato correttamente
2. Server non attivo nel multiselect
3. Server non raggiungibile (verifica comando/URL)

**Soluzione**: 
- Verifica configurazione in "🔌 MCP"
- Controlla che il server sia selezionato nel multiselect
- Testa il comando manualmente nel terminale

### Errore: "Agent non chiama i tools MCP"
**Possibili cause**:
1. Modalità agentica non abilitata
2. Toggle MCP non attivo
3. Tools non caricati

**Soluzione**:
- Abilita "Modalità Agentica" nella sidebar
- Abilita toggle "MCP"
- Clicca "Carica Tools" e verifica il conteggio

### Performance lente
**Possibili cause**:
1. Troppi server attivi contemporaneamente
2. Server remoti lenti
3. Cache non utilizzata

**Soluzione**:
- Disattiva server non necessari
- Usa cache (evita di cliccare "Ricarica" troppo spesso)
- Considera di usare solo server locali per sviluppo

## Compatibilità

- ✅ Retrocompatibile con configurazioni esistenti nel DB
- ✅ Nessuna modifica ai provider esistenti
- ✅ Nessuna modifica alla modalità agentica
- ✅ Tools custom continuano a funzionare
- ✅ Funzioni di compatibilità mantenute in `gui_mcp_discovery.py`

## Prossimi Passi

1. ✅ Installare `mcp-use`
2. ✅ Testare con un server MCP reale
3. ✅ Verificare che tools, risorse e prompt siano tutti disponibili
4. ✅ Testare la modalità agentica end-to-end
5. ⏳ Aggiornare documentazione utente se necessario
6. ⏳ Considerare l'aggiunta di esempi di server MCP comuni

## Note Tecniche

### Conversione Async → Sync
I tools di `mcp-use` sono async, ma il progetto li usa in modo sincrono.
L'adapter gestisce automaticamente la conversione usando `asyncio.run()`.

### Cache
La cache è gestita a livello di `MCPClientManager` e si invalida automaticamente
quando le configurazioni cambiano. Può essere invalidata manualmente con
`manager.invalidate_cache()`.

### Formato Configurazione
Il formato delle configurazioni nel DB rimane invariato:
- **Local**: `{comando, args, env}`
- **Remote**: `{url, api_key, headers}`

`mcp-use` accetta lo stesso formato, quindi non serve migrazione.

## Riferimenti

- [mcp-use Documentation](https://manufact.com/docs/python/getting-started/welcome)
- [mcp-use LangChain Integration](https://manufact.com/docs/python/integration/langchain)
- [MCP Protocol](https://modelcontextprotocol.io/)

---

**Made with Bob** 🤖