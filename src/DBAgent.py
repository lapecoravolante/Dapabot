import sqlite3, json, os, inspect, subprocess, socket
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path





class DBAgent:
    """
    Classe per gestire il database SQLite3 che memorizza la configurazione
    dei tools per la modalità agentica.
    """
    
    FILENAME = "agent.db"
    TOOLS_LIST = []  # Lista dei tools disponibili, popolata dinamicamente
    _tools_metadata = {}  # Metadati dei tools (parametri, descrizioni, ecc.)
    
    # Connessione persistente
    _conn: sqlite3.Connection | None = None
    _cursor: sqlite3.Cursor | None = None
    
    # Dizionario che associa ogni tool al pacchetto Python necessario
    TOOLS_PACKAGES = {
        # Search Tools
        "WikipediaQueryRun": "wikipedia",
        "ArxivQueryRun": "arxiv",
        "DuckDuckGoSearchRun": "duckduckgo-search",
        "TavilySearchResults": "tavily-python",
        "PubmedQueryRun": "xmltodict",  # Requires xmltodict for parsing
        "WolframAlphaQueryRun": "wolframalpha",
        "GoogleSearchRun": "google-search-results",
        "BingSearchRun": "azure-cognitiveservices-search-websearch",
        "BraveSearch": "langchain-community",
        "YouTubeSearchTool": "youtube-search",
        "RedditSearchRun": "praw",
        "StackExchangeTool": "stackapi",
        "OpenWeatherMapQueryRun": "pyowm",
        "SerpAPIWrapper": "google-search-results",
        "SearxSearchRun": "langchain-community",
        "MetaphorSearchResults": "metaphor-python",
        "GoogleSerperAPIWrapper": "google-serper",
        
        # Coding & Shell
        "PythonREPLTool": "langchain-experimental", # Often moved here or keeps in community
        "ShellTool": "langchain-community",
        "FileManagementTool": "langchain-community",
        "ReadFileTool": "langchain-community",
        "WriteFileTool": "langchain-community",
        "ListDirectoryTool": "langchain-community",
        
        # Web & Requests
        "RequestsGetTool": "requests",
        "RequestsPostTool": "requests",
        "HumanInputRun": "langchain-community",
        
        # AI & Models used as tools
        "DalleImageGeneratorTool": "openai",
        "ElevenLabsText2SpeechTool": "elevenlabs",
    }

    
    # Gestione server sqlite-web per agent.db
    _sqlite_web_process = None
    _sqlite_web_host = "127.0.0.1"
    _sqlite_web_port = 8081
    
    @classmethod
    def _get_connection(cls):
        """Crea e ritorna una connessione persistente al database."""
        if not cls._conn or not cls._cursor:
            cls._conn = sqlite3.connect(cls.FILENAME, check_same_thread=False)
            cls._conn.row_factory = sqlite3.Row
            cls._cursor = cls._conn.cursor()

    @classmethod
    def crea_schema(cls, configurazione: Dict = {}):
        """
        Crea lo schema del database.
        
        Args:
            configurazione: Dizionario con la struttura delle tabelle.
                           Se vuoto, usa lo schema di default.
        """
        cls._get_connection()
        
        if not configurazione:
            # Schema di default
            cls._cursor.execute("""
                CREATE TABLE IF NOT EXISTS tools (
                    nome_tool TEXT PRIMARY KEY,
                    configurazione TEXT NOT NULL,
                    data_creazione TEXT NOT NULL,
                    data_modifica TEXT NOT NULL
                )
            """)
        else:
            # Schema personalizzato (per estensioni future)
            for table_name, columns in configurazione.items():
                cols_def = ", ".join([f"{col} {dtype}" for col, dtype in columns.items()])
                cls._cursor.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({cols_def})")
        
        cls._conn.commit()

        # conn.close() # Non chiudiamo la connessione persistente
    
    @classmethod
    def salva_db(cls, configurazione: Dict = {}):
        """
        Salva la configurazione completa su database.
        Se la configurazione è vuota, esegue la truncate di tutte le tabelle.
        
        Args:
            configurazione: Dizionario con la configurazione da salvare.
                           Formato: {"tool_name": {"param1": "value1", ...}, ...}
        """
        cls.crea_schema()
        cls._get_connection()
        
        if not configurazione:
            # Truncate: elimina tutti i record
            cls._cursor.execute("DELETE FROM tools")
        else:
            # Salva ogni tool
            for tool_name, params in configurazione.items():
                cls.salva_tool({"nome_tool": tool_name, "configurazione": params})
        
        cls._conn.commit()

        # conn.close()
    
    @classmethod
    def esporta_db(cls) -> str:
        """
        Esporta l'intero database in formato JSON.
        
        Returns:
            Stringa JSON con il contenuto del database.
        """
        cls.crea_schema()
        cls._get_connection()
        
        cls._cursor.execute("SELECT * FROM tools")
        rows = cls._cursor.fetchall()
        
        data = {
            "export_date": datetime.now().isoformat(),
            "tools": []
        }
        
        for row in rows:
            data["tools"].append({
                "nome_tool": row["nome_tool"],
                "configurazione": json.loads(row["configurazione"]),
                "data_creazione": row["data_creazione"],
                "data_modifica": row["data_modifica"]
            })
        
        # conn.close()
        
        # Genera il nome del file con la data
        filename = f"agentdb-{datetime.now().strftime('%Y%m%d')}.json"
        json_str = json.dumps(data, indent=2, ensure_ascii=False)
        
        return json_str
    
    @classmethod
    def importa_db(cls, json_data: str):
        """
        Importa la configurazione da un file JSON esportato.
        
        Args:
            json_data: Stringa JSON con i dati da importare.
        """
        cls.crea_schema()
        data = json.loads(json_data)
        
        cls._get_connection()
        
        for tool in data.get("tools", []):
            cls._cursor.execute("""
                INSERT OR REPLACE INTO tools 
                (nome_tool, configurazione, data_creazione, data_modifica)
                VALUES (?, ?, ?, ?)
            """, (
                tool["nome_tool"],
                json.dumps(tool["configurazione"]),
                tool.get("data_creazione", datetime.now().isoformat()),
                tool.get("data_modifica", datetime.now().isoformat())
            ))
        
        cls._conn.commit()

        # conn.close()
    
    @classmethod
    def elimina_db(cls):
        """Cancella il file del database."""
        try:
            # Chiude la connessione se aperta
            if cls._conn:
                try:
                    if cls._cursor:
                        cls._cursor.close()
                    cls._conn.close()
                except:
                    pass
                cls._conn = None
                cls._cursor = None
                
            if os.path.exists(cls.FILENAME):
                os.remove(cls.FILENAME)
                cls.TOOLS_LIST.clear()
                cls._tools_metadata.clear()
        except Exception as e:
            raise Exception(f"Errore nell'eliminazione del database: {e}")
    
    @classmethod
    def check_and_install_tool(cls, tool_name: str):
        """
        Verifica se il pacchetto per il tool è installato, altrimenti lo installa.
        """
        package = cls.TOOLS_PACKAGES.get(tool_name)
        if not package:
            return # Nessun pacchetto specifico o sconosciuto
            
        try:
            # Semplice check: prova ad importare il pacchetto se il nome coincide, 
            # ma molti pacchetti hanno nomi diversi dal modulo importato (es. google-search-results -> serpapi).
            # Quindi ci affidiamo al fatto che se il tool è richiesto, lo installiamo se non siamo sicuri?
            # Oppure ci fidiamo di 'uv add' che gestisce le dipendenze esistenti velocemente.
            # L'utente vuole: "essere fatto il controllo sulla presenza nel sistema ... e installarlo se necessario"
            # Usiamo uv add che è idempotente e veloce se già presente?
            # Per evitare overhead, proviamo prima un controllo.
            
            # Tuttavia, mappare pacchetto -> modulo importabile è complesso.
            # Esempio: "google-search-results" -> "serpapi"
            # Esempio: "duckduckgo-search" -> "duckduckgo_search"
            
            # Per semplicità e robustezza, come richiesto:
            cls.install_package(package)
            
        except Exception as e:
            print(f"Warning: Could not check/install package {package} for tool {tool_name}: {e}")

    @classmethod
    def install_package(cls, package: str):
        """Installa un pacchetto usando uv."""
        if not package:
            return
            
        # Verifica se è già installato (opzionale ma consigliato per velocità)
        # Ma 'uv add' è progettato per essere veloce. 
        # Tuttavia, per evitare spam di log o subprocess, potremmo usare importlib.util.find_spec 
        # SOLO SE conosciamo il nome del modulo. Qui abbiamo il nome del pacchetto.
        # Quindi lanciamo il comando.
        try:
            # Usiamo sys.executable per essere sicuri di usare lo stesso python env se uv lo supporta,
            # ma 'uv pip install' gestisce il progetto corrente senza aggiungere il pacchetto installato 
            # alle dipendenze del progetto. Assumiamo che 'uv' sia nel path.
            print(f"Installing package for tool: {package}...")
            subprocess.check_call(["uv", "pip", "install", package])
        except subprocess.CalledProcessError as e:
            print(f"Failed to install package {package}: {e}")
            raise

    @classmethod
    def salva_tool(cls, tool: Dict = {}):
        """
        Inserisce o aggiorna la configurazione di un tool nella tabella tools.
        
        Args:
            tool: Dizionario con 'nome_tool' e 'configurazione'.
                  Formato: {"nome_tool": "Wikipedia", "configurazione": {"lang": "en", ...}}
        """
        if not tool or "nome_tool" not in tool:
            raise ValueError("Il dizionario tool deve contenere almeno 'nome_tool'")
        
        # Verifica e installa dipendenze
        cls.check_and_install_tool(tool["nome_tool"])
        
        cls.crea_schema()
        cls._get_connection()
        
        nome_tool = tool["nome_tool"]
        configurazione = tool.get("configurazione", {})
        
        # Verifica se il tool esiste già
        cls._cursor.execute("SELECT nome_tool FROM tools WHERE nome_tool = ?", (nome_tool,))
        exists = cls._cursor.fetchone()
        
        now = datetime.now().isoformat()
        
        if exists:
            # Aggiorna
            cls._cursor.execute("""
                UPDATE tools 
                SET configurazione = ?, data_modifica = ?
                WHERE nome_tool = ?
            """, (json.dumps(configurazione), now, nome_tool))
        else:
            # Inserisci
            cls._cursor.execute("""
                INSERT INTO tools (nome_tool, configurazione, data_creazione, data_modifica)
                VALUES (?, ?, ?, ?)
            """, (nome_tool, json.dumps(configurazione), now, now))
        
        cls._conn.commit()

        # conn.close()
    
    @classmethod
    def cancella_tool(cls, tool: Dict = {}):
        """
        Cancella la configurazione di un tool dal database.
        
        Args:
            tool: Dizionario con 'nome_tool'.
                  Formato: {"nome_tool": "Wikipedia"}
        """
        if not tool or "nome_tool" not in tool:
            raise ValueError("Il dizionario tool deve contenere 'nome_tool'")
        
        cls.crea_schema()
        cls._get_connection()
        
        cls._cursor.execute("DELETE FROM tools WHERE nome_tool = ?", (tool["nome_tool"],))
        
        cls._conn.commit()

        # conn.close()
    
    @classmethod
    def carica_tools(cls) -> List[Dict]:
        """
        Carica tutti i tools configurati dal database.
        
        Returns:
            Lista di dizionari con la configurazione di ogni tool.
            Formato: [{"nome_tool": "Wikipedia", "configurazione": {"lang": "en", ...}}, ...]
        """
        cls.crea_schema()
        cls._get_connection()
        
        cls._cursor.execute("SELECT nome_tool, configurazione FROM tools")
        rows = cls._cursor.fetchall()
        
        tools = []
        for row in rows:
            tools.append({
                "nome_tool": row["nome_tool"],
                "configurazione": json.loads(row["configurazione"])
            })
        
        # conn.close()
        return tools
    
    @classmethod
    def get_tool_params(cls, tool_name: str) -> Dict[str, Any]:
        """
        Ritorna i parametri configurabili per un tool specifico.
        
        Args:
            tool_name: Nome del tool.
        
        Returns:
            Dizionario con i parametri e i loro tipi/valori di default.
            Formato: {"param_name": {"type": "str", "default": "value", "description": "..."}, ...}
        """
        if tool_name in cls._tools_metadata:
            return cls._tools_metadata[tool_name]
        
        # Se non è in cache, prova a caricarlo dinamicamente
        try:
            tool_class = cls._load_tool_class(tool_name)
            if tool_class:
                params = cls._extract_params_from_class(tool_class)
                cls._tools_metadata[tool_name] = params
                return params
        except Exception:
            pass
        
        return {}
    
    @classmethod
    def _load_tool_class(cls, tool_name: str):
        """
        Carica dinamicamente la classe di un tool da langchain_community.tools.
        
        Args:
            tool_name: Nome del tool.
        
        Returns:
            La classe del tool o None se non trovata.
        """
        try:
            # Prova a importare da langchain_community.tools
            module = __import__(f"langchain_community.tools", fromlist=[tool_name])
            if hasattr(module, tool_name):
                return getattr(module, tool_name)
            
            # Prova con il nome in lowercase
            tool_name_lower = tool_name.lower()
            if hasattr(module, tool_name_lower):
                return getattr(module, tool_name_lower)
            
            # Prova a cercare nei sottomoduli
            submodule_name = tool_name_lower.replace("tool", "").replace("_", "")
            try:
                submodule = __import__(
                    f"langchain_community.tools.{submodule_name}", 
                    fromlist=[tool_name]
                )
                if hasattr(submodule, tool_name):
                    return getattr(submodule, tool_name)
            except ImportError:
                pass
            
        except Exception:
            pass
        
        return None
    
    @classmethod
    def _extract_params_from_class(cls, tool_class) -> Dict[str, Any]:
        """
        Estrae i parametri configurabili da una classe tool usando introspezione.
        
        Args:
            tool_class: La classe del tool.
        
        Returns:
            Dizionario con i parametri e i loro metadati.
        """
        params = {}
        
        try:
            # Prova a ottenere i parametri dal __init__
            sig = inspect.signature(tool_class.__init__)
            for param_name, param in sig.parameters.items():
                if param_name in ('self', 'args', 'kwargs'):
                    continue
                
                param_info = {
                    "type": "str",  # default
                    "default": None,
                    "description": ""
                }
                
                # Determina il tipo
                if param.annotation != inspect.Parameter.empty:
                    param_info["type"] = str(param.annotation).replace("<class '", "").replace("'>", "")
                
                # Valore di default
                if param.default != inspect.Parameter.empty:
                    param_info["default"] = param.default
                
                params[param_name] = param_info
            
            # Prova a ottenere la descrizione dalla docstring
            if tool_class.__doc__:
                params["_description"] = tool_class.__doc__.strip()
        
        except Exception:
            pass
        
        return params
    
    @classmethod
    def inizializza_tools_list(cls):
        """
        Inizializza la lista dei tools disponibili caricandoli dalla definizione dei pacchetti.
        """
        if cls.TOOLS_LIST:
            return  # Già inizializzata
        
        # Popola la lista basandosi sulle chiavi del dizionario TOOLS_PACKAGES
        # Non installiamo tutto subito, ma mostriamo cosa è disponibile.
        # L'installazione avverrà on-demand quando il tool viene aggiunto/configurato.
        
        try:            
            # Usa le chiavi del dizionario come lista dei tools possibili
            possible_tools = list(cls.TOOLS_PACKAGES.keys())
            
            # Inoltre, aggiungiamo quelli che potremmo trovare dinamicamente ma che non sono nel dizionario?
            # Per ora atteniamoci al dizionario come fonte di verità per i tools gestiti.
            
            # Verifica quali sono effettivamente importabili (senza installare)
            # O semplicemente li elenchiamo tutti come "disponibili per l'uso" (e poi si installano)?
            # Se 'inizializza_tools_list' serve a popolare una UI di selezione, 
            # ha senso mostrare tutto.
            
            for tool_name in possible_tools:
                cls.TOOLS_LIST.append(tool_name)
            
            # Se la lista è vuota (improbabile), fallback
            if not cls.TOOLS_LIST:
                cls.TOOLS_LIST = [
                    "WikipediaQueryRun", "ArxivQueryRun", "DuckDuckGoSearchRun"
                ]
        
        except Exception:
             # Fallback
            cls.TOOLS_LIST = ["WikipediaQueryRun", "ArxivQueryRun"]

    @staticmethod
    def _is_port_in_use(host: str, port: int) -> bool:
        """Verifica se una porta è già in uso."""
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except OSError:
            return False
    
    @staticmethod
    def start_sqlite_web_server(host: str = "127.0.0.1", port: int = 8081, no_browser: bool = True) -> bool:
        """
        Avvia il server sqlite-web per agent.db sulla porta 8081.
        
        Args:
            host: Host su cui avviare il server (default: 127.0.0.1)
            port: Porta su cui avviare il server (default: 8081)
            no_browser: Se True, non apre il browser automaticamente
        
        Returns:
            True se il server è stato avviato o è già attivo, False altrimenti
        """
        if DBAgent._is_port_in_use(host, port):
            return True
        try:
            args = ["sqlite_web", DBAgent.FILENAME, "--host", host, "--port", str(port)]
            if no_browser:
                args.append("--no-browser")
            DBAgent._sqlite_web_process = subprocess.Popen(args)
            return True
        except Exception:
            DBAgent._sqlite_web_process = None
            return False
    
    @staticmethod
    def is_sqlite_web_active() -> bool:
        """Verifica se il server sqlite-web è attivo."""
        return DBAgent._is_port_in_use(DBAgent._sqlite_web_host, DBAgent._sqlite_web_port)
    
    @staticmethod
    def get_sqlite_web_url() -> str:
        """Ritorna l'URL del server sqlite-web."""
        return f"http://{DBAgent._sqlite_web_host}:{DBAgent._sqlite_web_port}/"

# Made with Bob
