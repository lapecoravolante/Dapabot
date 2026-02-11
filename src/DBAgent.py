import sqlite3, json, os, inspect, subprocess, socket
from datetime import datetime
from pathlib import Path





class DBAgent:
    """
    Classe per gestire il database SQLite3 che memorizza la configurazione
    dei tools per la modalità agentica.
    """
    
    FILENAME = "agent.db"
    
    # Connessione persistente
    _conn: sqlite3.Connection | None = None
    _cursor: sqlite3.Cursor | None = None

    
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
    def crea_schema(cls, configurazione: dict = {}):
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
    def salva_db(cls, configurazione: dict = {}):
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
        except Exception as e:
            raise Exception(f"Errore nell'eliminazione del database: {e}")
    
    @classmethod
    def salva_tool(cls, tool: dict = {}):
        """
        Inserisce o aggiorna la configurazione di un tool nella tabella tools.
        
        Args:
            tool: Dizionario con 'nome_tool' e 'configurazione'.
                  Formato: {"nome_tool": "Wikipedia", "configurazione": {"lang": "en", ...}}
        """
        if not tool or "nome_tool" not in tool:
            raise ValueError("Il dizionario tool deve contenere almeno 'nome_tool'")
        
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
    def cancella_tool(cls, tool: dict = {}):
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
    def carica_tools(cls) -> list[dict]:
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
