# Server MCP di Test per DapaBot

Server MCP completo per testare l'integrazione MCP in DapaBot. Supporta **stdio** (raccomandato per uso normale) e **HTTP/SSE** (solo per debug avanzato).

## ⚠️ IMPORTANTE: Usa Stdio, Non HTTP

**Raccomandazione**: Usa **SOLO stdio** per server MCP locali in DapaBot.

**Perché?**
- ✅ **Stdio funziona perfettamente** con `langchain-mcp-adapters`
- ✅ **Gestione automatica** del processo da parte di DapaBot
- ✅ **Nessuna configurazione di rete** necessaria
- ✅ **Più sicuro** (nessuna porta esposta)
- ❌ **HTTP/SSE di FastMCP NON è compatibile** con `langchain-mcp-adapters`

**HTTP è utile solo per**:
- Debug manuale con curl
- Test del server in isolamento
- Sviluppo del server stesso

**Per uso in DapaBot**: Configura sempre come server **local** (stdio), mai come **remote** (HTTP).

## 🛠️ Tools Disponibili

1. **somma(a, b)** - Somma due numeri
2. **moltiplica(a, b)** - Moltiplica due numeri
3. **saluta(nome)** - Saluta una persona
4. **conta_parole(testo)** - Analizza un testo e restituisce statistiche

## 📋 Prerequisiti

```bash
# Installa FastMCP
uv pip install fastmcp

# Per modalità HTTP, installa anche uvicorn
uv pip install uvicorn
```

## 🧪 Test Modalità HTTP (Solo Debug - NON per DapaBot)

### ⚠️ ATTENZIONE
FastMCP con `transport="sse"` **NON è compatibile** con `langchain-mcp-adapters`. Questa modalità è utile **SOLO** per:
- Test manuali del server con curl
- Debug del server in isolamento
- Verifica che i tools funzionino correttamente

**NON configurare server HTTP in DapaBot** - usa sempre stdio!

### 1. Avvia il Server (Solo per Test Manuali)

```bash
python test_mcp_server.py --http
```

Output:
```
🌐 Avvio server MCP in modalità HTTP...
📍 URL: http://127.0.0.1:8000
🛠️  Tools disponibili: somma, moltiplica, saluta, conta_parole
⚠️  NOTA: Questa modalità è solo per test manuali, non per DapaBot!
```

### 2. Testa con curl (Solo Verifica Funzionamento)

**NOTA**: Questi comandi servono solo per verificare che il server funzioni. Per usare il server in DapaBot, vedi la sezione "Test Modalità Stdio" più sotto.

**Lista tools disponibili:**
```bash
curl -X POST http://127.0.0.1:8000/sse \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","params":{},"id":1}'
```

**Risposta attesa:**
```
405 Method Not Allowed
```

**Perché?** FastMCP SSE usa GET per SSE, non POST. Questo conferma che HTTP/SSE di FastMCP non è compatibile con il protocollo HTTP standard di MCP.

### 3. ❌ NON Configurare HTTP in DapaBot

**NON FARE QUESTO:**
```
❌ Nome: test-server-http
❌ Tipo: remote
❌ URL: http://127.0.0.1:8000/sse
```

**Risultato**: Errore "unhandled errors in a TaskGroup" perché `langchain-mcp-adapters` si aspetta un protocollo HTTP diverso da quello di FastMCP SSE.

## 🔌 Test Modalità Stdio (✅ RACCOMANDATO per DapaBot)

### 1. Configura in DapaBot (Metodo Corretto)

1. **Apri DapaBot**: `streamlit run dapabot.py`

2. **Apri Dialog MCP**:
   - Nella sidebar, espandi "🤖 Modalità Agentica"
   - Click su "🔌 Configura MCP"

3. **Aggiungi Server**:
   - Click "➕ Aggiungi Nuovo Server"
   - Compila il form:
     - **Nome**: `test-server`
     - **Tipo**: `local` ← IMPORTANTE!
     - **Descrizione**: `Server di test con tools matematici`
     - **Comando**: `python`
     - **Argomenti** (uno per riga):
       ```
       /percorso/completo/test_mcp_server.py
       ```
       ⚠️ Usa il percorso **assoluto** del file!
       
       Esempio: `/home/user/workspace/bob/Dapabot/test_mcp_server.py`

4. **Salva**: Click "💾 Salva"

5. **Attiva Server**:
   - Nella lista a sinistra, seleziona `test-server` nel multiselect
   - Il server apparirà con icona 💻 (locale)

6. **Chiudi Dialog**: Click fuori dal dialog o su X

### 2. Usa in DapaBot (Flusso Completo)

1. **Attiva Modalità Agentica**:
   ```
   ☑ Abilita Modalità Agentica
   ```

2. **Attiva MCP**:
   ```
   ☑ Abilita MCP
   ```
   Nota: Questo abilita automaticamente anche la modalità agentica se non era già attiva.

3. **Verifica Server Attivi**:
   - Espandi "🔌 Server MCP attivi"
   - Dovresti vedere: `💻 test-server (local)`

4. **Testa i Tools**:

   **Test 1 - Somma:**
   ```
   User: Quanto fa 5 + 3?
   Agent: [Usa tool somma] Il risultato è 8.
   ```

   **Test 2 - Moltiplicazione:**
   ```
   User: Moltiplica 7 per 6
   Agent: [Usa tool moltiplica] 7 × 6 = 42
   ```

   **Test 3 - Saluto:**
   ```
   User: Salutami come Mario
   Agent: [Usa tool saluta] Ciao Mario! Benvenuto nel server MCP di test.
   ```

   **Test 4 - Analisi Testo:**
   ```
   User: Analizza questo testo: "Il sole splende nel cielo azzurro"
   Agent: [Usa tool conta_parole]
   Il testo contiene:
   - 6 parole
   - 35 caratteri
   - 6 parole uniche
   - Parola più lunga: "splende" (8 caratteri)
   ```

### 3. Verifica Funzionamento

**Indicatori di successo:**
- ✅ Server appare in "🔌 Server MCP attivi"
- ✅ Nessun errore in "⚠️ Errori di caricamento tools"
- ✅ Agent usa i tools automaticamente
- ✅ Risposte corrette dall'agent

**Se ci sono problemi:**
- ❌ Verifica il percorso assoluto del file
- ❌ Controlla che Python sia nel PATH
- ❌ Verifica che fastmcp sia installato: `uv pip install fastmcp`
- ❌ Guarda l'expander "⚠️ Errori di caricamento tools"

## 🐛 Troubleshooting

### Server HTTP non parte

**Errore**: `ModuleNotFoundError: No module named 'uvicorn'`

**Soluzione**:
```bash
uv pip install uvicorn
```

### Server Stdio blocca DapaBot

**Problema**: Il toggle MCP rimane in caricamento infinito

**Causa**: Il server è configurato male o il percorso è errato

**Soluzione**:
1. Verifica il percorso assoluto del file
2. Testa il server manualmente:
   ```bash
   python test_mcp_server.py
   # Premi Ctrl+D per inviare EOF e vedere se risponde
   ```

### Tools non appaiono

**Problema**: L'agent non vede i tools MCP

**Verifica**:
1. Il server è attivo nel multiselect?
2. Il toggle "Abilita MCP" è attivo?
3. Controlla l'expander "🔌 Server MCP attivi"
4. Controlla l'expander "⚠️ Errori di caricamento tools"

## 📊 Esempi di Utilizzo

### Esempio 1: Calcoli Matematici
```
User: Quanto fa 15 moltiplicato per 7?
Agent: [Usa tool moltiplica] Il risultato è 105.
```

### Esempio 2: Analisi Testo
```
User: Analizza questo testo: "Il sole splende nel cielo azzurro"
Agent: [Usa tool conta_parole] 
Il testo contiene:
- 6 parole
- 35 caratteri
- 6 parole uniche
- Parola più lunga: "splende"
```

### Esempio 3: Combinazione Tools
```
User: Salutami come Bob e poi dimmi quanto fa 10 + 20
Agent: [Usa tool saluta] Ciao Bob! Benvenuto nel server MCP di test.
       [Usa tool somma] 10 + 20 = 30
```
## 🔄 Differenze Stdio vs HTTP

| Aspetto | Stdio | HTTP/SSE (FastMCP) |
|---------|-------|-------------------|
| **Compatibilità DapaBot** | ✅ Perfetta | ❌ Non compatibile |
| **Avvio** | ✅ Automatico da DapaBot | ❌ Manuale in terminale |
| **Test** | ✅ Tramite DapaBot | ⚠️ Solo con curl (limitato) |
| **Debug** | ⚠️ Più difficile | ✅ Facile (vedi log) |
| **Riavvio** | ✅ Automatico | ❌ Manuale |
| **Sicurezza** | ✅ Nessuna porta esposta | ⚠️ Porta locale esposta |
| **Uso Raccomandato** | ✅ Sempre per DapaBot | ❌ Solo debug server |
| **Protocollo** | ✅ MCP standard (stdio) | ❌ SSE custom FastMCP |

## 💡 Consigli Aggiornati

1. **Per DapaBot**: Usa **SEMPRE stdio** (tipo `local`)
2. **Per debug server**: Usa HTTP solo per verificare che i tools funzionino
3. **Per produzione**: Usa stdio per sicurezza e compatibilità
4. **Per test**: Stdio è sufficiente, HTTP non aggiunge valore per DapaBot

## ⚠️ Problemi Comuni e Soluzioni

### Problema: "unhandled errors in a TaskGroup"
**Causa**: Hai configurato un server HTTP in DapaBot  
**Soluzione**: Riconfigura come server `local` (stdio), non `remote` (HTTP)

### Problema: Server non si avvia
**Causa**: Percorso file non corretto o Python non trovato  
**Soluzione**: 
1. Usa percorso **assoluto** del file
2. Verifica: `which python` o `where python`
3. Testa manualmente: `python /percorso/completo/test_mcp_server.py`

### Problema: Tools non appaiono
**Causa**: Server non attivo o toggle MCP disabilitato  
**Soluzione**:
1. Verifica che il server sia selezionato nel multiselect
2. Verifica che toggle "Abilita MCP" sia attivo
3. Controlla expander "⚠️ Errori di caricamento tools"

### Problema: curl ritorna 405 Method Not Allowed
**Causa**: FastMCP SSE usa GET, non POST  
**Soluzione**: Questo è normale! Conferma che HTTP/SSE non è compatibile con `langchain-mcp-adapters`. Usa stdio invece.



## 🎯 Prossimi Passi

Dopo aver testato questo server, puoi:
1. Creare i tuoi server MCP personalizzati
2. Aggiungere tools più complessi
3. Integrare API esterne
4. Usare resources e prompts MCP

Buon test! 🚀