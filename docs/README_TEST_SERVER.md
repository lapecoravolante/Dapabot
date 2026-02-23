# Server MCP di Test

Server MCP completo per testare l'integrazione mcp-use in DapaBot.

## Contenuto

- **4 Tools**: somma, moltiplica, saluta, conta_parole
- **4 Prompts**: analizza_codice, scrivi_documentazione, debug_assistente, revisione_testo
- **5 Risorse**: guide Python, best practices, glossario, esempi

## Avvio Server

### Modalità HTTP SSE (Remoto) - DEFAULT

```bash
# Porta default 8000
.venv/bin/python test_mcp_server.py

# Porta personalizzata
.venv/bin/python test_mcp_server.py --port 6969

# Host e porta personalizzati
.venv/bin/python test_mcp_server.py --host 0.0.0.0 --port 8080
```

### Modalità stdio (Locale)

```bash
.venv/bin/python test_mcp_server.py --transport stdio
```

## Configurazione in DapaBot

### Server Remoto (HTTP SSE)

1. Avvia il server: `.venv/bin/python test_mcp_server.py --port 6969`
2. In DapaBot, vai su **🔌 MCP**
3. Clicca **➕ Aggiungi Nuovo Server**
4. Configura:
   - **Nome**: `test-server`
   - **Tipo**: `remote`
   - **URL**: `http://127.0.0.1:6969/sse`
5. Seleziona nel multiselect
6. Clicca **💾 Salva**

### Server Locale (stdio)

1. In DapaBot, vai su **🔌 MCP**
2. Clicca **➕ Aggiungi Nuovo Server**
3. Configura:
   - **Nome**: `test-server`
   - **Tipo**: `local`
   - **Comando**: `.venv/bin/python`
   - **Argomenti**: `test_mcp_server.py --transport stdio`
4. Seleziona nel multiselect
5. Clicca **💾 Salva**

## Test del Server

### Con curl

```bash
# Lista tools
curl -X POST http://127.0.0.1:6969/sse \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","method":"tools/list","params":{},"id":1}'

# Lista risorse
curl -X POST http://127.0.0.1:6969/sse \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","method":"resources/list","params":{},"id":2}'

# Lista prompt
curl -X POST http://127.0.0.1:6969/sse \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","method":"prompts/list","params":{},"id":3}'

# Chiama tool somma
curl -X POST http://127.0.0.1:6969/sse \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"somma","arguments":{"a":5,"b":3}},"id":4}'
```

### Con DapaBot

1. Configura il server (vedi sopra)
2. Clicca il pulsante **🔍** per preview
3. Esplora i 3 tabs:
   - **🔧 Tools**: Vedi i 4 tools disponibili
   - **📄 Risorse**: Vedi le 5 risorse disponibili
   - **💬 Prompt**: Vedi i 4 prompt disponibili
4. Abilita **Modalità Agentica**
5. Abilita toggle **MCP**
6. Clicca **Carica Tools**
7. Testa con messaggi come:
   - "Quanto fa 5 + 3?"
   - "Salutami!"
   - "Conta le parole in: Hello world from MCP"
   - "Mostrami la guida Python"

## Argomenti CLI

```
--transport {stdio,sse}  Tipo di trasporto (default: sse)
--host HOST              Host per SSE (default: 127.0.0.1)
--port PORT              Porta per SSE (default: 8000)
```

## Esempi

### Server su porta 6969
```bash
.venv/bin/python test_mcp_server.py --port 6969
```

### Server accessibile da rete
```bash
.venv/bin/python test_mcp_server.py --host 0.0.0.0 --port 8000
```

### Server locale stdio
```bash
.venv/bin/python test_mcp_server.py --transport stdio
```

## Troubleshooting

### Porta già in uso
```
OSError: [Errno 98] Address already in use
```
**Soluzione**: Usa una porta diversa con `--port 6969`

### uvicorn non trovato
```
ImportError: No module named 'uvicorn'
```
**Soluzione**: Installa uvicorn
```bash
.venv/bin/uv pip install uvicorn
```

### Server non raggiungibile
**Verifica**:
1. Server in esecuzione: `ps aux | grep test_mcp_server`
2. Porta aperta: `netstat -tuln | grep 6969`
3. URL corretto in DapaBot: `http://127.0.0.1:6969/sse`

## Note

- **SSE (Server-Sent Events)** è il protocollo HTTP per MCP remoto
- **stdio** è per comunicazione locale via standard input/output
- Il server supporta **tutti** i tipi MCP: tools, risorse e prompt
- Perfetto per testare l'integrazione mcp-use completa

---

**Made with Bob** 🤖