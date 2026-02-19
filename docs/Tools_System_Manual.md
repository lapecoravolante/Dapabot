
# Manuale del Sistema Tools in DapaBot

**Versione:** 1.0  
**Data:** 19 Febbraio 2026  
**Autore:** IBM Bob

---

## Indice

1. [Introduzione](#1-introduzione)
2. [Cosa sono i Tools in LangChain](#2-cosa-sono-i-tools-in-langchain)
3. [Architettura del Sistema Tools](#3-architettura-del-sistema-tools)
4. [Logica di Design](#4-logica-di-design)
5. [Integrazione GUI](#5-integrazione-gui)
6. [Implementare un Nuovo Tool](#6-implementare-un-nuovo-tool)
7. [Esempi Pratici](#7-esempi-pratici)
8. [Migliorie Future](#8-migliorie-future)
9. [Riferimenti](#9-riferimenti)

---

## 1. Introduzione

### 1.1 Scopo del Documento

Questo manuale descrive il sistema di gestione dei **tools** in DapaBot, spiegando come sono strutturati, come vengono caricati e utilizzati, e come implementarne di nuovi. Il sistema è progettato per essere estensibile e permettere l'integrazione di qualsiasi tool LangChain in modo uniforme.

### 1.2 Contesto

DapaBot utilizza i tools in **modalità agentica**, dove un agente LLM può decidere autonomamente quali tools utilizzare per rispondere alle richieste dell'utente. Il sistema tools fornisce:

- **Astrazione uniforme**: Tutti i tools seguono la stessa interfaccia
- **Configurazione persistente**: Le impostazioni vengono salvate nel database
- **Caricamento automatico**: I tools vengono scoperti e caricati dinamicamente
- **Gestione dipendenze**: Installazione automatica dei pacchetti necessari

---

## 2. Cosa sono i Tools in LangChain

### 2.1 Definizione

Un **tool** in LangChain è una funzione che un agente può invocare per eseguire azioni specifiche. Ogni tool ha:

- **Nome**: Identificatore univoco
- **Descrizione**: Spiega cosa fa il tool (usata dall'LLM per decidere quando usarlo)
- **Schema degli argomenti**: Definisce i parametri richiesti
- **Funzione di esecuzione**: Il codice che viene eseguito

### 2.2 Classe BaseTool

LangChain fornisce la classe base `BaseTool`:

```python
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

class MyToolArgs(BaseModel):
    """Schema degli argomenti"""
    query: str = Field(description="Query di ricerca")
    limit: int = Field(default=10, description="Numero massimo di risultati")

class MyTool(BaseTool):
    name = "my_tool"
    description = "Descrizione del tool per l'LLM"
    args_schema = MyToolArgs
    
    def _run(self, query: str, limit: int = 10) -> str:
        """Esecuzione sincrona"""
        # Logica del tool
        return "Risultato"
    
    async def _arun(self, query: str, limit: int = 10) -> str:
        """Esecuzione asincrona (opzionale)"""
        return self._run(query, limit)
```

### 2.3 Toolkits

Un **toolkit** è una collezione di tools correlati. Ad esempio, `FileManagementToolkit` include:

- `ReadFileTool`: Legge file
- `WriteFileTool`: Scrive file
- `ListDirectoryTool`: Lista directory
- `CopyFileTool`: Copia file
- `DeleteFileTool`: Elimina file
- `MoveFileTool`: Sposta file

```python
from langchain_community.agent_toolkits import FileManagementToolkit

toolkit = FileManagementToolkit(root_dir="/path/to/dir")
tools = toolkit.get_tools()  # Lista di BaseTool
```

### 2.4 Wrappers e Utilities

Molti tools LangChain usano un pattern a due livelli:

1. **Wrapper/Utility**: Gestisce la logica di business e le chiamate API
2. **Tool**: Wrappa il wrapper per esporlo come BaseTool

```python
# Wrapper
from langchain_community.utilities import WikipediaAPIWrapper

wiki_wrapper = WikipediaAPIWrapper(
    top_k_results=3,
    lang="it"
)

# Tool
from langchain_community.tools.wikipedia.tool import WikipediaQueryRun

wiki_tool = WikipediaQueryRun(api_wrapper=wiki_wrapper)
```

---

## 3. Architettura del Sistema Tools

### 3.1 Diagramma Architetturale

```
┌─────────────────────────────────────────────────────────────┐
│                     DapaBot GUI                             │
│                   (Streamlit)                               │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ Configurazione Tools
                         │
┌────────────────────────▼────────────────────────────────────┐
│                  ConfigurazioneDB                           │
│                  (SQLite + Peewee)                          │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ ToolModel                                            │  │
│  │ - nome_tool (PK)                                     │  │
│  │ - configurazione (JSON)                              │  │
│  │ - attivo (Boolean)                                   │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ Carica Config
                         │
┌────────────────────────▼────────────────────────────────────┐
│                    Loader                                   │
│                (src/tools/loader.py)                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ - discover_tools()                                   │  │
│  │   • Scansiona package src.tools                      │  │
│  │   • Importa tutti i moduli                           │  │
│  │   • Istanzia sottoclassi di Tool                     │  │
│  │   • Installa dipendenze                              │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ Dizionario {nome: Tool}
                         │
┌────────────────────────▼────────────────────────────────────┐
│                    Tool (ABC)                               │
│                (src/tools/Tool.py)                          │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Classe base astratta per tutti i tools              │  │
│  │ - __init__(nome, variabili, pacchetti, params)      │  │
│  │ - installa_pacchetti()                               │  │
│  │ - get_configurazione() → dict                        │  │
│  │ - get_tool() → List[BaseTool] (abstract)            │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ Estende
                         │
        ┌────────────────┼────────────────┬────────────────┐
        │                │                │                │
┌───────▼──────┐ ┌───────▼──────┐ ┌──────▼───────┐ ┌─────▼──────┐
│   Arxiv      │ │  Wikipedia   │ │  Filesystem  │ │   Github   │
│              │ │              │ │              │ │            │
│ get_tool()   │ │ get_tool()   │ │ get_tool()   │ │ get_tool() │
│ → [Tool]     │ │ → [Tool]     │ │ → [Tools]    │ │ → [Tools]  │
└──────────────┘ └──────────────┘ └──────────────┘ └────────────┘
                         │
                         │ Lista di BaseTool
                         │
┌────────────────────────▼────────────────────────────────────┐
│              LangChain Agent                                │
│              (Modalità Agentica)                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ - create_agent(model, tools)                         │  │
│  │ - Decide quali tools usare                           │  │
│  │ - Esegue tools in base al contesto                   │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Flusso di Caricamento Tools

```
1. Avvio applicazione
   ↓
2. Loader.discover_tools()
   ↓
3. Scansione package src.tools
   ↓
4. Import di tutti i moduli (eccetto Tool.py)
   ↓
5. Identificazione sottoclassi di Tool
   ↓
6. Istanziazione di ogni sottoclasse
   ↓
7. Installazione pacchetti necessari
   ↓
8. Registrazione in dizionario {nome: istanza}
   ↓
9. Caricamento configurazioni da DB
   ↓
10. Applicazione configurazioni alle istanze
   ↓
11. Tools pronti per l'uso
```

### 3.3 Flusso di Esecuzione Tool

```
Utente: "Cerca informazioni su Python su Wikipedia"
   ↓
Agent riceve messaggio
   ↓
Agent analizza richiesta
   ↓
Agent decide: usare tool "Wikipedia"
   ↓
Agent prepara parametri: {query: "Python"}
   ↓
LangChain valida parametri con Pydantic
   ↓
Chiamata a WikipediaQueryRun._run(query="Python")
   ↓
WikipediaAPIWrapper esegue ricerca
   ↓
Risultato ritorna all'agent
   ↓
Agent formula risposta finale
   ↓
Risposta mostrata all'utente
```

---

## 4. Logica di Design

### 4.1 Diagramma delle Classi

```
┌─────────────────────────────────────────────────────────┐
│                    Tool (ABC)                           │
├─────────────────────────────────────────────────────────┤
│ # Attributi                                             │
│ - _nome: str                                            │
│ - _variabili_necessarie: dict[str, str]                 │
│ - _pacchetti_python_necessari: dict[str, str]           │
│ - _configurazione: dict                                 │
│ - **parametri_iniziali (attributi dinamici)            │
├─────────────────────────────────────────────────────────┤
│ # Metodi                                                │
│ + __init__(nome, variabili, pacchetti, config, params) │
│ + installa_pacchetti() → None                           │
│ + get_nome() → str                                      │
│ + set_variabili_necessarie(dict) → None                 │
│ + get_variabili_necessarie() → dict                     │
│ + set_configurazione(dict) → None                       │
│ + get_configurazione() → dict                           │
│ + get_tool() → List[BaseTool] (abstract)                │
└─────────────────────────────────────────────────────────┘
                         △
                         │ extends
         ┌───────────────┼───────────────┬──────────────┐
         │               │               │              │
┌────────┴────────┐ ┌────┴──────┐ ┌─────┴──────┐ ┌─────┴──────┐
│     Arxiv       │ │ Wikipedia │ │ Filesystem │ │   Github   │
├─────────────────┤ ├───────────┤ ├────────────┤ ├────────────┤
│ + top_k_results │ │ + lang    │ │ + root_dir │ │ + repo     │
│ + load_max_docs │ │ + top_k   │ │ + selected │ │ + branch   │
│ + doc_chars_max │ │ + doc_max │ │   _tools   │ │ + app_id   │
├─────────────────┤ ├───────────┤ ├────────────┤ ├────────────┤
│ + get_tool()    │ │+ get_tool │ │+ get_tool()│ │+ get_tool()│
│   → [ArxivTool] │ │  → [Wiki] │ │  → [Tools] │ │  → [Tools] │
└─────────────────┘ └───────────┘ └────────────┘ └────────────┘
```

### 4.2 Pattern di Design Utilizzati

#### 4.2.1 Template Method Pattern

La classe `Tool` definisce il template per tutti i tools:

```python
class Tool(ABC):
    def __init__(self, ...):
        # 1. Inizializza attributi base
        self._nome = nome
        self._variabili_necessarie = variabili_necessarie
        
        # 2. Imposta parametri configurabili come attributi
        if parametri_iniziali:
            for nome_param, valore_default in parametri_iniziali.items():
                setattr(self, nome_param, valore_default)
        
        # 3. Installa dipendenze
        self.installa_pacchetti()
    
    @abstractmethod
    def get_tool(self) -> list:
        """Sottoclassi implementano questo metodo"""
        pass
```

Le sottoclassi seguono il template ma personalizzano `get_tool()`.

#### 4.2.2 Factory Pattern

Il `Loader` agisce come factory per creare istanze di tools:

```python
class Loader:
    @staticmethod
    def discover_tools():
        # Scopre tutte le sottoclassi di Tool
        for cls in Tool.__subclasses__():
            instance = cls()  # Factory: crea istanza
            Loader._moduli[instance.get_nome()] = instance
        return Loader._moduli
```

#### 4.2.3 Singleton Pattern

Il `Loader` usa un singleton per garantire un'unica istanza:

```python
class Loader:
    _caricamento_effettuato = False
    _moduli = {}
    _mutex = Lock()
    
    @staticmethod
    def discover_tools():
        with Loader._mutex:
            if not Loader._caricamento_effettuato:
                # Carica tools una sola volta
                ...
                Loader._caricamento_effettuato = True
        return Loader._moduli
```

#### 4.2.4 Strategy Pattern

Ogni tool implementa una strategia diversa per `get_tool()`:

```python
# Strategia 1: Tool singolo
class Arxiv(Tool):
    def get_tool(self):
        wrapper = ArxivAPIWrapper(...)
        tool = ArxivQueryRun(api_wrapper=wrapper)
        return [tool]  # Lista con un elemento

# Strategia 2: Toolkit (multipli tools)
class Filesystem(Tool):
    def get_tool(self):
        toolkit = FileManagementToolkit(...)
        return toolkit.get_tools()  # Lista con più elementi
```

### 4.3 Principi SOLID

#### Single Responsibility
- `Tool`: Gestisce configurazione e dipendenze
- `Loader`: Scopre e carica tools
- `ConfigurazioneDB`: Persistenza
- Sottoclassi: Implementano tool specifici

#### Open/Closed
- Sistema aperto all'estensione (nuovi tools)
- Chiuso alla modifica (classe base stabile)

#### Liskov Substitution
- Tutte le sottoclassi di `Tool` sono intercambiabili
- Tutte ritornano `List[BaseTool]`

#### Interface Segregation
- Interfaccia minima: solo `get_tool()` è astratto
- Metodi opzionali: `set_configurazione()`, etc.

#### Dependency Inversion
- Dipendenza da astrazione (`Tool`)
- Non da implementazioni concrete

### 4.4 Diagramma di Sequenza: Caricamento Tool

```
Loader          Tool(ABC)      Arxiv         ArxivAPIWrapper    ArxivQueryRun
  │                │             │                  │                 │
  │─discover_tools()             │                  │                 │
  │                │             │                  │                 │
  │────────────────┼─import──────>│                  │                 │
  │                │             │                  │                 │
  │────────────────┼─__init__()──>│                  │                 │
  │                │             │                  │                 │
  │                │<─super().__init__()             │                 │
  │                │             │                  │                 │
  │                │─installa_pacchetti()            │                 │
  │                │             │                  │                 │
  │<───────────────┼─────────────│                  │                 │
  │                │             │                  │                 │
  │─get_tool()─────┼─────────────>│                  │                 │
  │                │             │                  │                 │
  │                │             │─new──────────────>│                 │
  │                │             │                  │                 │
  │                │             │<─wrapper─────────│                 │
  │                │             │                  │                 │
  │                │             │─new──────────────┼─────────────────>│
  │                │             │                  │                 │
  │                │             │<─tool────────────┼─────────────────│
  │                │             │                  │                 │
  │<───────────────┼─────────────│ [tool]           │                 │
  │                │             │                  │                 │
```

### 4.5 Diagramma di Attività: Uso Tool in Agent

```
┌─────────────────────────────────────────────────────────┐
│ START: Utente invia messaggio                          │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
          ┌──────────────────────┐
          │ Agent analizza       │
          │ messaggio            │
          └──────────┬───────────┘
                     │
                     ▼
          ┌──────────────────────┐
          │ Serve un tool?       │
          └──────────┬───────────┘
                     │
          ┌──────────┴──────────┐
          │ NO                  │ SI
          ▼                     ▼
┌─────────────────┐   ┌─────────────────────┐
│ Risposta diretta│   │ Seleziona tool      │
└─────────────────┘   │ appropriato         │
                      └──────────┬──────────┘
                                 │
                                 ▼
                      ┌─────────────────────┐
                      │ Prepara parametri   │
                      └──────────┬──────────┘
                                 │
                                 ▼
                      ┌─────────────────────┐
                      │ Valida con Pydantic │
                      └──────────┬──────────┘
                                 │
                      ┌──────────┴──────────┐
                      │ Valido?             │
                      └──────────┬──────────┘
                                 │
                      ┌──────────┴──────────┐
                      │ NO                  │ SI
                      ▼                     ▼
            ┌─────────────────┐   ┌─────────────────────┐
            │ Errore parametri│   │ Esegue tool._run()  │
            └─────────────────┘   └──────────┬──────────┘
                                             │
                                             ▼
                                  ┌─────────────────────┐
                                  │ Tool ritorna        │
                                  │ risultato           │
                                  └──────────┬──────────┘
                                             │
                                             ▼
                                  ┌─────────────────────┐
                                  │ Agent elabora       │
                                  │ risultato           │
                                  └──────────┬──────────┘
                                             │
                                             ▼
                                  ┌─────────────────────┐
                                  │ Serve altro tool?   │
                                  └──────────┬──────────┘
                                             │
                                  ┌──────────┴──────────┐
                                  │ SI                  │ NO
                                  │ (loop)              ▼
                                  │          ┌─────────────────────┐
                                  └──────────│ Formula risposta    │
                                             │ finale              │
                                             └──────────┬──────────┘
                                                        │
                                                        ▼
                                             ┌─────────────────────┐
                                             │ END: Mostra risposta│
                                             └─────────────────────┘
```

---

## 5. Integrazione GUI

### 5.1 Interfaccia Utente

La gestione dei tools avviene nella sidebar di Streamlit, nell'expander **"🤖 Modalità Agentica"**.

```
┌─────────────────────────────────┐
│ 🤖 DapaBot                      │
│                                 │
│ [Provider Selection]            │
│ [Model Selection]               │
│                                 │
│ ▼ 🤖 Modalità Agentica          │ ← Expander
│   ☑ Abilita Modalità Agentica  │
│                                 │
│   [⚙️ Configura] [🔌 Configura]│ ← Pulsanti affiancati
│   [   Tools    ] [    MCP     ]│
│                                 │
│   📋 Dettagli tools attivi      │
│   • Arxiv                       │
│   • Wikipedia                   │
│   • MCP                         │
└─────────────────────────────────┘
```

**Note importanti:**
- I pulsanti **"⚙️ Configura Tools"** e **"🔌 Configura MCP"** sono affiancati per un accesso rapido
- Il pulsante Tools apre il dialog di configurazione tools (implementato in `src/tools/gui_tools.py`)
- Il pulsante MCP apre il dialog di configurazione server MCP (implementato in `src/mcp/gui_mcp.py`)

### 5.2 Attività Comuni

#### 5.2.1 Aggiunta Configurazione Tool al Database

**Scenario**: Configurare il tool Wikipedia per la prima volta.

**Passi**:

1. **Attivare Modalità Agentica**
   ```
   ☑ Modalità Agentica
   ```

2. **Selezionare Tool**
   ```
   ☑ Wikipedia  ← Click sulla checkbox
   ```

3. **Aprire Configurazione**
   ```
   [⚙️ Configura Tools]  ← Click sul pulsante (a sinistra)
   ```

4. **Compilare Form**
   ```
   ┌─────────────────────────────────┐
   │ ⚙️ Configurazione Wikipedia     │
   ├─────────────────────────────────┤
   │ Lingua:                         │
   │ [it___________________________] │
   │                                 │
   │ Numero risultati:               │
   │ [3____________________________] │
   │                                 │
   │ Caratteri massimi:              │
   │ [4000_________________________] │
   │                                 │
   │ Carica tutti i metadati:        │
   │ ☐                               │
   │                                 │
   │ [💾 Salva]  [❌ Annulla]        │
   └─────────────────────────────────┘
   ```

5. **Salvare**
   - Click su **"💾 Salva"**
   - Configurazione salvata in `ToolModel`
   - Tool pronto per l'uso

**Codice dietro le quinte**:
```python
# In gui_utils.py
def configura_tools():
    # Ottieni tool selezionato
    tool = tools_disponibili["Wikipedia"]
    
    # Mostra form con parametri attuali
    lang = st.text_input("Lingua", value=tool.lang)
    top_k = st.number_input("Numero risultati", value=tool.top_k_results)
    
    if st.button("Salva"):
        # Aggiorna attributi
        tool.lang = lang
        tool.top_k_results = top_k
        
        # Salva nel database
        ConfigurazioneDB.salva_tool(
            nome_tool="Wikipedia",
            configurazione=tool.get_configurazione(),
            attivo=True
        )
```

#### 5.2.2 Rimozione Configurazione Tool

**Scenario**: Rimuovere completamente il tool Github.

**Passi**:

1. **Deselezionare Tool**
   ```
   ☐ Github  ← Rimuovi spunta
   ```

2. **Confermare**
   - Il tool viene disattivato immediatamente
   - Configurazione rimane nel DB ma `attivo=False`

**Per eliminare completamente**:

```python
# Tramite codice (non disponibile in GUI standard)
ConfigurazioneDB.cancella_tool("Github")
```

#### 5.2.3 Configurazione di un Tool

**Scenario**: Modificare la directory root del tool Filesystem.

**Passi**:

1. **Assicurarsi che il tool sia attivo**
   ```
   ☑ Filesystem
   ```

2. **Aprire Configurazione**
   ```
   [⚙️ Configura Tools]  ← Pulsante a sinistra nell'expander
   ```

3. **Selezionare Tool**
   ```
   Tool: [Filesystem ▼]
   ```

4. **Modificare Parametri**
   ```
   ┌─────────────────────────────────┐
   │ ⚙️ Configurazione Filesystem    │
   ├─────────────────────────────────┤
   │ Directory Root:                 │
   │ [/home/user/documents_________] │
   │                                 │
   │ Tools selezionati:              │
   │ ☑ read_file                     │
   │ ☑ write_file                    │
   │ ☑ list_directory                │
   │ ☐ copy_file                     │
   │ ☐ delete_file                   │
   │ ☐ move_file                     │
   │                                 │
   │ [💾 Salva]  [❌ Annulla]        │
   └─────────────────────────────────┘
   ```

5. **Salvare**
   - Click su **"💾 Salva"**
   - Nuova configurazione applicata

#### 5.2.4 Attivazione Tool in Modalità Agentica

**Scenario**: Attivare i tools Arxiv e Wikipedia per una sessione di ricerca.

**Passi**:

1. **Attivare Modalità Agentica**
   ```
   ☑ Modalità Agentica  ← IMPORTANTE
   ```

2. **Selezionare Tools**
   ```
   Tools disponibili:
   ☑ Arxiv       ← Attivo
   ☑ Wikipedia   ← Attivo
   ☐ Filesystem  ← Non attivo
   ☐ Github      ← Non attivo
   ```

3. **Verificare Attivazione**
   - I tools selezionati sono immediatamente disponibili
   - L'agent può usarli nelle risposte

4. **Testare**
   ```
   Utente: "Cerca articoli su quantum computing su Arxiv"
   
   Agent (interno):
   1. Identifica necessità tool "Arxiv"
   2. Prepara query: "quantum computing"
   3. Esegue: arxiv_tool.run(query="quantum computing")
   4. Riceve risultati
   5. Formula risposta
   
   Risposta: "Ho trovato 3 articoli recenti su quantum computing:
   1. [Titolo] - [Autori] - [Abstract]
   2. ..."
   ```

**Flusso Tecnico**:
```python
# In gui_utils.py
def crea_sidebar():
    # Carica tools disponibili
    tools_disponibili = Loader.discover_tools()
    
    # Carica configurazioni dal DB
    tools_attivi_db = ConfigurazioneDB.carica_tools_attivi()
    
    # Mostra checkboxes
    tools_selezionati = []
    for nome, tool in tools_disponibili.items():
        attivo = nome in [t['nome_tool'] for t in tools_attivi_db]
        if st.checkbox(nome, value=attivo):
            tools_selezionati.append(nome)
    
    # Aggiorna DB
    ConfigurazioneDB.aggiorna_stati_tools(tools_selezionati)
    
    # Ritorna tools per l'agent
    return [tools_disponibili[nome].get_tool() 
            for nome in tools_selezionati]
```

### 5.3 Gestione Errori nella GUI

#### Tool non disponibile
```
⚠️ Tool "Github" non disponibile
Verifica che le variabili d'ambiente siano configurate:
- GITHUB_TOKEN
- GITHUB_REPOSITORY
```

#### Dipendenze mancanti
```
📦 Installazione pacchetto: pygithub
⏳ Attendere...
✅ Installazione completata
```

#### Errore di configurazione
```
❌ Errore configurazione Filesystem
Directory '/invalid/path' non esiste
```

---

## 6. Implementare un Nuovo Tool

### 6.1 Struttura Base

Ogni nuovo tool deve:
1. Estendere la classe `Tool`
2. Implementare `get_tool()`
3. Essere salvato in `src/tools/NomeTool.py`

### 6.2 Esempio: Tool DuckDuckGo Search

Implementiamo un tool per ricerche web usando DuckDuckGo (disponibile in langchain-community).

#### Passo 1: Analizzare il Tool LangChain

```python
# Da langchain-community
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper

# Uso base
search = DuckDuckGoSearchRun()
result = search.run("Python programming")

# Con configurazione
wrapper = DuckDuckGoSearchAPIWrapper(
    region="it-it",
    time="d",  # last day
    max_results=5
)
search = DuckDuckGoSearchRun(api_wrapper=wrapper)
```

#### Passo 2: Creare la Classe

```python
# src/tools/DuckDuckGo.py
from src.tools.Tool import Tool
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper

class DuckDuckGo(Tool):
    
    def __init__(self) -> None:
        super().__init__(
            nome="DuckDuckGo",
            pacchetti_python_necessari={
                "langchain-community": "langchain_community",
                "duckduckgo-search": "duckduckgo_search"
            },
            parametri_iniziali={
                "region": "it-it",
                "time": "y",  # last year
                "max_results": 5,
                "safesearch": "moderate"
            }
        )
    
    def get_tool(self):
        # Crea il wrapper con i parametri configurati
        wrapper = DuckDuckGoSearchAPIWrapper(
            region=self.region,
            time=self.time,
            max_results=self.max_results,
            safesearch=self.safesearch
        )
        
        # Crea il tool
        search_tool = DuckDuckGoSearchRun(api_wrapper=wrapper)
        
        # Ritorna lista con il tool
        return [search_tool]
```

#### Passo 3: Testare

```python
# Test manuale
from src.tools.DuckDuckGo import DuckDuckGo

# Crea istanza
ddg = DuckDuckGo()

# Ottieni tool
tools = ddg.get_tool()
search_tool = tools[0]

# Usa tool
result = search_tool.run("Python tutorials")
print(result)
```

#### Passo 4: Integrare

Il tool viene automaticamente scoperto da `Loader.discover_tools()` all'avvio dell'applicazione.

### 6.3 Esempio Avanzato: Tool con Variabili d'Ambiente

Implementiamo un tool per OpenWeatherMap che richiede una API key.

```python
# src/tools/OpenWeatherMap.py
from src.tools.Tool import Tool
from langchain_community.tools.openweathermap.tool import OpenWeatherMapQueryRun
from langchain_community.utilities.openweathermap import OpenWeatherMapAPIWrapper

class OpenWeatherMap(Tool):
    
    def __init__(self) -> None:
        super().__init__(
            nome="OpenWeatherMap",
            variabili_necessarie={
                "OPENWEATHERMAP_API_KEY": ""  # Deve essere fornita dall'utente
            },
            pacchetti_python_necessari={
                "langchain-community": "langchain_community",
                "pyowm": "pyowm"
            },
            parametri_iniziali={
                "language": "it"
            }
        )
    
    def get_tool(self):
        # Verifica che l'API key sia stata impostata
        api_key = self._variabili_necessarie.get("OPENWEATHERMAP_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENWEATHERMAP_API_KEY non configurata. "
                "Impostala nelle variabili d'ambiente del tool."
            )
        
        # Crea wrapper
        wrapper = OpenWeatherMapAPIWrapper(
            openweathermap_api_key=api_key,
            language=self.language
        )
        
        # Crea tool
        weather_tool = OpenWeatherMapQueryRun(api_wrapper=wrapper)
        
        return [weather_tool]
```

**Configurazione GUI**:
```python
# In gui_utils.py - form di configurazione
def configura_openweathermap(tool):
    st.subheader("Configurazione OpenWeatherMap")
    
    # Variabili d'ambiente
    api_key = st.text_input(
        "API Key",
        value=tool._variabili_necessarie.get("OPENWEATHERMAP_API_KEY", ""),
        type="password"
    )
    
    # Parametri
    language = st.selectbox(
        "Lingua",
        options=["it", "en", "es", "fr", "de"],
        index=0 if tool.language == "it" else 1
    )
    
    if st.button("Salva"):
        # Aggiorna variabili d'ambiente
        tool.set_variabili_necessarie({
            "OPENWEATHERMAP_API_KEY": api_key
        })
        
        # Aggiorna parametri
        tool.language = language
        
        # Salva nel DB
        ConfigurazioneDB.salva_tool(
            nome_tool="OpenWeatherMap",
            configurazione=tool.get_configurazione(),
            attivo=True
        )
```

### 6.4 Esempio: Toolkit con Multipli Tools

Implementiamo un wrapper per il toolkit Gmail.

```python
# src/tools/Gmail.py
from src.tools.Tool import Tool
from langchain_community.agent_toolkits import GmailToolkit
from langchain_community.tools.gmail.utils import build_resource_service
import os

class Gmail(Tool):
    
    def __init__(self) -> None:
        super().__init__(
            nome="Gmail",
            variabili_necessarie={
                "GOOGLE_APPLICATION_CREDENTIALS": ""
            },
            pacchetti_python_necessari={
                "langchain-community": "langchain_community",
                "google-auth": "google.auth",
                "google-auth-oauthlib": "google_auth_oauthlib",
                "google-auth-httplib2": "google_auth_httplib2",
                "google-api-python-client": "googleapiclient"
            },
            parametri_iniziali={
                "selected_tools": [
                    "search",
                    "get_message",
                    "send_message",
                    "create_draft"
                ]
            }
        )
    
    def get_tool(self):
        # Verifica credenziali
        creds_path = self._variabili_necessarie.get(
            "GOOGLE_APPLICATION_CREDENTIALS"
        )
        if not creds_path or not os.path.exists(creds_path):
            raise ValueError(
                "GOOGLE_APPLICATION_CREDENTIALS non configurato o file non trovato"
            )
        
        # Crea servizio Gmail
        api_resource = build_resource_service()
        
        # Crea toolkit
        toolkit = GmailToolkit(api_resource=api_resource)
        
        # Ottieni tutti i tools
        all_tools = toolkit.get_tools()
        
        # Filtra in base a selected_tools
        selected = [
            tool for tool in all_tools 
            if tool.name in self.selected_tools
        ]
        
        return selected
```

### 6.5 Best Practices

#### 6.5.1 Naming Conventions
- **Classe**: PascalCase (es. `DuckDuckGo`, `OpenWeatherMap`)
- **File**: PascalCase.py (es. `DuckDuckGo.py`)
- **Nome tool**: Stesso della classe (es. `nome="DuckDuckGo"`)

#### 6.5.2 Parametri Configurabili
- Usa `parametri_iniziali` per valori modificabili dall'utente
- Fornisci valori di default sensati
- Documenta ogni parametro

```python
parametri_iniziali={
    "max_results": 5,  # Numero massimo di risultati
    "language": "it",  # Lingua dei risultati
    "safe_search": True  # Abilita safe search
}
```

#### 6.5.3 Gestione Errori
- Valida parametri in `get_tool()`
- Fornisci messaggi di errore chiari
- Gestisci eccezioni delle API esterne

```python
def get_tool(self):
    try:
        wrapper = SomeAPIWrapper(api_key=self.api_key)
        return [SomeTool(api_wrapper=wrapper)]
    except ValueError as e:
        raise ValueError(f"Configurazione non valida: {e}")
    except Exception as e:
        raise RuntimeError(f"Errore inizializzazione tool: {e}")
```

#### 6.5.4 Documentazione
- Docstring per la classe
- Commenti per logica complessa
- README se il tool richiede setup particolare

```python
class MyTool(Tool):
    """
    Tool per [descrizione funzionalità].
    
    Richiede:
    - API key da [provider]
    - Pacchetto [nome_pacchetto]
    
    Parametri configurabili:
    - param1: Descrizione param1
    - param2: Descrizione param2
    
    Esempio:
        tool = MyTool()
        tool.param1 = "valore"
        tools = tool.get_tool()
    """
```

#### 6.5.5 Testing
- Test unitari per `get_tool()`
- Test di integrazione con LangChain
- Mock delle API esterne

```python
# tests/test_duckduckgo.py
import pytest
from src.tools.DuckDuckGo import DuckDuckGo

def test_duckduckgo_initialization():
    tool = DuckDuckGo()
    assert tool.get_nome() == "DuckDuckGo"
    assert tool.region == "it-it"

def test_duckduckgo_get_tool():
    tool = DuckDuckGo()
    tools = tool.get_tool()
    assert len(tools) == 1
    assert tools[0].name == "duckduckgo_search"

@pytest.mark.integration
def test_duckduckgo_search():
    tool = DuckDuckGo()
    search_tool = tool.get_tool()[0]
    result = search_tool.run("Python")
    assert result is not None
    assert len(result) > 0
```

---

## 7. Esempi Pratici

### 7.1 Tool Arxiv

**Scopo**: Ricerca articoli scientifici su arXiv.org

**Codice**:
```python
# src/tools/Arxiv.py
from src.tools.Tool import Tool
from langchain_community.tools.arxiv.tool import ArxivQueryRun
from langchain_community.utilities import ArxivAPIWrapper

class Arxiv(Tool):
    def __init__(self) -> None:
        super().__init__(
            nome="Arxiv",
            pacchetti_python_necessari={
                "langchain-community": "langchain_community",
                "arxiv": "arxiv"
            },
            parametri_iniziali={
                "top_k_results": 3,
                "ARXIV_MAX_QUERY_LENGTH": 300,
                "continue_on_failure": False,
                "load_max_docs": 100,
                "load_all_available_meta": False,
                "doc_content_chars_max": 4000
            }
        )

    def get_tool(self):
        arxiv_wrapper = ArxivAPIWrapper(
            top_k_results=self.top_k_results,
            ARXIV_MAX_QUERY_LENGTH=self.ARXIV_MAX_QUERY_LENGTH,
            continue_on_failure=self.continue_on_failure,
            load_max_docs=self.load_max_docs,
            load_all_available_meta=self.load_all_available_meta,
            doc_content_chars_max=self.doc_content_chars_max
        )
        arxiv_tool = ArxivQueryRun(api_wrapper=arxiv_wrapper)
        return [arxiv_tool]
```

**Uso**:
```
Utente: "Cerca articoli recenti su machine learning"

Agent:
1. Usa tool "Arxiv"
2. Query: "machine learning"
3. Riceve 3 articoli
4. Risponde con titoli, autori e abstract
```

**Configurazione**:
- `top_k_results`: Numero di articoli da ritornare
- `doc_content_chars_max`: Lunghezza massima abstract

### 7.2 Tool Wikipedia

**Scopo**: Ricerca informazioni su Wikipedia

**Codice**:
```python
# src/tools/Wikipedia.py
from src.tools.Tool import Tool
from langchain_community.utilities import WikipediaAPIWrapper
from langchain_community.tools.wikipedia.tool import WikipediaQueryRun

class Wikipedia(Tool):
    def __init__(self) -> None:
        super().__init__(
            nome="Wikipedia",
            pacchetti_python_necessari={
                "langchain-community": "langchain_community",
                "wikipedia": "wikipedia"
            },
            parametri_iniziali={
                "lang": "it",
                "top_k_results": 3,
                "load_all_available_meta": False,
                "doc_content_chars_max": 4000
            }
        )

    def get_tool(self):
        wiki_wrapper = WikipediaAPIWrapper(
            top_k_results=self.top_k_results,
            lang=self.lang,
            load_all_available_meta=self.load_all_available_meta,
            doc_content_chars_max=self.doc_content_chars_max
        )
        return [WikipediaQueryRun(api_wrapper=wiki_wrapper)]
```

**Uso**:
```
Utente: "Chi era Alan Turing?"

Agent:
1. Usa tool "Wikipedia"
2. Query: "Alan Turing"
3. Riceve articolo Wikipedia
4. Risponde con biografia sintetica
```

**Configurazione**:
- `lang`: Lingua di Wikipedia (it, en, es, etc.)
- `top_k_results`: Numero di articoli da considerare

### 7.3 Tool Filesystem

**Scopo**: Gestione file e directory

**Codice**:
```python
# src/tools/Filesystem.py
from src.tools.Tool import Tool
from langchain_community.agent_toolkits import FileManagementToolkit

class Filesystem(Tool):
    def __init__(self) -> None:
        super().__init__(
            nome="Filesystem",
            pacchetti_python_necessari={
                "langchain-community": "langchain_community"
            },
            parametri_iniziali={
                "root_dir": "",
                "selected_tools": [
                    tool.name 
                    for tool in FileManagementToolkit().get_tools()
                ]
            }
        )

    def get_tool(self):
        return FileManagementToolkit(
            root_dir=self.root_dir,
            selected_tools=self.selected_tools
        ).get_tools()
```

**Tools disponibili**:
- `read_file`: Legge contenuto file
- `write_file`: Scrive file
- `list_directory`: Lista directory
- `copy_file`: Copia file
- `delete_file`: Elimina file
- `move_file`: Sposta file

**Uso**:
```
Utente: "Crea un file chiamato notes.txt con il contenuto 'Hello World'"

Agent:
1. Usa tool "write_file"
2. Parametri: filename="notes.txt", content="Hello World"
3. File creato
4. Conferma all'utente
```

**Configurazione**:
- `root_dir`: Directory base (sicurezza)
- `selected_tools`: Quali tools abilitare

### 7.4 Tool Github

**Scopo**: Interazione con repository GitHub

**Codice**:
```python
# src/tools/Github.py
from src.tools.Tool import Tool
from langchain_community.agent_toolkits.github.toolkit import GitHubToolkit
from langchain_community.utilities.github import GitHubAPIWrapper

class Github(Tool):
    def __init__(self) -> None:
        super().__init__(
            nome="Github",
            pacchetti_python_necessari={
                "langchain-community": "langchain_community",
                "pygithub": "github"
            },
            variabili_necessarie={
                "LANGSMITH_API_KEY": "",
                "LANGSMITH_TRACING": "",
                "GITHUB_REPOSITORY": "",
                "GITHUB_APP_ID": "",
                "GITHUB_APP_PRIVATE_KEY": "",
                "GITHUB_BRANCH": "",
                "GITHUB_BASE_BRANCH": ""
            },
            parametri_iniziali={
                "include_release_tools": False
            }
        )

    def get_tool(self):
        return GitHubToolkit.from_github_api_wrapper(
            github_api_wrapper=GitHubAPIWrapper(),
            include_release_tools=self.include_release_tools
        ).get_tools()
```

**Tools disponibili**:
- `get_issues`: Lista issues
- `get_issue`: Dettagli issue
- `comment_on_issue`: Commenta issue
- `create_pull_request`: Crea PR
- `create_file`: Crea file nel repo
- `read_file`: Legge file dal repo
- `update_file`: Aggiorna file
- `delete_file`: Elimina file

**Uso**:
```
Utente: "Crea una issue su GitHub per bug nel login"

Agent:
1. Usa tool "create_issue"
2. Parametri: title="Bug nel login", body="Descrizione..."
3. Issue creata
4. Ritorna URL issue
```

**Configurazione**:
- Variabili d'ambiente per autenticazione GitHub
- `include_release_tools`: Include tools per release

### 7.5 Tool MCP

**Scopo**: Integrazione con server MCP (vedi [Manuale MCP](MCP_Integration_Manual.md))

**Codice**:
```python
# src/tools/MCPTool.py
from typing import List
import asyncio
from langchain.tools import BaseTool
from src.tools.Tool import Tool
from src.mcp.client import get_mcp_client_manager

class MCPToolIntegration(Tool):
    def __init__(self):
        super().__init__(
            nome="MCP",
            pacchetti_python_necessari={
                "langchain-mcp-adapters": "langchain_mcp_adapters"
            }
        )
        self._manager = get_mcp_client_manager()
        self._tools_cache: List[BaseTool] = []
    
    def get_tool(self) -> List[BaseTool]:
        if self._tools_cache:
            return self._tools_cache
        
        try:
            self._manager.carica_configurazioni_da_db()
            self._tools_cache = asyncio.run(self._manager.get_tools())
            return self._tools_cache
        except Exception as e:
            print(f"Errore caricamento tools MCP: {e}")
            return []
```

**Caratteristiche**:
- Carica tools da server MCP configurati
- Supporta server locali e remoti
- Cache per performance

---

## 8. Migliorie Future

### 8.1 Sistema di Plugin

**Obiettivo**: Permettere installazione di tools da repository esterni

**Implementazione**:
```python
# src/tools/plugin_manager.py
class PluginManager:
    def install_from_git(self, repo_url: str):
        """Installa tool da repository Git"""
        # 1. Clone repository
        # 2. Verifica che estenda Tool
        # 3. Installa dipendenze
        # 4. Registra nel Loader
        pass
    
    def install_from_pypi(self, package_name: str):
        """Installa tool da PyPI"""
        # 1. pip install package
        # 2. Importa e registra
        pass
```

**GUI**:
```
┌─────────────────────────────────┐
│ 📦 Installa Tool                │
├─────────────────────────────────┤
│ Sorgente:                       │
│ ○ Repository Git                │
│ ● PyPI Package                  │
│                                 │
│ Nome pacchetto:                 │
│ [langchain-tool-example_______] │
│                                 │
│ [📥 Installa]                   │
└─────────────────────────────────┘
```

### 8.2 Validazione Automatica

**Obiettivo**: Validare configurazioni prima dell'uso

**Implementazione**:
```python
class Tool(ABC):
    def validate_configuration(self) -> tuple[bool, str]:
        """
        Valida la configurazione del tool.
        
        Returns:
            (is_valid, error_message)
        """
        # Verifica variabili d'ambiente
        for var, value in self._variabili_necessarie.items():
            if not value:
                return False, f"Variabile {var} non configurata"
        
        # Verifica parametri
        # ...
        
        return True, ""
```

**GUI**:
```
⚠️ Tool "Github" non configurato correttamente
Variabile GITHUB_TOKEN non impostata

[⚙️ Configura Ora]
```

### 8.3 Metriche e Monitoring

**Obiettivo**: Tracciare uso e performance dei tools

**Implementazione**:
```python
# src/tools/metrics.py
class ToolMetrics(BaseModel):
    tool_name = CharField()
    execution_count = IntegerField()
    total_duration_ms = IntegerField()
    success_count = IntegerField()
    error_count = IntegerField()
    last_used = DateTimeField()

# Wrapper per tracciare metriche
class MetricsWrapper(BaseTool):
    def __init__(self, tool: BaseTool):
        self.tool = tool
        super().__init__(name=tool.name, description=tool.description)
    
    def _run(self, *args, **kwargs):
        start = time.time()
        try:
            result = self.tool._run(*args, **kwargs)
            success = True
            return result
        except Exception as e:
            success = False
            raise
        finally:
            duration = (time.time() - start) * 1000
            self._record_metrics(duration, success)
```

**Dashboard**:
```
┌─────────────────────────────────┐
│ 📊 Statistiche Tools            │
├─────────────────────────────────┤
│ Tool         Usi  Successo  Avg │
│ Wikipedia    45   100%      1.2s│
│ Arxiv        23   95%       2.5s│
│ Filesystem   12   100%      0.3s│
│ Github       8    87%       3.1s│
└─────────────────────────────────┘
```

### 8.4 Tool Compositi

**Obiettivo**: Creare tools che combinano altri tools

**Implementazione**:
```python
class CompositeTool(Tool):
    """Tool che combina più tools"""
    
    def __init__(self, tools: List[Tool]):
        self.sub_tools = tools
        super().__init__(nome="Composite")
    
    def get_tool(self):
        # Combina tools in un workflow
        all_tools = []
        for tool in self.sub_tools:
            all_tools.extend(tool.get_tool())
        return all_tools

# Esempio: Research Tool
class ResearchTool(CompositeTool):
    def __init__(self):
        super().__init__([
            Arxiv(),
            Wikipedia(),
            DuckDuckGo()
        ])
```

### 8.5 Caching Intelligente

**Obiettivo**: Cache risultati per query ripetute

**Implementazione**:
```python
from functools import lru_cache
import hashlib

class CachedTool(BaseTool):
    def __init__(self, tool: BaseTool, ttl: int = 3600):
        self.tool = tool
        self.ttl = ttl
        self.cache = {}
        super().__init__(name=tool.name, description=tool.description)
    
    def _cache_key(self, *args, **kwargs):
        key_str = f"{args}:{kwargs}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _run(self, *args, **kwargs):
        key = self._cache_key(*args, **kwargs)
        
        # Controlla cache
        if key in self.cache:
            cached, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return cached
        
        # Esegui e salva in cache
        result = self.tool._run(*args, **kwargs)
        self.cache[key] = (result, time.time())
        return result
```

### 8.6 Tool Personalizzati via GUI

**Obiettivo**: Creare tools custom senza codice

**GUI**:
```
┌─────────────────────────────────┐
│ ✨ Crea Tool Personalizzato     │
├─────────────────────────────────┤
│ Nome:                           │
│ [MyCustomTool_________________] │
│                                 │
│ Descrizione:                    │
│ ┌─────────────────────────────┐ │
│ │ Tool per...                 │ │
│ └─────────────────────────────┘ │
│                                 │
│ Tipo:                           │
│ ○ API REST                      │
│ ○ Script Python                 │
│ ● Comando Shell                 │
│                                 │
│ Comando:                        │
│ [curl -X GET https://...______] │
│                                 │
│ Parametri:                      │
│ + query (string, required)      │
│ + limit (int, optional)         │
│                                 │
│ [💾 Crea Tool]                  │
└─────────────────────────────────┘
```

### 8.7 Versioning Tools

**Obiettivo**: Gestire versioni diverse dello stesso tool

**Implementazione**:
```python
class VersionedTool(Tool):
    def __init__(self, version: str = "1.0.0"):
        self.version = version
        super().__init__(nome=f"{self.__class__.__name__}@{version}")
    
    @classmethod
    def get_available_versions(cls) -> List[str]:
        """Ritorna versioni disponibili"""
        return ["1.0.0", "1.1.0", "2.0.0"]
    
    def migrate_config(self, old_version: str, new_version: str):
        """Migra configurazione tra versioni"""
        pass
```

### 8.8 Tool Marketplace

**Obiettivo**: Repository centralizzato di tools

**Caratteristiche**:
- Ricerca tools per categoria
- Ratings e reviews
- Installazione con un click
- Aggiornamenti automatici

**GUI**:
```
┌─────────────────────────────────┐
│ 🏪 Tool Marketplace             │
├─────────────────────────────────┤
│ Cerca: [_____________________🔍]│
│                                 │
│ Categorie:                      │
│ • Ricerca Web (12)              │
│ • Database (8)                  │
│ • File Management (15)          │
│ • API Integration (23)          │
│                                 │
│ ┌─────────────────────────────┐ │
│ │ 🌐 Advanced Web Search      │ │
│ │ ⭐⭐⭐⭐⭐ (45 reviews)        │ │
│ │ Ricerca avanzata con filtri │ │
│ │ [📥 Installa]               │ │
│ └─────────────────────────────┘ │
└─────────────────────────────────┘
```

---

## 9. Riferimenti

### 9.1 Documentazione

- **LangChain Tools**: https://python.langchain.com/docs/modules/agents/tools/
- **LangChain Community Tools**: https://github.com/langchain-ai/langchain-community/tree/main/libs/community/langchain_community/tools
- **BaseTool API**: https://api.python.langchain.com/en/latest/tools/langchain_core.tools.BaseTool.html
- **Pydantic**: https://docs.pydantic.dev/

### 9.2 Tools LangChain Community

Alcuni tools interessanti da langchain-community:

#### Ricerca e Informazioni
- `ArxivQueryRun`: Ricerca articoli scientifici
- `WikipediaQueryRun`: Ricerca su Wikipedia
- `DuckDuckGoSearchRun`: Ricerca web
- `GoogleSerperRun`: Ricerca Google
- `TavilySearchResults`: Ricerca ottimizzata per AI

#### Database e Storage
- `SQLDatabaseToolkit`: Interazione con database SQL
- `CassandraDatabase`: Query su Cassandra
- `SparkSQL`: Query su Spark

#### File e Filesystem
- `FileManagementToolkit`: Gestione file completa
- `ReadFileTool`: Lettura file
- `WriteFileTool`: Scrittura file

#### API e Servizi
- `GitHubToolkit`: Integrazione GitHub
- `GitLabToolkit`: Integrazione GitLab
- `SlackToolkit`: Integrazione Slack


#### API e Servizi
- `GitHubToolkit`: Integrazione GitHub
- `GitLabToolkit`: Integrazione GitLab
- `SlackToolkit`: Integrazione Slack
- `GmailToolkit`: Integrazione Gmail
- `JiraToolkit`: Integrazione Jira
- `ClickUpToolkit`: Integrazione ClickUp

#### Comunicazione
- `ElevenLabsText2SpeechTool`: Text-to-speech
- `HumanInputRun`: Input umano interattivo

#### Utilità
- `ShellTool`: Esecuzione comandi shell
- `PythonREPLTool`: Esecuzione codice Python
- `RequestsGetTool`: HTTP GET requests
- `RequestsPostTool`: HTTP POST requests

### 9.3 Codice Sorgente DapaBot

#### File Principali
- `src/tools/Tool.py`: Classe base astratta
- `src/tools/loader.py`: Caricamento dinamico tools
- `src/tools/Arxiv.py`: Esempio tool singolo
- `src/tools/Filesystem.py`: Esempio toolkit
- `src/tools/Github.py`: Esempio con variabili d'ambiente
- `src/tools/MCPTool.py`: Integrazione MCP

#### Database
- `src/models/tool.py`: Modello Peewee
- `src/ConfigurazioneDB.py`: Metodi CRUD (linee 386-480)

#### GUI
- `src/gui_utils.py`: Interfaccia Streamlit principale, gestione sidebar e integrazione tools/MCP
- `src/tools/gui_tools.py`: Dialog di configurazione tools (spostato da gui_utils.py per separazione responsabilità)

### 9.4 Risorse Aggiuntive

#### Tutorial e Guide
- [LangChain Tools Tutorial](https://python.langchain.com/docs/modules/agents/tools/custom_tools)
- [Creating Custom Tools](https://python.langchain.com/docs/modules/agents/tools/how_to/custom_tools)
- [Tool Calling Best Practices](https://python.langchain.com/docs/modules/model_io/chat/function_calling)

#### Community
- [LangChain Discord](https://discord.gg/langchain)
- [LangChain GitHub Discussions](https://github.com/langchain-ai/langchain/discussions)
- [Stack Overflow - langchain tag](https://stackoverflow.com/questions/tagged/langchain)

---

## Appendice A: Checklist Implementazione

### A.1 Checklist per Nuovo Tool

- [ ] **Analisi**
  - [ ] Identificato tool LangChain da usare
  - [ ] Comprese dipendenze necessarie
  - [ ] Identificati parametri configurabili
  - [ ] Verificate variabili d'ambiente richieste

- [ ] **Implementazione**
  - [ ] Creato file `src/tools/NomeTool.py`
  - [ ] Estesa classe `Tool`
  - [ ] Implementato `__init__()` con parametri
  - [ ] Implementato `get_tool()`
  - [ ] Gestiti errori e validazioni

- [ ] **Testing**
  - [ ] Test unitari per `get_tool()`
  - [ ] Test con parametri di default
  - [ ] Test con parametri personalizzati
  - [ ] Test gestione errori
  - [ ] Test integrazione con agent

- [ ] **Documentazione**
  - [ ] Docstring classe
  - [ ] Commenti codice complesso
  - [ ] Esempio d'uso
  - [ ] README se necessario

- [ ] **Integrazione**
  - [ ] Tool caricato da Loader
  - [ ] Configurazione salvabile in DB
  - [ ] Form GUI funzionante
  - [ ] Tool usabile in modalità agentica

### A.2 Checklist Debugging

- [ ] **Tool non caricato**
  - [ ] File in `src/tools/`?
  - [ ] Estende `Tool`?
  - [ ] `__init__()` chiama `super().__init__()`?
  - [ ] Nome univoco?

- [ ] **Errore dipendenze**
  - [ ] Pacchetti in `pacchetti_python_necessari`?
  - [ ] Nome modulo corretto?
  - [ ] Pacchetto installabile con `uv pip install`?

- [ ] **Tool non funziona**
  - [ ] Variabili d'ambiente configurate?
  - [ ] Parametri validi?
  - [ ] API key corretta?
  - [ ] Rete accessibile (per API remote)?

- [ ] **Errore in modalità agentica**
  - [ ] Tool attivo in GUI?
  - [ ] Modalità agentica abilitata?
  - [ ] Descrizione tool chiara per LLM?
  - [ ] Schema argomenti corretto?

---

## Appendice B: FAQ

### B.1 Domande Generali

**Q: Quanti tools posso avere attivi contemporaneamente?**  
A: Non c'è un limite tecnico, ma troppi tools possono confondere l'agent. Consigliato: 5-10 tools per sessione.

**Q: I tools funzionano solo in modalità agentica?**  
A: Sì, i tools sono progettati per essere usati dagli agenti LangChain.

**Q: Posso usare tools di altre librerie oltre LangChain?**  
A: Sì, basta wrappare il tool in una classe che estende `BaseTool`.

### B.2 Configurazione

**Q: Dove vengono salvate le configurazioni?**  
A: Nel database SQLite `config.db`, tabella `tool`.

**Q: Come resetto la configurazione di un tool?**  
A: Disattiva e riattiva il tool, oppure elimina e ricrea la configurazione.

**Q: Le variabili d'ambiente sono persistenti?**  
A: Sì, vengono salvate nel database e ricaricate ad ogni avvio.

### B.3 Sviluppo

**Q: Devo riavviare l'app dopo aver aggiunto un tool?**  
A: Sì, il Loader carica i tools all'avvio.

**Q: Posso modificare un tool esistente?**  
A: Sì, modifica il file e riavvia l'app. Le configurazioni in DB rimangono.

**Q: Come debuggo un tool?**  
A: Usa logging, test unitari, e testa il tool direttamente prima di usarlo nell'agent.

### B.4 Performance

**Q: I tools rallentano l'agent?**  
A: Dipende dal tool. Tools che chiamano API esterne possono essere lenti.

**Q: Posso cachare i risultati?**  
A: Sì, implementa un wrapper con cache (vedi sezione 8.5).

**Q: Come ottimizzare le performance?**  
A: Usa solo i tools necessari, implementa timeout, considera il caching.

---

**Fine del Manuale**

---

*Questo documento è stato generato da IBM Bob.*  
*Per aggiornamenti e correzioni, consultare il repository del progetto.*  
*Versione: 1.0 - Data: 19 Febbraio 2026*
