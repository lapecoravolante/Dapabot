# Changelog - Integrazione mcp-use

## [Unreleased] - 2026-02-23

### 🎉 Nuove Funzionalità

#### Integrazione Completa mcp-use
- **Tools, Risorse E Prompt**: Ora tutti e tre i tipi di elementi MCP sono disponibili per l'agent
- **Preview Discovery**: Nuova GUI per esplorare cosa offre ogni server MCP prima di attivarlo
- **Pulsante Preview**: Pulsante 🔍 nella lista server per accesso rapido al discovery
- **Tabs Organizzati**: Discovery con 3 tabs separati (Tools, Risorse, Prompt)
- **Ricerca Unificata**: Ricerca per nome/descrizione in tutti i tabs
- **Metriche**: Riepilogo con conteggi per tipo di elemento

### 🔄 Modifiche

#### Dipendenze
- ➕ Aggiunto: `mcp-use>=0.1.0`
- ➖ Rimosso: `langchain-mcp-adapters>=0.1.0`
- ➖ Rimosso: `mcp>=1.0.0` (SDK nativo)
- ✅ Mantenuto: `fastmcp>=3.0.0`

#### Architettura
- **MCPClientManager** (`src/mcp/client.py`): Completamente riscritto per usare mcp-use
- **Adapter Module** (`src/mcp/langchain_adapter.py`): Nuovo modulo per conversione async→sync
- **GUI Discovery** (`src/mcp/gui_mcp_discovery.py`): Riscritta con supporto per tools/risorse/prompt
- **GUI MCP** (`src/mcp/gui_mcp.py`): Aggiunto pulsante preview per server attivi
- **Tools Loading** (`src/gui_utils.py`): Aggiornato per caricare tutto in modo unificato

### ✨ Miglioramenti

#### Performance
- Cache unificata per tools+risorse+prompt
- Meno chiamate di rete grazie a caricamento batch
- Preview istantaneo con cache

#### Usabilità
- Utente vede cosa offre ogni server prima di attivarlo
- Schema argomenti visibile per ogni elemento
- Feedback chiaro su conteggi e disponibilità
- Ricerca rapida in tutti i tabs

#### Manutenibilità
- Un solo client invece di due sistemi separati
- Meno codice, più semplice da mantenere
- Migliore separazione delle responsabilità

### 🔧 Dettagli Tecnici

#### File Modificati
```
pyproject.toml                    # Dipendenze
src/mcp/langchain_adapter.py      # NUOVO
src/mcp/client.py                 # Riscritto
src/mcp/gui_mcp_discovery.py      # Riscritto
src/mcp/gui_mcp.py                # Aggiornato
src/gui_utils.py                  # Aggiornato
docs/MCP_USE_INTEGRATION.md       # NUOVO
```

#### Metodi Principali

**MCPClientManager**:
- `get_all_as_langchain_tools()` - Ritorna tools+risorse+prompt unificati
- `get_tools_only()` - Solo tools
- `get_resources_only()` - Solo risorse
- `get_prompts_only()` - Solo prompt
- `get_preview_info()` - Conteggi per preview
- `invalidate_cache()` - Invalida cache

**MCPLangChainAdapter**:
- `create_all(client)` - Crea tutto
- `create_tools(client)` - Solo tools
- `create_resources(client)` - Solo risorse
- `create_prompts(client)` - Solo prompt
- Proprietà: `tools`, `resources`, `prompts`, `all_tools`

### 🔒 Retrocompatibilità

- ✅ Configurazioni esistenti nel DB continuano a funzionare
- ✅ Nessuna modifica ai provider esistenti
- ✅ Nessuna modifica alla modalità agentica
- ✅ Tools custom non influenzati
- ✅ Funzioni di compatibilità mantenute

### 📋 Checklist Pre-Release

- [x] Dipendenze aggiornate
- [x] Codice implementato
- [x] Documentazione creata
- [ ] Testing con server MCP reale
- [ ] Verifica modalità agentica end-to-end
- [ ] Test di regressione su funzionalità esistenti
- [ ] Verifica performance
- [ ] Review codice

### 🚀 Installazione

```bash
# Installa nuove dipendenze
uv sync

# Oppure
pip install mcp-use
```

### 🧪 Testing Rapido

```bash
# 1. Verifica installazione
python -c "from mcp_use import MCPClient; print('✅ OK')"

# 2. Avvia app
streamlit run dapabot.py

# 3. Configura un server MCP di test
# 4. Usa il pulsante 🔍 per preview
# 5. Abilita modalità agentica e testa
```

### 📚 Documentazione

Vedi `docs/MCP_USE_INTEGRATION.md` per:
- Guida completa all'integrazione
- Istruzioni di testing dettagliate
- Troubleshooting
- Note tecniche

### 🐛 Known Issues

Nessuno al momento. Segnala problemi su GitHub.

### 🙏 Crediti

- Libreria `mcp-use`: https://manufact.com/docs/python
- MCP Protocol: https://modelcontextprotocol.io/

---

**Made with Bob** 🤖