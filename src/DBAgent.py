import sqlite3
import json
import os
import inspect
import subprocess
import socket
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
    
    # Gestione server sqlite-web per agent.db
    _sqlite_web_process = None
    _sqlite_web_host = "127.0.0.1"
    _sqlite_web_port = 8081
    
    @staticmethod
    def _get_connection():
        """Crea e ritorna una connessione al database."""
        conn = sqlite3.connect(DBAgent.FILENAME)
        conn.row_factory = sqlite3.Row
        return conn
    
    @staticmethod
    def crea_schema(configurazione: Dict = {}):
        """
        Crea lo schema del database.
        
        Args:
            configurazione: Dizionario con la struttura delle tabelle.
                           Se vuoto, usa lo schema di default.
        """
        conn = DBAgent._get_connection()
        cursor = conn.cursor()
        
        if not configurazione:
            # Schema di default
            cursor.execute("""
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
                cursor.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({cols_def})")
        
        conn.commit()
        conn.close()
    
    @staticmethod
    def salva_db(configurazione: Dict = {}):
        """
        Salva la configurazione completa su database.
        Se la configurazione è vuota, esegue la truncate di tutte le tabelle.
        
        Args:
            configurazione: Dizionario con la configurazione da salvare.
                           Formato: {"tool_name": {"param1": "value1", ...}, ...}
        """
        DBAgent.crea_schema()
        conn = DBAgent._get_connection()
        cursor = conn.cursor()
        
        if not configurazione:
            # Truncate: elimina tutti i record
            cursor.execute("DELETE FROM tools")
        else:
            # Salva ogni tool
            for tool_name, params in configurazione.items():
                DBAgent.salva_tool({"nome_tool": tool_name, "configurazione": params})
        
        conn.commit()
        conn.close()
    
    @staticmethod
    def esporta_db() -> str:
        """
        Esporta l'intero database in formato JSON.
        
        Returns:
            Stringa JSON con il contenuto del database.
        """
        DBAgent.crea_schema()
        conn = DBAgent._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM tools")
        rows = cursor.fetchall()
        
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
        
        conn.close()
        
        # Genera il nome del file con la data
        filename = f"agentdb-{datetime.now().strftime('%Y%m%d')}.json"
        json_str = json.dumps(data, indent=2, ensure_ascii=False)
        
        return json_str
    
    @staticmethod
    def importa_db(json_data: str):
        """
        Importa la configurazione da un file JSON esportato.
        
        Args:
            json_data: Stringa JSON con i dati da importare.
        """
        DBAgent.crea_schema()
        data = json.loads(json_data)
        
        conn = DBAgent._get_connection()
        cursor = conn.cursor()
        
        for tool in data.get("tools", []):
            cursor.execute("""
                INSERT OR REPLACE INTO tools 
                (nome_tool, configurazione, data_creazione, data_modifica)
                VALUES (?, ?, ?, ?)
            """, (
                tool["nome_tool"],
                json.dumps(tool["configurazione"]),
                tool.get("data_creazione", datetime.now().isoformat()),
                tool.get("data_modifica", datetime.now().isoformat())
            ))
        
        conn.commit()
        conn.close()
    
    @staticmethod
    def elimina_db():
        """Cancella il file del database."""
        try:
            if os.path.exists(DBAgent.FILENAME):
                os.remove(DBAgent.FILENAME)
                DBAgent.TOOLS_LIST.clear()
                DBAgent._tools_metadata.clear()
        except Exception as e:
            raise Exception(f"Errore nell'eliminazione del database: {e}")
    
    @staticmethod
    def salva_tool(tool: Dict = {}):
        """
        Inserisce o aggiorna la configurazione di un tool nella tabella tools.
        
        Args:
            tool: Dizionario con 'nome_tool' e 'configurazione'.
                  Formato: {"nome_tool": "Wikipedia", "configurazione": {"lang": "en", ...}}
        """
        if not tool or "nome_tool" not in tool:
            raise ValueError("Il dizionario tool deve contenere almeno 'nome_tool'")
        
        DBAgent.crea_schema()
        conn = DBAgent._get_connection()
        cursor = conn.cursor()
        
        nome_tool = tool["nome_tool"]
        configurazione = tool.get("configurazione", {})
        
        # Verifica se il tool esiste già
        cursor.execute("SELECT nome_tool FROM tools WHERE nome_tool = ?", (nome_tool,))
        exists = cursor.fetchone()
        
        now = datetime.now().isoformat()
        
        if exists:
            # Aggiorna
            cursor.execute("""
                UPDATE tools 
                SET configurazione = ?, data_modifica = ?
                WHERE nome_tool = ?
            """, (json.dumps(configurazione), now, nome_tool))
        else:
            # Inserisci
            cursor.execute("""
                INSERT INTO tools (nome_tool, configurazione, data_creazione, data_modifica)
                VALUES (?, ?, ?, ?)
            """, (nome_tool, json.dumps(configurazione), now, now))
        
        conn.commit()
        conn.close()
    
    @staticmethod
    def cancella_tool(tool: Dict = {}):
        """
        Cancella la configurazione di un tool dal database.
        
        Args:
            tool: Dizionario con 'nome_tool'.
                  Formato: {"nome_tool": "Wikipedia"}
        """
        if not tool or "nome_tool" not in tool:
            raise ValueError("Il dizionario tool deve contenere 'nome_tool'")
        
        DBAgent.crea_schema()
        conn = DBAgent._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM tools WHERE nome_tool = ?", (tool["nome_tool"],))
        
        conn.commit()
        conn.close()
    
    @staticmethod
    def carica_tools() -> List[Dict]:
        """
        Carica tutti i tools configurati dal database.
        
        Returns:
            Lista di dizionari con la configurazione di ogni tool.
            Formato: [{"nome_tool": "Wikipedia", "configurazione": {"lang": "en", ...}}, ...]
        """
        DBAgent.crea_schema()
        conn = DBAgent._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT nome_tool, configurazione FROM tools")
        rows = cursor.fetchall()
        
        tools = []
        for row in rows:
            tools.append({
                "nome_tool": row["nome_tool"],
                "configurazione": json.loads(row["configurazione"])
            })
        
        conn.close()
        return tools
    
    @staticmethod
    def get_tool_params(tool_name: str) -> Dict[str, Any]:
        """
        Ritorna i parametri configurabili per un tool specifico.
        
        Args:
            tool_name: Nome del tool.
        
        Returns:
            Dizionario con i parametri e i loro tipi/valori di default.
            Formato: {"param_name": {"type": "str", "default": "value", "description": "..."}, ...}
        """
        if tool_name in DBAgent._tools_metadata:
            return DBAgent._tools_metadata[tool_name]
        
        # Se non è in cache, prova a caricarlo dinamicamente
        try:
            tool_class = DBAgent._load_tool_class(tool_name)
            if tool_class:
                params = DBAgent._extract_params_from_class(tool_class)
                DBAgent._tools_metadata[tool_name] = params
                return params
        except Exception:
            pass
        
        return {}
    
    @staticmethod
    def _load_tool_class(tool_name: str):
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
    
    @staticmethod
    def _extract_params_from_class(tool_class) -> Dict[str, Any]:
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
    
    @staticmethod
    def inizializza_tools_list():
        """
        Inizializza la lista dei tools disponibili caricandoli dinamicamente
        da langchain_community.tools.
        """
        if DBAgent.TOOLS_LIST:
            return  # Già inizializzata
        
        try:
            import langchain_community.tools as lc_tools
            
            # Lista manuale dei tools più comuni e stabili
            common_tools = [
                "WikipediaQueryRun",
                "ArxivQueryRun", 
                "DuckDuckGoSearchRun",
                "TavilySearchResults",
                "PubmedQueryRun",
                "WolframAlphaQueryRun",
                "GoogleSearchRun",
                "BingSearchRun",
                "BraveSearch",
                "YouTubeSearchTool",
                "RedditSearchRun",
                "StackExchangeTool",
                "OpenWeatherMapQueryRun",
                "HumanInputRun",
                "PythonREPLTool",
                "ShellTool",
                "RequestsGetTool",
                "RequestsPostTool",
                "FileManagementTool",
                "ReadFileTool",
                "WriteFileTool",
                "ListDirectoryTool",
            ]
            
            # Verifica quali sono effettivamente disponibili
            for tool_name in common_tools:
                try:
                    if hasattr(lc_tools, tool_name):
                        DBAgent.TOOLS_LIST.append(tool_name)
                    else:
                        # Prova a caricarlo dinamicamente
                        tool_class = DBAgent._load_tool_class(tool_name)
                        if tool_class:
                            DBAgent.TOOLS_LIST.append(tool_name)
                except Exception:
                    continue
            
            # Se la lista è ancora vuota, usa una lista di fallback
            if not DBAgent.TOOLS_LIST:
                DBAgent.TOOLS_LIST = [
                    "WikipediaQueryRun",
                    "ArxivQueryRun",
                    "DuckDuckGoSearchRun",
                    "PythonREPLTool"
                ]
        
        except ImportError:
            # langchain_community non disponibile, usa lista minimale
            DBAgent.TOOLS_LIST = [
                "WikipediaQueryRun",
                "ArxivQueryRun",
                "DuckDuckGoSearchRun"
            ]
    
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
