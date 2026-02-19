# Manuale di Integrazione MCP in DapaBot

**Versione:** 1.0  
**Data:** 19 Febbraio 2026
**Versione Codice:** 2.0 (con langchain-mcp-adapters)
**Autore:** IBM Bob

---

## Indice

1. [Introduzione](#1-introduzione)
2. [Il Protocollo MCP](#2-il-protocollo-mcp)
3. [Strumenti LangChain per MCP](#3-strumenti-langchain-per-mcp)
4. [Architettura dell'Integrazione](#4-architettura-dellintegrazione)
5. [Logica di Integrazione](#5-logica-di-integrazione)
6. [Modifiche al Codice](#6-modifiche-al-codice)
7. [Integrazione Tools LangChain-MCP](#7-integrazione-tools-langchain-mcp)
8. [Guida Utente GUI](#8-guida-utente-gui)
9. [Estensioni Future](#9-estensioni-future)
10. [Riferimenti](#10-riferimenti)

---

## 1. Introduzione

### 1.1 Scopo del Documento

Questo manuale descrive l'integrazione del protocollo **Model Context Protocol (MCP)** all'interno di DapaBot, un'applicazione di chatbot basata su LangChain e Streamlit. L'integrazione permette di estendere le capacità del bot con tools e risorse esterne fornite da server MCP, sia locali che remoti.

### 1.2 Contesto

DapaBot è un sistema di chatbot multimodale che supporta:
- Diversi provider LLM (OpenRouter, HuggingFace, Replicate)
- Modalità agentica con tools personalizzati
- RAG (Retrieval-Augmented Generation)
- Persistenza delle conversazioni

L'integrazione MCP aggiunge la capacità di utilizzare tools standardizzati da server esterni, ampliando significativamente le funzionalità disponibili.

---

## 2. Il Protocollo MCP

### 2.1 Cos'è MCP

Il **Model Context Protocol (MCP)** è un protocollo aperto che standardizza come le applicazioni forniscono tools e contesto ai Large Language Models (LLM). Definisce:

- **Tools**: Funzioni eseguibili che gli LLM possono invocare
- **Resources**: Dati accessibili (file, database, API)
- **Prompts**: Template di prompt riutilizzabili

### 2.2 Architettura MCP

```
┌─────────────────┐
│   LLM Client    │
│   (DapaBot)     │
└────────┬────────┘
         │
         │ MCP Protocol
         │ (JSON-RPC 2.0)
         │
    ┌────┴────┐
    │         │
┌───▼───┐ ┌──▼────┐
│ Local │ │Remote │
│Server │ │Server │
│(stdio)│ │(HTTP) │
└───────┘ └───────┘
```

### 2.3 Trasporti Supportati

1. **stdio**: Comunicazione tramite standard input/output con processi locali
2. **HTTP**: Comunicazione tramite richieste HTTP/HTTPS con server remoti

---

## 3. Strumenti LangChain per MCP

### 3.1 Libreria langchain-mcp-adapters

LangChain fornisce la libreria `langchain-mcp-adapters` che offre:

#### 3.1.1 MultiServerMCPClient

Classe principale per gestire connessioni a più server MCP:

```python
from langchain_mcp_adapters.client import MultiServerMCPClient

client = MultiServerMCPClient({
    "server1": {
        "transport": "stdio",
        "command": "python",
        "args": ["server.py"]
    },
    "server2": {
        "transport": "http",
        "url": "https://api.example.com/mcp"
    }
})
```

**Caratteristiche:**
- Gestione automatica del ciclo di vita delle connessioni
- Supporto per sessioni stateful e stateless
- Conversione automatica tools MCP → LangChain tools

#### 3.1.2 Funzioni di Caricamento

```python
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_mcp_adapters.resources import load_mcp_resources
from langchain_mcp_adapters.prompts import load_mcp_prompt

# Carica tools
tools = await client.get_tools()

# Carica resources
blobs = await client.get_resources("server_name")

# Carica prompts
messages = await client.get_prompt("server_name", "prompt_name")
```

#### 3.1.3 Interceptors

Sistema middleware per modificare richieste/risposte:

```python
async def auth_interceptor(request, handler):
    """Aggiunge autenticazione alle richieste"""
    modified = request.override(
        headers={"Authorization": f"Bearer {token}"}
    )
    return await handler(modified)

client = MultiServerMCPClient(
    {...},
    tool_interceptors=[auth_interceptor]
)
```

**Casi d'uso:**
- Autenticazione dinamica
- Logging e monitoring
- Retry logic
- Modifica parametri runtime

#### 3.1.4 Callbacks

Sistema di notifiche per eventi:

```python
from langchain_mcp_adapters.callbacks import Callbacks

async def on_progress(progress, total, message, context):
    print(f"Progress: {progress}/{total} - {message}")

client = MultiServerMCPClient(
    {...},
    callbacks=Callbacks(on_progress=on_progress)
)
```

**Eventi supportati:**
- Progress notifications
- Logging messages
- Elicitation requests

#### 3.1.5 Gestione Sessioni

```python
# Sessione stateful per server con stato
async with client.session("server_name") as session:
    tools = await load_mcp_tools(session)
    # La sessione rimane aperta per tutta la durata del blocco
```

---

## 4. Architettura dell'Integrazione

### 4.1 Diagramma Architetturale

```
┌─────────────────────────────────────────────────────────────┐
│                        DapaBot GUI                          │
│                      (Streamlit)                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Toggle "Abilita MCP" (richiede modalità agentica)   │  │
│  │ Pulsante "🔌 Configura MCP" → Dialog modale         │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ Configurazione via Dialog
                         │
┌────────────────────────▼────────────────────────────────────┐
│                  gui_mcp.py                                 │
│              (src/mcp/gui_mcp.py)                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Dialog modale con:                                   │  │
│  │ - Lista server (sinistra)                            │  │
│  │ - Configurazione server (destra)                     │  │
│  │ - Multiselect per attivazione server                 │  │
│  │ - Form per aggiungere/modificare server             │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ Salva in DB
                         │
┌────────────────────────▼────────────────────────────────────┐
│                  ConfigurazioneDB                           │
│                  (SQLite + Peewee)                          │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ MCPServerModel                                       │  │
│  │ - nome (PK), tipo (local/remote)                     │  │
│  │ - descrizione, configurazione (JSON)                 │  │
│  │ - attivo (Boolean)                                   │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ Carica Config Attivi
                         │
┌────────────────────────▼────────────────────────────────────┐
│              MCPClientManager                               │
│              (src/mcp/client.py)                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ - carica_configurazioni_da_db()                      │  │
│  │ - get_client() → MultiServerMCPClient               │  │
│  │ - get_tools() → List[BaseTool] (con caching)        │  │
│  │ - async_to_sync_tool() → Conversione async→sync     │  │
│  │ - reset() → Invalida cache                          │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ Tools MCP (sincroni)
                         │
┌────────────────────────▼────────────────────────────────────┐
│                  gui_utils.py                               │
│              (src/gui_utils.py)                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ _carica_tools_nei_provider():                        │  │
│  │ - Carica tools standard                              │  │
│  │ - Se MCP attivo: carica tools MCP                    │  │
│  │ - Combina tutti i tools per l'agent                  │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ Tools combinati
                         │
┌────────────────────────▼────────────────────────────────────┐
│                  LangChain Agent                            │
│                  (Modalità Agentica)                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ - create_agent(model, tools)                         │  │
│  │ - Esegue tools standard + tools MCP                  │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 Flusso di Dati

```
1. Utente apre dialog MCP via pulsante "🔌 Configura MCP"
   ↓
2. Utente configura server (nome, tipo, URL/comando, ecc.)
   ↓
3. Utente seleziona server attivi tramite multiselect
   ↓
4. Configurazione salvata in SQLite (MCPServerModel)
   ↓
5. Utente attiva toggle "Abilita MCP" (abilita auto modalità agentica)
   ↓
6. MCPClientManager carica config server attivi da DB
   ↓
7. Crea MultiServerMCPClient con configurazioni
   ↓
8. get_tools() ottiene tools async da client
   ↓
9. async_to_sync_tool() converte tools in sincroni
   ↓
10. Tools MCP combinati con tools standard in gui_utils.py
   ↓
11. Tutti i tools passati all'agent LangChain
   ↓
12. Agent esegue tools quando necessario
   ↓
13. Risultati tornano all'utente via GUI
```

---

## 5. Logica di Integrazione

### 5.1 Principi di Design

L'integrazione segue questi principi:

1. **Separazione delle Responsabilità**
   - `MCPClientManager`: Gestione client e configurazioni
   - `MCPToolIntegration`: Integrazione con sistema tools
   - `gui_mcp.py`: Interfaccia utente
   - `MCPServerModel`: Persistenza dati

2. **Singleton Pattern**
   - Un'unica istanza di `MCPClientManager` per l'applicazione
   - Evita connessioni duplicate ai server

3. **Lazy Loading**
   - Tools caricati solo quando necessario
   - Cache per evitare ricaricamenti

4. **Configurazione Dichiarativa**
   - Server definiti tramite dizionari di configurazione
   - Facile serializzazione/deserializzazione

### 5.2 Strategia di Implementazione

#### Fase 1: Modello Dati
```python
# src/models/mcp_server.py
class MCPServerModel(BaseModel):
    nome = CharField(primary_key=True)
    tipo = CharField()  # 'local' o 'remote'
    descrizione = TextField()
    configurazione = TextField()  # JSON
    attivo = BooleanField()
```

#### Fase 2: Manager Client
```python
# src/mcp/client.py
class MCPClientManager:
    def carica_configurazioni_da_db(self):
        # Legge da ConfigurazioneDB
        # Converte in formato MultiServerMCPClient
        
    def get_client(self):
        # Crea/ritorna MultiServerMCPClient
        
    async def get_tools(self):
        # Ottiene tools da tutti i server attivi
```

#### Fase 3: Integrazione Tools
```python
# src/tools/MCPTool.py
class MCPToolIntegration(Tool):
    def get_tool(self):
        # Ottiene tools da MCPClientManager
        # Ritorna lista compatibile con LangChain
```

#### Fase 4: GUI
```python
# src/mcp/gui_mcp.py
def mostra_gestione_mcp():
    # Form per aggiungere/modificare server
    # Visualizzazione server esistenti
    # Attivazione/disattivazione server
```

---

## 6. Modifiche al Codice

### 6.1 File Creati

#### 6.1.1 src/mcp/client.py (~170 righe)
**Scopo**: Wrapper per `MultiServerMCPClient` con integrazione database e conversione async→sync

**Componenti principali:**

**1. Funzione di conversione async→sync:**
```python
def async_to_sync_tool(async_tool: BaseTool) -> BaseTool:
    """
    Converte un tool async in un tool sincrono.
    Necessario perché langchain-mcp-adapters ritorna tools async,
    ma LangChain li chiama in modo sincrono.
    """
    if not hasattr(async_tool, 'coroutine'):
        return async_tool  # Già sincrono
    
    @wraps(async_tool.coroutine)
    def sync_wrapper(*args, **kwargs):
        return asyncio.run(async_tool.coroutine(*args, **kwargs))
    
    return StructuredTool(
        name=async_tool.name,
        description=async_tool.description,
        func=sync_wrapper,
        args_schema=async_tool.args_schema
    )
```

**2. Manager con caching intelligente:**
```python
class MCPClientManager:
    """Gestisce client MCP e configurazioni"""
    
    def __init__(self):
        self._client = None
        self._server_configs = {}
        self._tools_cache = []
        self._config_hash = None  # Per invalidare cache
    
    def carica_configurazioni_da_db(self):
        """Carica config da ConfigurazioneDB"""
        servers = ConfigurazioneDB.carica_mcp_servers_attivi()
        
        self._server_configs = {}
        for server in servers:
            if server['tipo'] == 'local':
                self._server_configs[server['nome']] = {
                    'transport': 'stdio',
                    'command': config['comando'],
                    'args': config['args'],
                    'env': config['env']
                }
            elif server['tipo'] == 'remote':
                self._server_configs[server['nome']] = {
                    'transport': 'http',
                    'url': config['url'],
                    'headers': config.get('headers', {})
                }
    
    def get_client(self):
        """Ottiene/crea MultiServerMCPClient"""
        if self._client is None:
            self._client = MultiServerMCPClient(
                self._server_configs
            )
        return self._client
    
    async def get_tools(self):
        """Ottiene tools con caching intelligente"""
        import json
        import hashlib
        
        # Calcola hash della configurazione
        config_str = json.dumps(self._server_configs, sort_keys=True)
        current_hash = hashlib.md5(config_str.encode()).hexdigest()
        
        # Usa cache se configurazione non è cambiata
        if self._config_hash == current_hash and self._tools_cache:
            return self._tools_cache
        
        # Carica tools da server
        client = self.get_client()
        async_tools = await client.get_tools()
        
        # Converti in sincroni
        sync_tools = [async_to_sync_tool(tool) for tool in async_tools]
        
        # Aggiorna cache
        self._tools_cache = sync_tools
        self._config_hash = current_hash
        
        return sync_tools
    
    def reset(self):
        """Resetta client e cache (chiamato dopo modifiche config)"""
        self._client = None
        self._tools_cache = []
        self._config_hash = None
```

**3. Funzione singleton:**
```python
_mcp_client_manager = None

def get_mcp_client_manager():
    global _mcp_client_manager
    if _mcp_client_manager is None:
        _mcp_client_manager = MCPClientManager()
    return _mcp_client_manager
```

**Caratteristiche chiave:**
- ✅ Conversione automatica async→sync per compatibilità LangChain
- ✅ Caching con hash MD5 per evitare ricaricamenti inutili
- ✅ Metodo `reset()` per invalidare cache dopo modifiche
- ✅ Supporto completo per server locali (stdio) e remoti (HTTP)

#### 6.1.2 src/mcp/gui_mcp.py (~340 righe)
**Scopo**: Dialog modale Streamlit per gestione server MCP

**Architettura:**
- Dialog modale (non sidebar) per UX coerente con sistema tools
- Layout a due colonne: lista server (sinistra) + configurazione (destra)
- Multiselect per attivazione/disattivazione server
- Form inline per aggiungere/modificare server

**Funzioni principali:**

**1. Callback chiusura dialog:**
```python
def _on_close_mcp_dialog():
    """
    Chiamato quando dialog viene chiusa.
    Salva le selezioni del multiselect nel DB.
    """
    st.session_state["mcp_dialog_open"] = False
    
    if "mcp_servers_selezionati_temp" in st.session_state:
        servers_selezionati = st.session_state["mcp_servers_selezionati_temp"]
        ConfigurazioneDB.aggiorna_stati_mcp_servers(servers_selezionati)
        
        # Resetta manager per ricaricare config
        manager = get_mcp_client_manager()
        manager.reset()
```

**2. Dialog principale:**
```python
@st.dialog(
    "🔌 Configurazione Server MCP",
    width="large",
    dismissible=True,
    on_dismiss=lambda: _on_close_mcp_dialog()
)
def mostra_dialog_mcp():
    """Dialog per configurare server MCP"""
    st.caption("Configura i server MCP per estendere le capacità dell'agent")
    
    # Carica server dal DB
    servers_db = ConfigurazioneDB.carica_mcp_servers()
    servers_dict = {s["nome"]: s for s in servers_db}
    
    # Layout a due colonne
    col_left, col_right = st.columns([1, 2])
    
    with col_left:
        # LISTA SERVER con ricerca e multiselect
        st.subheader("📋 Server Disponibili")
        search_filter = st.text_input("🔍 Cerca server")
        
        # Multiselect per attivazione
        servers_attivi = [s["nome"] for s in servers_db if s["attivo"]]
        servers_selezionati = st.multiselect(
            "Server attivi",
            options=list(servers_dict.keys()),
            default=servers_attivi,
            key="mcp_servers_selezionati_temp"
        )
        
        # Pulsante aggiungi
        if st.button("➕ Aggiungi Nuovo Server"):
            st.session_state["selected_mcp_server"] = "__new__"
    
    with col_right:
        # CONFIGURAZIONE SERVER
        if st.session_state.get("selected_mcp_server"):
            _mostra_form_configurazione_server(servers_dict)
```

**3. Form configurazione:**
```python
def _mostra_form_configurazione_server(servers_dict):
    """Form per aggiungere/modificare server"""
    selected = st.session_state["selected_mcp_server"]
    
    if selected == "__new__":
        st.subheader("➕ Nuovo Server MCP")
        server_data = {}
    else:
        st.subheader(f"✏️ Modifica: {selected}")
        server_data = servers_dict[selected]
    
    # Form fields
    nome = st.text_input("Nome", value=server_data.get("nome", ""))
    tipo = st.selectbox("Tipo", ["local", "remote"],
                        index=0 if server_data.get("tipo") == "local" else 1)
    
    if tipo == "local":
        comando = st.text_input("Comando", value=config.get("comando", ""))
        args = st.text_area("Argomenti (uno per riga)",
                            value="\n".join(config.get("args", [])))
        env = st.text_area("Variabili d'ambiente (KEY=value)",
                           value="\n".join([f"{k}={v}" for k,v in config.get("env", {}).items()]))
    else:
        url = st.text_input("URL", value=config.get("url", ""))
        headers = st.text_area("Headers HTTP (KEY: value)",
                               value="\n".join([f"{k}: {v}" for k,v in config.get("headers", {}).items()]))
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Salva", use_container_width=True):
            # Salva nel DB
            ConfigurazioneDB.salva_mcp_server(...)
            st.success("✅ Server salvato!")
            st.session_state["selected_mcp_server"] = None
    
    with col2:
        if st.button("❌ Annulla", use_container_width=True):
            st.session_state["selected_mcp_server"] = None
```

**Caratteristiche chiave:**
- ✅ Dialog modale invece di sidebar per UX migliore
- ✅ Multiselect per attivazione rapida di più server
- ✅ Ricerca/filtro server per liste lunghe
- ✅ Form inline per configurazione immediata
- ✅ Callback `on_dismiss` per salvare automaticamente
- ✅ Reset automatico del manager dopo modifiche

#### 6.1.3 src/models/mcp_server.py
**Scopo**: Modello Peewee per persistenza

```python
class MCPServerModel(BaseModel):
    nome = CharField(primary_key=True, max_length=100)
    tipo = CharField(max_length=20)
    descrizione = TextField(default='')
    configurazione = TextField()  # JSON
    attivo = BooleanField(default=True)
    
    def get_configurazione(self):
        return json.loads(self.configurazione)
    
    def set_configurazione(self, config_dict):
        self.configurazione = json.dumps(
            config_dict, 
            ensure_ascii=False
        )
```

### 6.2 File Modificati

#### 6.2.1 src/tools/MCPTool.py
**NOTA IMPORTANTE**: Questo file è stato **ELIMINATO** nell'implementazione finale!

**Motivo**: Creava confusione apparendo come un tool nella lista tools, quando in realtà MCP è un sistema di integrazione, non un tool singolo.

**Soluzione adottata**: Integrazione diretta in `gui_utils.py` senza passare per il sistema tools.

**Prima** (con MCPTool.py - DEPRECATO):
```python
class MCPToolIntegration(Tool):
    def __init__(self):
        super().__init__(nome="MCP", ...)
        self._manager = get_mcp_client_manager()
    
    def get_tool(self):
        self._manager.carica_configurazioni_da_db()
        return asyncio.run(self._manager.get_tools())
```

**Dopo** (integrazione diretta in gui_utils.py - ATTUALE):
```python
# In gui_utils.py, funzione _carica_tools_nei_provider()
def _carica_tools_nei_provider(provider_name):
    tools_to_use = []
    
    # 1. Carica tools standard
    tools_attivi = ConfigurazioneDB.carica_tools_attivi()
    for tool_config in tools_attivi:
        tool_instance = tools_disponibili[tool_config['nome_tool']]
        tools_to_use.extend(tool_instance.get_tool())
    
    # 2. Carica tools MCP se toggle attivo
    if st.session_state.get("mcp_enabled", False):
        try:
            manager = get_mcp_client_manager()
            manager.carica_configurazioni_da_db()
            mcp_tools = asyncio.run(manager.get_tools())
            tools_to_use.extend(mcp_tools)
        except Exception as e:
            st.error(f"Errore caricamento tools MCP: {e}")
    
    return tools_to_use
```

**Vantaggi dell'approccio attuale:**
- ✅ MCP non appare nella lista tools (era confusionario)
- ✅ Toggle dedicato "Abilita MCP" separato dai tools
- ✅ Gestione errori più chiara
- ✅ Codice più semplice e diretto

#### 6.2.2 src/ConfigurazioneDB.py (linee 485-595)
**Aggiunte**: Metodi CRUD completi per server MCP

```python
class ConfigurazioneDB:
    # ... metodi esistenti ...
    
    @classmethod
    def salva_mcp_server(cls, nome, tipo, descrizione, 
                         configurazione, attivo):
        """Salva configurazione server MCP"""
        server, created = MCPServerModel.get_or_create(
            nome=nome,
            defaults={
                'tipo': tipo,
                'descrizione': descrizione,
                'configurazione': json.dumps(configurazione),
                'attivo': attivo
            }
        )
        if not created:
            server.tipo = tipo
            server.descrizione = descrizione
            server.set_configurazione(configurazione)
            server.attivo = attivo
            server.save()
    
    @classmethod
    def carica_mcp_servers(cls):
        """Carica tutti i server MCP (attivi e non)"""
        servers = MCPServerModel.select()
        return [{
            'nome': s.nome,
            'tipo': s.tipo,
            'descrizione': s.descrizione,
            'configurazione': json.loads(s.configurazione),
            'attivo': s.attivo
        } for s in servers]
    
    @classmethod
    def carica_mcp_servers_attivi(cls):
        """Carica solo server attivi"""
        servers = MCPServerModel.select().where(
            MCPServerModel.attivo == True
        )
        return [{
            'nome': s.nome,
            'tipo': s.tipo,
            'descrizione': s.descrizione,
            'configurazione': json.loads(s.configurazione),
            'attivo': s.attivo
        } for s in servers]
    
    @classmethod
    def carica_mcp_server(cls, nome):
        """Carica un singolo server per nome"""
        try:
            server = MCPServerModel.get(MCPServerModel.nome == nome)
            return {
                'nome': server.nome,
                'tipo': server.tipo,
                'descrizione': server.descrizione,
                'configurazione': json.loads(server.configurazione),
                'attivo': server.attivo
            }
        except MCPServerModel.DoesNotExist:
            return None
    
    @classmethod
    def cancella_mcp_server(cls, nome):
        """Elimina un server MCP"""
        query = MCPServerModel.delete().where(
            MCPServerModel.nome == nome
        )
        return query.execute()
    
    @classmethod
    def aggiorna_stati_mcp_servers(cls, nomi_servers_attivi):
        """
        Aggiorna lo stato attivo/disattivo dei server.
        Usato dal multiselect nella GUI.
        """
        # Disattiva tutti
        MCPServerModel.update(attivo=False).execute()
        
        # Attiva solo quelli selezionati
        if nomi_servers_attivi:
            MCPServerModel.update(attivo=True).where(
                MCPServerModel.nome.in_(nomi_servers_attivi)
            ).execute()
```

**Metodi chiave:**
- `salva_mcp_server()`: Crea o aggiorna server
- `carica_mcp_servers()`: Tutti i server (per GUI)
- `carica_mcp_servers_attivi()`: Solo attivi (per client)
- `aggiorna_stati_mcp_servers()`: Gestione multiselect
- `cancella_mcp_server()`: Eliminazione server

#### 6.2.3 src/gui_utils.py (linee 79, 260-270, 513-580)
**Modifiche**: Integrazione MCP e gestione toggle

**1. Pulizia tool "MCP" obsoleto (linea 79):**
```python
def _inizializza_tools():
    """Inizializza tools e pulisce eventuali tool obsoleti"""
    tools_disponibili = Loader.discover_tools()
    
    # Rimuovi tool "MCP" se presente (obsoleto)
    if "MCP" in tools_disponibili:
        del tools_disponibili["MCP"]
        # Pulisci anche dal DB
        try:
            ConfigurazioneDB.cancella_tool("MCP")
        except:
            pass
    
    return tools_disponibili
```

**2. Caricamento tools MCP (linee 260-270):**
```python
def _carica_tools_nei_provider(provider_name):
    """Carica tools standard + MCP se attivo"""
    tools_to_use = []
    risultato = {'errors': []}
    
    # Carica tools standard
    tools_attivi = ConfigurazioneDB.carica_tools_attivi()
    for tool_config in tools_attivi:
        # ... carica tool standard ...
    
    # Carica tools MCP se toggle attivo
    if st.session_state.get("mcp_enabled", False):
        try:
            manager = get_mcp_client_manager()
            manager.carica_configurazioni_da_db()
            mcp_tools = asyncio.run(manager.get_tools())
            tools_to_use.extend(mcp_tools)
        except Exception as e:
            error_msg = f"Errore caricamento tools MCP: {str(e)}"
            risultato['errors'].append(error_msg)
    
    return {'tools': tools_to_use, 'errors': risultato['errors']}
```

**3. Toggle MCP con dipendenze (linee 513-541):**
```python
# Toggle Modalità Agentica
modalita_agentica = st.toggle("Abilita Modalità Agentica", ...)

# Toggle MCP (richiede modalità agentica)
def on_toggle_mcp():
    # Se abilito MCP, abilito automaticamente anche modalità agentica
    if st.session_state.get("mcp_enabled", False):
        if not st.session_state[provider_scelto][agentic_key]:
            st.session_state[agentic_key] = True
            st.session_state[provider_scelto][agentic_key] = True
    
    # Ricarica tools
    risultato = _carica_tools_nei_provider(provider_name=provider_scelto)
    if risultato['errors']:
        st.session_state["tools_loading_errors"] = risultato['errors']

# MCP disabilitato se modalità agentica è off
mcp_disabled = not modalita_agentica
mcp_enabled = st.toggle("Abilita MCP",
               value=st.session_state.get("mcp_enabled", False) and modalita_agentica,
               key="mcp_enabled",
               on_change=on_toggle_mcp,
               disabled=mcp_disabled,
               help="Abilita i tools dai server MCP attivi (richiede modalità agentica)")
```

**4. Pulsanti configurazione (linee 544-553):**
```python
# Pulsanti affiancati per Tools e MCP
col_tools, col_mcp = st.columns(2)

with col_tools:
    if st.button("⚙️ Configura Tools", use_container_width=True):
        st.session_state["tools_dialog_open"] = True

with col_mcp:
    if st.button("🔌 Configura MCP", use_container_width=True):
        st.session_state["mcp_dialog_open"] = True
```

**5. Expander server MCP attivi (linee 565-573):**
```python
if st.session_state.get("mcp_enabled", False):
    servers_mcp_attivi = ConfigurazioneDB.carica_mcp_servers_attivi()
    if servers_mcp_attivi:
        with st.expander("🔌 Server MCP attivi", expanded=False):
            for server in servers_mcp_attivi:
                tipo_icon = "💻" if server['tipo'] == 'local' else "🌐"
                st.write(f"{tipo_icon} **{server['nome']}** ({server['tipo']})")
```

#### 6.2.4 src/models/__init__.py
**Aggiunta**: Import del nuovo modello

```python
from .mcp_server import MCPServerModel

__all__ = [
    # ... altri modelli ...
    'MCPServerModel',
]
```

#### 6.2.5 src/models/base.py
**Aggiunta**: Registrazione modello per creazione tabelle

```python
def create_tables():
    """Crea tutte le tabelle nel database"""
    db.create_tables([
        # ... altri modelli ...
        MCPServerModel,
    ])

def drop_tables():
    """Elimina tutte le tabelle dal database"""
    db.drop_tables([
        # ... altri modelli ...
        MCPServerModel,
    ])
```

#### 6.2.6 pyproject.toml
**Aggiunta**: Nuova dipendenza

```toml
dependencies = [
    # ... altre dipendenze ...
    "langchain-mcp-adapters>=0.1.0",
]
```

### 6.3 File Eliminati

**Dopo il refactoring con `langchain-mcp-adapters`:**

1. `src/mcp/base.py` (~180 righe) - Implementazione custom protocollo MCP
2. `src/mcp/local.py` (~360 righe) - Client stdio custom
3. `src/mcp/remote.py` (~350 righe) - Client HTTP custom
4. `src/mcp/loader.py` (~340 righe) - Loader custom per server MCP
5. `src/tools/MCPTool.py` (~92 righe) - Tool wrapper (causava confusione)

**Totale eliminato**: ~1322 righe di codice custom

**Sostituito con**: ~170 righe in `src/mcp/client.py` + ~340 righe in `src/mcp/gui_mcp.py` = ~510 righe

**Rapporto**: 1322 righe → 510 righe = **61% di riduzione del codice** 🎉

**Benefici aggiuntivi:**
- ✅ Codice più manutenibile (usa libreria standard)
- ✅ Meno bug potenziali
- ✅ Aggiornamenti automatici con langchain-mcp-adapters
- ✅ Migliore compatibilità con ecosistema LangChain

---

## 7. Integrazione Tools LangChain-MCP

### 7.1 Conversione Automatica con Wrapper Async→Sync

`langchain-mcp-adapters` converte automaticamente tools MCP in tools LangChain, ma ritorna tools **async**. DapaBot aggiunge un wrapper per convertirli in **sync**:

```
┌─────────────────────┐
│   MCP Tool          │
│                     │
│ {                   │
│   name: "somma",    │
│   description: "...",│
│   inputSchema: {...}│
│ }                   │
└──────────┬──────────┘
           │
           │ MultiServerMCPClient.get_tools()
           │
           ▼
┌─────────────────────┐
│ LangChain BaseTool  │
│ (ASYNC)             │
│                     │
│ class SommaTool:    │
│   name = "somma"    │
│   description = "..."│
│   args_schema = ... │
│   async def _arun():│
│     # Async MCP     │
└──────────┬──────────┘
           │
           │ async_to_sync_tool()
           │ (src/mcp/client.py)
           │
           ▼
┌─────────────────────┐
│ LangChain BaseTool  │
│ (SYNC)              │
│                     │
│ class SommaTool:    │
│   name = "somma"    │
│   description = "..."│
│   args_schema = ... │
│   def _run(...):    │
│     # asyncio.run() │
└─────────────────────┘
```

**Problema risolto**: LangChain chiama i tools in modo sincrono, ma `langchain-mcp-adapters` ritorna tools async. Il wrapper `async_to_sync_tool()` risolve questa incompatibilità usando `asyncio.run()`.

### 7.2 Schema degli Argomenti

La conversione degli schemi JSON in modelli Pydantic è automatica:

**MCP Tool Schema:**
```json
{
  "name": "search",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "Search query"
      },
      "limit": {
        "type": "integer",
        "description": "Max results"
      }
    },
    "required": ["query"]
  }
}
```

**LangChain Tool (generato automaticamente):**
```python
class SearchToolArgs(BaseModel):
    query: str = Field(description="Search query")
    limit: Optional[int] = Field(
        default=None, 
        description="Max results"
    )

class SearchTool(BaseTool):
    name = "search"
    args_schema = SearchToolArgs
    
    def _run(self, query: str, limit: Optional[int] = None):
        # Esegue chiamata MCP
```

### 7.3 Esecuzione Tools

#### 7.3.1 Flusso di Esecuzione

```
1. Agent decide di usare tool "search"
   ↓
2. LangChain valida argomenti con Pydantic
   ↓
3. Tool wrapper chiama MultiServerMCPClient
   ↓
4. Client invia richiesta JSON-RPC al server MCP
   ↓
5. Server MCP esegue tool
   ↓
6. Risposta torna al client
   ↓
7. Client converte risposta in formato LangChain
   ↓
8. Risultato ritorna all'agent
```

#### 7.3.2 Esempio Pratico

**Configurazione Server:**
```python
# Server locale che espone tool "add"
{
    "math": {
        "transport": "stdio",
        "command": "python",
        "args": ["math_server.py"]
    }
}
```

**Server MCP (math_server.py):**
```python
from fastmcp import FastMCP

mcp = FastMCP("Math")

@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b

if __name__ == "__main__":
    mcp.run(transport="stdio")
```

**Uso in DapaBot:**
```python
# 1. Configurazione caricata da DB
manager = get_mcp_client_manager()
manager.carica_configurazioni_da_db()

# 2. Tools ottenuti
tools = await manager.get_tools()
# tools = [AddTool(name="math_add", ...)]

# 3. Agent creato con tools
agent = create_agent("gpt-4", tools)

# 4. Esecuzione
response = await agent.ainvoke({
    "messages": [{"role": "user", "content": "what's 5 + 3?"}]
})
# Agent usa automaticamente il tool math_add
```

### 7.4 Gestione Errori

```python
# Gli errori MCP sono gestiti automaticamente
try:
    result = await tool._arun(query="test")
except Exception as e:
    # Errore convertito in messaggio per l'agent
    return f"Tool execution failed: {str(e)}"
```

### 7.5 Contenuto Multimodale

I tools MCP possono ritornare contenuto multimodale (testo, immagini, ecc.):

```python
# Tool MCP ritorna immagine
{
    "content": [
        {"type": "text", "text": "Screenshot taken"},
        {"type": "image", "data": "base64...", "mimeType": "image/png"}
    ]
}

# Convertito automaticamente in content_blocks LangChain
message.content_blocks = [
    {"type": "text", "text": "Screenshot taken"},
    {"type": "image", "base64": "...", "mime_type": "image/png"}
]
```

---

## 8. Guida Utente GUI

### 8.1 Accesso alla Gestione MCP

Ci sono **due modi** per accedere alla gestione dei server MCP:

#### Metodo 1: Pulsante nell'Expander Modalità Agentica (Consigliato)

1. Avviare DapaBot: `streamlit run dapabot.py`
2. Nella sidebar, aprire l'expander **"🤖 Modalità Agentica"**
3. Click sul pulsante **"🔌 Configura MCP"**

```
┌─────────────────────────────────┐
│ 🤖 DapaBot                      │
│                                 │
│ [Provider Selection]            │
│ [Model Selection]               │
│                                 │
│ ▼ 🤖 Modalità Agentica          │
│   ☑ Abilita Modalità Agentica  │
│                                 │
│   [⚙️ Configura] [🔌 Configura]│ ← Click qui
│   [   Tools    ] [    MCP     ]│
│                                 │
│   📋 Dettagli tools attivi      │
└─────────────────────────────────┘
```

**Vantaggi:**
- Accesso rapido durante la configurazione della modalità agentica
- Pulsanti Tools e MCP affiancati per comodità
- Contestuale all'uso dei tools

#### Metodo 2: Sezione Dedicata nella Sidebar (Deprecato)

**Nota**: Questo metodo è ancora disponibile ma verrà rimosso in future versioni. Si consiglia di usare il Metodo 1.

1. Avviare DapaBot: `streamlit run dapabot.py`
2. Nella sidebar, scorrere fino alla sezione **"🔌 Server MCP"**

```
┌─────────────────────────┐
│ 🤖 DapaBot              │
│                         │
│ [Provider Selection]    │
│ [Model Selection]       │
│                         │
│ ─────────────────────── │
│ 🔌 Server MCP           │ ← Sezione MCP
│                         │
│ [Server configurati]    │
│ [➕ Aggiungi Server]    │
└─────────────────────────┘
```

### 8.2 Aggiungere un Server MCP Remoto

#### Passo 1: Aprire il Form
Click su **"➕ Aggiungi Server MCP"**

#### Passo 2: Compilare i Campi

```
┌─────────────────────────────────┐
│ ➕ Nuovo Server MCP             │
├─────────────────────────────────┤
│ Nome: [weather-api____________] │
│                                 │
│ Tipo: [Remote ▼]                │
│                                 │
│ Descrizione:                    │
│ ┌─────────────────────────────┐ │
│ │ Server meteo via API        │ │
│ └─────────────────────────────┘ │
│                                 │
│ ── Configurazione Server ────── │
│                                 │
│ URL:                            │
│ [https://api.weather.com/mcp__] │
│                                 │
│ API Key:                        │
│ [••••••••••••••••••••••••••••] │
│                                 │
│ Headers HTTP:                   │
│ ┌─────────────────────────────┐ │
│ │ X-Custom-Header: value      │ │
│ └─────────────────────────────┘ │
│                                 │
│ ☑ Attivo                        │
│                                 │
│ [💾 Salva]  [❌ Annulla]        │
└─────────────────────────────────┘
```

**Campi obbligatori:**
- **Nome**: Identificatore univoco (es. "weather-api")
- **URL**: Endpoint del server MCP (es. "https://api.weather.com/mcp")

**Campi opzionali:**
- **API Key**: Token di autenticazione
- **Headers HTTP**: Headers personalizzati (formato `Chiave: valore`, uno per riga)
- **Descrizione**: Descrizione testuale del server

#### Passo 3: Salvare
Click su **"💾 Salva"**

Il server viene:
1. Salvato nel database SQLite
2. Registrato nel `MCPClientManager`
3. Visualizzato nella lista server

### 8.3 Aggiungere un Server MCP Locale

#### Passo 1: Aprire il Form
Click su **"➕ Aggiungi Server MCP"**

#### Passo 2: Compilare i Campi

```
┌─────────────────────────────────┐
│ ➕ Nuovo Server MCP             │
├─────────────────────────────────┤
│ Nome: [filesystem_____________] │
│                                 │
│ Tipo: [Local ▼]                 │
│                                 │
│ Descrizione:                    │
│ ┌─────────────────────────────┐ │
│ │ Accesso al filesystem       │ │
│ └─────────────────────────────┘ │
│                                 │
│ ── Configurazione Server ────── │
│                                 │
│ Comando:                        │
│ [npx_________________________] │
│                                 │
│ Argomenti:                      │
│ [-y @modelcontextprotocol/___] │
│ [server-filesystem /home/user] │
│                                 │
│ Variabili d'ambiente:           │
│ ┌─────────────────────────────┐ │
│ │ DEBUG=true                  │ │
│ │ LOG_LEVEL=info              │ │
│ └─────────────────────────────┘ │
│                                 │
│ ☑ Attivo                        │
│                                 │
│ [💾 Salva]  [❌ Annulla]        │
└─────────────────────────────────┘
```

**Campi obbligatori:**
- **Nome**: Identificatore univoco (es. "filesystem")
- **Comando**: Eseguibile per avviare il server (es. "npx", "python", "node")
- **Argomenti**: Argomenti del comando, separati da spazio

**Campi opzionali:**
- **Variabili d'ambiente**: Formato `CHIAVE=valore`, una per riga
- **Descrizione**: Descrizione testuale del server

#### Passo 3: Salvare
Click su **"💾 Salva"**

### 8.4 Configurare un Server Esistente

#### Passo 1: Trovare il Server
Nella sezione **"Server configurati"**, individuare il server da modificare

```
┌─────────────────────────────────┐
│ Server configurati:             │
├─────────────────────────────────┤
│ ▼ 🟢 weather-api (remote)       │
│   Stato: Attivo                 │
│   Server meteo via API          │
│                                 │
│   [⚙️]  [🗑️]                    │
└─────────────────────────────────┘
```

#### Passo 2: Aprire Modifica
Click sull'icona **⚙️** (ingranaggio)

#### Passo 3: Modificare i Campi
Il form si apre pre-compilato con i valori attuali:

```
┌─────────────────────────────────┐
│ ✏️ Modifica Server: weather-api │
├─────────────────────────────────┤
│ Nome: weather-api (bloccato)    │
│                                 │
│ Tipo: [Remote ▼]                │
│                                 │
│ [Campi modificabili...]         │
│                                 │
│ [💾 Salva]  [❌ Annulla]        │
└─────────────────────────────────┘
```

**Note:**
- Il **Nome** non può essere modificato (è la chiave primaria)
- Tutti gli altri campi sono modificabili

#### Passo 4: Salvare
Click su **"💾 Salva"**

Le modifiche sono applicate immediatamente.

### 8.5 Abilitare Server MCP in Modalità Agentica

#### Prerequisiti
1. Almeno un server MCP configurato e attivo
2. Modalità agentica abilitata

#### Passo 1: Attivare Modalità Agentica
Nella sidebar principale:

```
┌─────────────────────────────────┐
│ Modalità                        │
│ ☑ Modalità Agentica             │ ← Attivare
└─────────────────────────────────┘
```

#### Passo 2: Verificare Server Attivi
Nella sezione **"🔌 Server MCP"**:

```
┌─────────────────────────────────┐
│ Server configurati:             │
├─────────────────────────────────┤
│ ▼ 🟢 weather-api (remote)       │ ← Verde = Attivo
│   Stato: Attivo                 │
│                                 │
│ ▼ ⚪ filesystem (local)          │ ← Bianco = Disattivo
│   Stato: Disattivato            │
└─────────────────────────────────┘
```

**Legenda icone:**
- 🟢 Verde: Server attivo, tools disponibili
- ⚪ Bianco: Server disattivato, tools non disponibili

#### Passo 3: Attivare/Disattivare Server
Per modificare lo stato:
1. Click su **⚙️** (modifica)
2. Modificare checkbox **"☑ Attivo"**
3. Salvare

#### Passo 4: Verificare Tools Disponibili
I tools MCP sono automaticamente disponibili all'agent quando:
- Modalità agentica è attiva
- Almeno un server MCP è attivo
- Il server ha tools configurati

**Esempio di utilizzo:**
```
Utente: "Qual è il meteo a Roma?"

Agent (interno):
1. Identifica necessità di tool "get_weather"
2. Trova tool da server "weather-api"
3. Esegue: get_weather(city="Roma")
4. Riceve risultato
5. Formula risposta

Risposta: "A Roma oggi ci sono 22°C con cielo sereno."
```

### 8.6 Eliminare un Server

#### Passo 1: Trovare il Server
Nella lista server configurati

#### Passo 2: Click su Elimina
Click sull'icona **🗑️** (cestino)

#### Passo 3: Conferma
Il server viene eliminato immediatamente da:
- Database SQLite
- `MCPClientManager`
- Lista visualizzata

**Attenzione:** L'eliminazione è permanente e non può essere annullata.

### 8.7 Risoluzione Problemi Comuni

#### Server non si connette
**Sintomo:** Icona ⚪ bianca invece di 🟢 verde

**Soluzioni:**
1. **Server locale:**
   - Verificare che il comando sia corretto
   - Verificare che il server sia installato
   - Controllare i log per errori

2. **Server remoto:**
   - Verificare URL corretto
   - Verificare connessione di rete
   - Verificare API key se richiesta

#### Tools non disponibili
**Sintomo:** Agent non usa tools MCP

**Soluzioni:**
1. Verificare modalità agentica attiva
2. Verificare server attivo (🟢)
3. Verificare che il server esponga tools
4. Riavviare l'applicazione

#### Errori di configurazione
**Sintomo:** Errore al salvataggio

**Soluzioni:**
1. Verificare campi obbligatori compilati
2. Verificare formato corretto (es. URL valido)
3. Verificare nome univoco (non duplicato)

---

## 9. Estensioni Future

### 9.1 Funzionalità Pianificate

#### 9.1.1 Gestione Resources
**Obiettivo:** Permettere l'accesso a risorse MCP (file, database, API)

**Implementazione:**
```python
# In MCPClientManager
async def get_resources(self, server_name, uris=None):
    """Carica resources da server MCP"""
    client = self.get_client()
    return await client.get_resources(server_name, uris)

# In GUI
def mostra_resources_browser():
    """Browser per esplorare resources disponibili"""
    server = st.selectbox("Server", server_names)
    resources = asyncio.run(manager.get_resources(server))
    
    for resource in resources:
        with st.expander(resource.name):
            st.write(resource.description)
            if st.button("Carica", key=resource.uri):
                content = asyncio.run(
                    manager.leggi_resource(server, resource.uri)
                )
                st.write(content)
```

**Casi d'uso:**
- Accesso a file di configurazione
- Lettura database
- Recupero dati da API

#### 9.1.2 Gestione Prompts
**Obiettivo:** Utilizzare prompt template da server MCP

**Implementazione:**
```python
# In MCPClientManager
async def get_prompt(self, server_name, prompt_name, args=None):
    """Carica prompt da server MCP"""
    client = self.get_client()
    return await client.get_prompt(
        server_name, 
        prompt_name, 
        arguments=args
    )

# In GUI
def mostra_prompt_selector():
    """Selettore di prompt MCP"""
    server = st.selectbox("Server", server_names)
    prompts = asyncio.run(manager.list_prompts(server))
    
    prompt_name = st.selectbox("Prompt", prompts)
    
    if st.button("Usa Prompt"):
        messages = asyncio.run(
            manager.get_prompt(server, prompt_name)
        )
        # Inserisci messages nella chat
```

**Casi d'uso:**
- Template di prompt riutilizzabili
- Prompt specializzati per domini
- Prompt con parametri dinamici

#### 9.1.3 Interceptors Personalizzati
**Obiettivo:** Permettere configurazione di interceptors via GUI

**Implementazione:**
```python
# Interceptors predefiniti
INTERCEPTORS = {
    "auth": auth_interceptor,
    "retry": retry_interceptor,
    "logging": logging_interceptor,
    "rate_limit": rate_limit_interceptor
}

# In GUI
def configura_interceptors(server_name):
    """Configura interceptors per server"""
    st.subheader("Interceptors")
    
    selected = st.multiselect(
        "Interceptors attivi",
        options=list(INTERCEPTORS.keys())
    )
    
    # Configurazione parametri per ogni interceptor
    for name in selected:
        with st.expander(f"Configura {name}"):
            if name == "retry":
                max_retries = st.number_input("Max retries", 1, 10, 3)
                delay = st.number_input("Delay (s)", 0.1, 10.0, 1.0)
            # ... altri parametri
```

**Casi d'uso:**
- Retry automatico su errori
- Logging centralizzato
- Rate limiting
- Autenticazione dinamica

#### 9.1.4 Monitoring e Metriche
**Obiettivo:** Dashboard per monitorare uso server MCP

**Implementazione:**
```python
# Modello per metriche
class MCPMetrics(BaseModel):
    server_name = CharField()
    tool_name = CharField()
    timestamp = DateTimeField()
    duration_ms = IntegerField()
    success = BooleanField()
    error_message = TextField(null=True)

# Callback per raccolta metriche
async def metrics_callback(request, handler):
    start = time.time()
    try:
        result = await handler(request)
        success = True
        error = None
    except Exception as e:
        success = False
        error = str(e)
        raise
    finally:
        duration = (time.time() - start) * 1000
        MCPMetrics.create(
            server_name=request.server_name,
            tool_name=request.name,
            timestamp=datetime.now(),
            duration_ms=duration,
            success=success,
            error_message=error
        )

# Dashboard
def mostra_dashboard_mcp():
    """Dashboard metriche MCP"""
    st.title("📊 Dashboard MCP")
    
    # Statistiche generali
    col1, col2, col3 = st.columns(3)
    col1.metric("Tools eseguiti", total_calls)
    col2.metric("Successi", success_rate)
    col3.metric("Tempo medio", avg_duration)
    
    # Grafico chiamate nel tempo
    st.line_chart(calls_over_time)
    
    # Tabella errori recenti
    st.dataframe(recent_errors)
```

**Metriche raccolte:**
- Numero chiamate per tool
- Tempo di esecuzione
- Tasso di successo/errore
- Errori più frequenti

#### 9.1.5 Cache Risultati
**Obiettivo:** Cache intelligente per ridurre chiamate ripetute

**Implementazione:**
```python
from functools import lru_cache
import hashlib

class CachedMCPClient:
    def __init__(self, client, cache_ttl=300):
        self.client = client
        self.cache = {}
        self.cache_ttl = cache_ttl
    
    def _cache_key(self, server, tool, args):
        """Genera chiave cache"""
        key_str = f"{server}:{tool}:{json.dumps(args, sort_keys=True)}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    async def execute_tool(self, server, tool, args):
        """Esegue tool con cache"""
        key = self._cache_key(server, tool, args)
        
        # Controlla cache
        if key in self.cache:
            cached, timestamp = self.cache[key]
            if time.time() - timestamp < self.cache_ttl:
                return cached
        
        # Esegui e salva in cache
        result = await self.client.esegui_tool(server, tool, args)
        self.cache[key] = (result, time.time())
        return result
```

**Configurazione GUI:**
```python
def configura_cache(server_name):
    """Configura cache per server"""
    enable_cache = st.checkbox("Abilita cache")
    
    if enable_cache:
        ttl = st.slider("TTL (secondi)", 60, 3600, 300)
        max_size = st.number_input("Max entries", 10, 1000, 100)
        
        # Whitelist/blacklist tools
        st.multiselect("Tools da cachare", all_tools)
```

#### 9.1.6 Autenticazione Avanzata
**Obiettivo:** Supporto per OAuth2, JWT, etc.

**Implementazione:**
```python
from langchain_mcp_adapters.auth import OAuth2Auth

# Configurazione OAuth2
auth_config = {
    "type": "oauth2",
    "client_id": "...",
    "client_secret": "...",
    "token_url": "https://auth.example.com/token",
    "scopes": ["read", "write"]
}

# In MCPClientManager
def _create_auth(self, config):
    """Crea oggetto auth basato su config"""
    if config["type"] == "oauth2":
        return OAuth2Auth(
            client_id=config["client_id"],
            client_secret=config["client_secret"],
            token_url=config["token_url"],
            scopes=config["scopes"]
        )
    elif config["type"] == "jwt":
        return JWTAuth(...)
    # ... altri tipi
```

### 9.2 Architettura Estendibile

#### 9.2.1 Plugin System
**Obiettivo:** Permettere estensioni di terze parti

```python
# Plugin interface
class MCPPlugin(ABC):
    @abstractmethod
    def on_server_added(self, server_config):
        """Chiamato quando un server viene aggiunto"""
        pass
    
    @abstractmethod
    def on_tool_executed(self, server, tool, result):
        """Chiamato dopo esecuzione tool"""
        pass

# Plugin manager
class PluginManager:
    def __init__(self):
        self.plugins = []
    
    def register(self, plugin: MCPPlugin):
        self.plugins.append(plugin)
    
    def notify_server_added(self, config):
        for plugin in self.plugins:
            plugin.on_server_added(config)
```

**Esempio plugin:**
```python
class SlackNotificationPlugin(MCPPlugin):
    """Invia notifiche Slack per eventi MCP"""
    
    def on_tool_executed(self, server, tool, result):
        if result.error:
            send_slack_message(
                f"❌ Tool {tool} failed on {server}: {result.error}"
            )
```

#### 9.2.2 Custom Transports
**Obiettivo:** Supporto per trasporti personalizzati

```python
# Transport interface
class CustomTransport(ABC):
    @abstractmethod
    async def connect(self):
        pass
    
    @abstractmethod
    async def send(self, message):
        pass
    
    @abstractmethod
    async def receive(self):
        pass

# Esempio: WebSocket transport
class WebSocketTransport(CustomTransport):
    def __init__(self, url):
        self.url = url
        self.ws = None
    
    async def connect(self):
        self.ws = await websockets.connect(self.url)
    
    async def send(self, message):
        await self.ws.send(json.dumps(message))
    
    async def receive(self):
        data = await self.ws.recv()
        return json.loads(data)
```

### 9.3 Roadmap

#### Q2 2026
- ✅ Supporto base MCP (tools)
- ✅ GUI configurazione
- ✅ Persistenza database
- 🔄 Resources support
- 🔄 Prompts support

#### Q3 2026
- 📋 Interceptors personalizzati
- 📋 Monitoring e metriche
- 📋 Cache risultati
- 📋 Autenticazione avanzata

#### Q4 2026
- 📋 Plugin system
- 📋 Custom transports
- 📋 Dashboard analytics
- 📋 Export/import configurazioni

**Legenda:**
- ✅ Completato
- 🔄 In sviluppo
- 📋 Pianificato

---

## 10. Riferimenti

### 10.1 Documentazione

- **MCP Specification**: https://modelcontextprotocol.io/specification
- **LangChain MCP Docs**: https://docs.langchain.com/oss/python/langchain/mcp
- **langchain-mcp-adapters**: https://github.com/langchain-ai/langchain-mcp-adapters
- **FastMCP**: https://gofastmcp.com/getting-started/welcome

### 10.2 Esempi di Server MCP

#### Server Ufficiali
- **Filesystem**: `@modelcontextprotocol/server-filesystem`
- **GitHub**: `@modelcontextprotocol/server-github`
- **Google Drive**: `@modelcontextprotocol/server-gdrive`
- **Slack**: `@modelcontextprotocol/server-slack`

#### Installazione
```bash
# Via npm
npm install -g @modelcontextprotocol/server-filesystem

# Uso in DapaBot
Comando: npx
Args: -y @modelcontextprotocol/server-filesystem /path/to/directory
```

### 10.3 Codice Sorgente

#### File Principali
- `src/mcp/client.py`: Wrapper MultiServerMCPClient
- `src/mcp/gui_mcp.py`: Interfaccia Streamlit
- `src/tools/MCPTool.py`: Integrazione tools
- `src/models/mcp_server.py`: Modello database
- `src/ConfigurazioneDB.py`: Metodi CRUD

#### Repository
- **DapaBot**: [Link al repository]
- **Commit integrazione MCP**: [Link al commit]

### 10.4 Supporto

Per problemi o domande:
- **Issues**: [Link a GitHub Issues]
- **Discussions**: [Link a GitHub Discussions]
- **Email**: support@dapabot.example.com

---

## Appendice A: Diagrammi di Sequenza

### A.1 Aggiunta Server MCP

```
Utente          GUI              ConfigDB        MCPClientManager
  │              │                   │                  │
  │─Click Add───>│                   │                  │
  │              │                   │                  │
  │─Fill Form───>│                   │                  │
  │              │                   │                  │
  │─Click Save──>│                   │                  │
  │              │                   │                  │
  │              │─salva_mcp_server─>│                  │
  │              │                   │                  │
  │              │<─Success──────────│                  │
  │              │                   │                  │
  │              │─────────────reset()────────────────>│
  │              │                   │                  │
  │              │<────────────OK───────────────────────│
  │              │                   │                  │
  │<─Success─────│                   │                  │
```

### A.2 Esecuzione Tool MCP

```
Agent    MCPTool    MCPClientMgr    MultiServerClient    MCP Server
  │         │            │                 │                  │
  │─call────>│            │                 │                  │
  │  tool   │            │                 │                  │
  │         │            │                 │                  │
  │         │─get_tools─>│                 │                  │
  │         │            │                 │                  │
  │         │            │─get_client()───>│                  │
  │         │            │                 │                  │
  │         │            │<─client─────────│                  │
  │         │            │                 │                  │
  │         │            │─get_tools()────>│                  │
  │         │            │                 │                  │
  │         │            │                 │─JSON-RPC────────>│
  │         │            │                 │  tools/list      │
  │         │            │                 │                  │
  │         │            │                 │<─tools───────────│
  │         │            │                 │                  │
  │         │            │<─tools──────────│                  │
  │         │            │                 │                  │
  │         │<─tools─────│                 │                  │
  │         │            │                 │                  │
  │<─result─│            │                 │                  │
```

---

## Appendice B: Esempi di Configurazione

### B.1 Server Filesystem Locale

```json
{
  "nome": "filesystem",
  "tipo": "local",
  "descrizione": "Accesso al filesystem locale",
  "configurazione": {
    "comando": "npx",
    "args": [
      "-y",
      "@modelcontextprotocol/server-filesystem",
      "/home/user/documents"
    ],
    "env": {
      "DEBUG": "true"
    }
  },
  "attivo": true
}
```

### B.2 Server GitHub Locale

```json
{
  "nome": "github",
  "tipo": "local",
  "descrizione": "Integrazione GitHub",
  "configurazione": {
    "comando": "npx",
    "args": [
      "-y",
      "@modelcontextprotocol/server-github"
    ],
    "env": {
      "GITHUB_TOKEN": "ghp_xxxxxxxxxxxx"
    }
  },
  "attivo": true
}
```

### B.3 Server API Remoto

```json
{
  "nome": "weather-api",
  "tipo": "remote",
  "descrizione": "API meteo",
  "configurazione": {
    "url": "https://api.weather.com/mcp",
    "api_key": "sk-xxxxxxxxxxxx",
    "headers": {
      "X-Custom-Header": "value",
      "X-Client-Version": "1.0"
    }
  },
  "attivo": true
}
```

### B.4 Server Python Personalizzato

```json
{
  "nome": "custom-tools",
  "tipo": "local",
  "descrizione": "Tools personalizzati",
  "configurazione": {
    "comando": "python",
    "args": [
      "/path/to/my_mcp_server.py"
    ],
    "env": {
      "API_KEY": "xxxxxxxxxxxx",
      "LOG_LEVEL": "info"
    }
  },
  "attivo": true
}
```

---

## Appendice C: Troubleshooting Avanzato

### C.1 Debug Connessioni

#### Abilitare logging dettagliato

```python
import logging

# In src/mcp/client.py
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("mcp")

class MCPClientManager:
    def get_client(self):
        logger.debug(f"Creating client with configs: {self._server_configs}")
        # ...
```

#### Verificare connessione server locale

```bash
# Test manuale del server
python my_mcp_server.py

# Dovrebbe rispondere a stdin
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' | python my_mcp_server.py
```

#### Verificare connessione server remoto

```bash
# Test con curl
curl -X POST https://api.example.com/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}'
```

### C.2 Errori Comuni

#### "Server not found"
**Causa**: Server non registrato o nome errato

**Soluzione**:
```python
# Verificare server registrati
manager = get_mcp_client_manager()
print(manager.get_server_names())
```

#### "Tool execution timeout"
**Causa**: Server non risponde o tool troppo lento

**Soluzione**:
```python
# Aumentare timeout (se supportato)
client = MultiServerMCPClient(
    {...},
    timeout=60  # secondi
)
```

#### "Invalid JSON-RPC response"
**Causa**: Server non conforme allo standard MCP

**Soluzione**:
1. Verificare implementazione server
2. Controllare logs del server
3. Testare con client MCP ufficiale

### C.3 Performance

#### Ottimizzare caricamento tools

```python
# Cache tools per evitare ricaricamenti
class MCPToolIntegration(Tool):
    def get_tool(self):
        if self._tools_cache and not self._cache_expired():
            return self._tools_cache
        
        # Ricarica solo se necessario
        self._tools_cache = asyncio.run(
            self._manager.get_tools()
        )
        self._cache_timestamp = time.time()
        return self._tools_cache
```

#### Connessioni parallele

```python
# Connetti a più server in parallelo
async def connect_all_servers():
    tasks = [
        client.connect(server_name)
        for server_name in server_names
    ]
    results = await asyncio.gather(*tasks)
    return results
```

---

**Fine del Manuale**

---

*Questo documento è stato generato automaticamente da IBM Bob.*  
*Per aggiornamenti e correzioni, consultare il repository del progetto.*