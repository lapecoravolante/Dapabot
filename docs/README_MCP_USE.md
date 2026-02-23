# 🚀 Quick Start - Integrazione mcp-use

## Installazione Rapida

```bash
# Installa le dipendenze
uv sync

# Oppure con pip
pip install mcp-use
```

## Test Rapido

```bash
# Test dell'integrazione
python test_mcp_use_integration.py
```

## Uso nell'Applicazione

### 1. Configura un Server MCP

```bash
# Avvia l'app
streamlit run dapabot.py
```

Nella sidebar:
1. Vai su **🔌 MCP**
2. Clicca **➕ Aggiungi Nuovo Server**
3. Configura (esempio con filesystem):
   - **Nome**: `filesystem`
   - **Tipo**: `local`
   - **Comando**: `npx`
   - **Argomenti**: `-y @modelcontextprotocol/server-filesystem /tmp`
4. Seleziona il server nel multiselect
5. Clicca **💾 Salva**

### 2. Esplora con Preview

1. Nella lista server, clicca il pulsante **🔍** accanto al server attivo
2. Esplora i 3 tabs:
   - **🔧 Tools**: Funzioni che l'agent può chiamare
   - **📄 Risorse**: Contenuti che l'agent può leggere
   - **💬 Prompt**: Template di messaggi predefiniti
3. Usa la ricerca per trovare elementi specifici

### 3. Usa in Modalità Agentica

1. Nella sidebar, abilita **🤖 Modalità Agentica**
2. Abilita il toggle **MCP**
3. Clicca **Carica Tools**
4. Verifica il messaggio: `✅ X tools caricati (include tools+risorse+prompt)`
5. Invia un messaggio che richiede l'uso di un tool MCP

Esempio:
```
"Elenca i file nella directory /tmp"
```

L'agent userà automaticamente i tools MCP disponibili!

## Esempi di Server MCP

### Filesystem
```bash
npx -y @modelcontextprotocol/server-filesystem /path/to/directory
```

### GitHub
```bash
npx -y @modelcontextprotocol/server-github
```
Richiede: `GITHUB_PERSONAL_ACCESS_TOKEN`

### Google Drive
```bash
npx -y @modelcontextprotocol/server-gdrive
```

### Brave Search
```bash
npx -y @modelcontextprotocol/server-brave-search
```
Richiede: `BRAVE_API_KEY`

### Airbnb (esempio dalla documentazione)
```bash
npx -y @openbnb/mcp-server-airbnb --ignore-robots-txt
```

## Struttura del Progetto

```
Dapabot/
├── src/mcp/
│   ├── langchain_adapter.py      # Adapter mcp-use → LangChain
│   ├── client.py                 # Manager unificato
│   ├── gui_mcp.py                # GUI configurazione
│   └── gui_mcp_discovery.py      # GUI preview
├── docs/
│   └── MCP_USE_INTEGRATION.md    # Documentazione completa
├── test_mcp_use_integration.py   # Script di test
├── CHANGELOG_MCP_USE.md          # Changelog
└── README_MCP_USE.md             # Questo file
```

## Differenze Chiave

### Prima (langchain-mcp-adapters)
- ❌ Solo tools disponibili
- ❌ Risorse e prompt non accessibili
- ❌ Due sistemi separati (adapter + SDK nativo)
- ❌ Nessun preview

### Ora (mcp-use)
- ✅ Tools, risorse E prompt disponibili
- ✅ Sistema unificato
- ✅ Preview completo prima dell'attivazione
- ✅ Più semplice da mantenere

## Troubleshooting

### "Import mcp_use could not be resolved"
```bash
uv sync
# oppure
pip install mcp-use
```

### "No tools found"
1. Verifica che il server sia configurato correttamente
2. Verifica che sia selezionato nel multiselect
3. Usa il pulsante 🔍 per vedere cosa offre

### "Agent non usa i tools MCP"
1. Abilita "Modalità Agentica"
2. Abilita toggle "MCP"
3. Clicca "Carica Tools"
4. Verifica il conteggio nel messaggio di successo

## Documentazione Completa

Vedi `docs/MCP_USE_INTEGRATION.md` per:
- Dettagli tecnici completi
- Guida al testing approfondita
- Troubleshooting avanzato
- Note sull'architettura

## Supporto

- 📚 [Documentazione mcp-use](https://manufact.com/docs/python)
- 🔗 [MCP Protocol](https://modelcontextprotocol.io/)
- 🐛 Segnala problemi su GitHub

---

**Made with Bob** 🤖