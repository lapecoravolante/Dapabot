import sqlite3, os, json, subprocess, socket, base64
from datetime import datetime
from typing import List
from uuid import uuid4
from src.Messaggio import Messaggio
from src.Allegato import Allegato

class StoricoChat:
    nome_db: str = "storico_chat.db"
    _sqlite_web_process = None
    _sqlite_web_host = "127.0.0.1"
    _sqlite_web_port = 8080

    @classmethod
    def _get_connection(cls):
        conn = sqlite3.connect(cls.nome_db)
        conn.row_factory = sqlite3.Row
        return conn

    @classmethod
    def _ensure_schema(cls):
        """Crea tutte le tabelle se non esistono."""
        conn = cls._get_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Provider (
            id TEXT PRIMARY KEY
        );
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Modello (
            id TEXT PRIMARY KEY,
            provider TEXT,
            FOREIGN KEY(provider) REFERENCES Provider(id) ON DELETE CASCADE
        );
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Messaggio (
            id TEXT NOT NULL,
            ruolo TEXT NOT NULL,
            contenuto TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            PRIMARY KEY (id, timestamp)
        );
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Chat (
            provider TEXT NOT NULL,
            modello TEXT NOT NULL,
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            UNIQUE(provider, modello),
            FOREIGN KEY(provider) REFERENCES Provider(id) ON DELETE CASCADE,
            FOREIGN KEY(modello) REFERENCES Modello(id) ON DELETE CASCADE
        );
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS MessaggiInChat (
            id_chat INTEGER,
            messaggio_id TEXT,
            messaggio_timestamp TEXT,
            PRIMARY KEY (id_chat, messaggio_id, messaggio_timestamp),
            FOREIGN KEY (id_chat) REFERENCES Chat(id) ON DELETE CASCADE,
            FOREIGN KEY (messaggio_id, messaggio_timestamp) REFERENCES Messaggio(id, timestamp) ON DELETE CASCADE
        );
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Allegato (
            id TEXT PRIMARY KEY,
            messaggio_id TEXT NOT NULL,
            messaggio_timestamp TEXT NOT NULL,
            tipo TEXT NOT NULL,
            mime_type TEXT,
            contenuto TEXT,
            filename TEXT,
            FOREIGN KEY(messaggio_id, messaggio_timestamp) REFERENCES Messaggio(id, timestamp) ON DELETE CASCADE
        );
        """)

        conn.commit()
        conn.close()

    @classmethod
    def _encode_allegato(cls, allegato: Allegato) -> str:
        """
        Restituisce la rappresentazione Base64 dell'allegato:
        - se allegato.contenuto è binario, lo codifica
        - se è plain/text ritorna direttamente la stringa
        """
        contenuto = allegato.contenuto
        tipo=allegato.tipo
        return contenuto if tipo.startswith("text")  else base64.b64encode(contenuto).decode("utf-8") 

    @classmethod
    def salva_chat(cls, provider: str, modello: str, cronologia: List[Messaggio]):
        cls._ensure_schema()
        conn = cls._get_connection()
        cursor = conn.cursor()

        cursor.execute("INSERT OR IGNORE INTO Provider (id) VALUES (?);", (provider,))
        cursor.execute(
            "INSERT OR IGNORE INTO Modello (id, provider) VALUES (?, ?);",
            (modello, provider)
        )

        cursor.execute(
            "SELECT id FROM Chat WHERE provider=? AND modello=?;",
            (provider, modello)
        )
        row = cursor.fetchone()

        if row:
            chat_id = row["id"]
            cursor.execute("DELETE FROM MessaggiInChat WHERE id_chat=?;", (chat_id,))
        else:
            cursor.execute(
                "INSERT INTO Chat (provider, modello) VALUES (?, ?);",
                (provider, modello)
            )
            conn.commit()
            cursor.execute(
                "SELECT id FROM Chat WHERE provider=? AND modello=?;",
                (provider, modello)
            )
            chat_id = cursor.fetchone()["id"]

        for mess in cronologia:
            msg_id = mess.get_id()
            ruolo = mess.get_ruolo()
            testo = mess.get_testo()
            timestamp=mess.timestamp().isoformat()

            cursor.execute("""
            INSERT OR IGNORE INTO Messaggio (id, ruolo, contenuto, timestamp)
            VALUES (?, ?, ?, ?);
            """, (msg_id, ruolo, testo, timestamp))

            cursor.execute("""
            INSERT OR IGNORE INTO MessaggiInChat
            (id_chat, messaggio_id, messaggio_timestamp)
            VALUES (?, ?, ?);
            """, (chat_id, msg_id, timestamp))


            # salva gli allegati codificandoli in Base64 (se serve)
            for allegato in mess.get_allegati():
                allegato_uuid = f"{msg_id}-{uuid4().hex}"
                contenuto = cls._encode_allegato(allegato)
                filename=allegato.filename
                cursor.execute("""
                INSERT OR IGNORE INTO Allegato
                (id, messaggio_id, messaggio_timestamp, tipo, mime_type, contenuto, filename)
                VALUES (?, ?, ?, ?, ?, ?, ?);
                """, (allegato_uuid, msg_id, timestamp, allegato.tipo, allegato.mime_type, contenuto, filename))

        conn.commit()
        conn.close()

    @classmethod
    def carica_cronologia(cls, provider: str, modello: str) -> List[Messaggio]:
        cls._ensure_schema()
        conn = cls._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
        SELECT c.id FROM Chat c
        WHERE provider=? AND modello=?;
        """, (provider, modello))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return []

        chat_id = row["id"]

        cursor.execute("""
        SELECT m.id, m.ruolo, m.contenuto, m.timestamp
        FROM MessaggiInChat mic
        JOIN Messaggio m
        ON mic.messaggio_id = m.id
        AND mic.messaggio_timestamp = m.timestamp
        WHERE mic.id_chat = ?
        ORDER BY m.timestamp;
        """, (chat_id,))

        messaggi = []
        for r in cursor.fetchall():
            msg_id = r["id"]
            testo = r["contenuto"]
            ruolo = r["ruolo"]
            timestamp=r["timestamp"]

            # carica gli allegati salvati in Base64
            cursor.execute("""
            SELECT tipo, mime_type, contenuto, filename FROM Allegato
            WHERE messaggio_id=? and messaggio_timestamp=?;
            """, (msg_id, timestamp))
            allegati = []
            for a in cursor.fetchall():
                tipo=a["tipo"]
                contenuto = a["contenuto"] if tipo.startswith("text") else base64.b64decode(a["contenuto"])
                mime_type=a["mime_type"]
                filename=a["filename"]
                # Decodifico il contenuto dell'allegato
                allegati.append(Allegato(tipo=tipo, contenuto=contenuto, mime_type=mime_type, filename=filename))
            messaggi.append(Messaggio(testo=testo, ruolo=ruolo, allegati=allegati, timestamp=timestamp, id=msg_id))
        conn.close()
        return messaggi

    @classmethod
    def cancella_chat(cls, provider: str, modello: str):
        cls._ensure_schema()
        conn = cls._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
        DELETE FROM Chat WHERE provider=? AND modello=?;
        """, (provider, modello))

        conn.commit()
        conn.close()

    @classmethod
    def cancella_tutto(cls):
        try:
            os.remove(cls.nome_db)
        except FileNotFoundError:
            pass

    @classmethod
    def esporta_json(cls) -> str:
        cls._ensure_schema()
        conn = cls._get_connection()
        cursor = conn.cursor()

        def fetch_all(table):
            cursor.execute(f"SELECT * FROM {table};")
            return [dict(row) for row in cursor.fetchall()]

        data = {
            "Provider": fetch_all("Provider"),
            "Modello": fetch_all("Modello"),
            "Messaggio": fetch_all("Messaggio"),
            "Chat": fetch_all("Chat"),
            "MessaggiInChat": fetch_all("MessaggiInChat"),
            "Allegato": fetch_all("Allegato")
        }

        conn.close()
        return json.dumps(data, indent=2)

    @classmethod
    def importa_json(cls, json_data: str):
        cls._ensure_schema()
        conn = cls._get_connection()
        cursor = conn.cursor()
        data = json.loads(json_data)

        for p in data.get("Provider", []):
            cursor.execute("INSERT OR IGNORE INTO Provider (id) VALUES (?);", (p["id"],))

        for m in data.get("Modello", []):
            cursor.execute("""
            INSERT OR IGNORE INTO Modello (id, provider)
            VALUES (?, ?);
            """, (m["id"], m["provider"]))

        for msg in data.get("Messaggio", []):
            cursor.execute("""
            INSERT OR IGNORE INTO Messaggio (id, ruolo, contenuto, timestamp)
            VALUES (?, ?, ?, ?);
            """, (msg["id"], msg["ruolo"], msg["contenuto"], msg["timestamp"]))

        for c in data.get("Chat", []):
            cursor.execute("""
            INSERT OR IGNORE INTO Chat (provider, modello, id)
            VALUES (?, ?, ?);
            """, (c["provider"], c["modello"], c["id"]))

        for mic in data.get("MessaggiInChat", []):
            cursor.execute("""
            INSERT OR IGNORE INTO MessaggiInChat (id_chat, messaggio_id, messaggio_timestamp)
            VALUES (?, ?, ?);
            """, (mic["id_chat"], mic["messaggio_id"], mic["messaggio_timestamp"]))

        for al in data.get("Allegato", []):
            cursor.execute("""
            INSERT OR IGNORE INTO Allegato
            (id, messaggio_id, tipo, mime_type, contenuto)
            VALUES (?, ?, ?, ?, ?);
            """, (al["id"], al["messaggio_id"], al["tipo"], al["mime_type"], al["contenuto"]))

        conn.commit()
        conn.close()
    
    @classmethod
    def ritorna_chat_recenti(cls):
        chat_rows=[]
        try:
            cls._ensure_schema()
            # carichiamo tuple (provider, modello) dal DB
            conn = cls._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT provider, modello
                FROM Chat
                ORDER BY provider, modello;
            """)
            chat_rows = cursor.fetchall()
            conn.close()
        except Exception as e:
            raise e
        else:
            return chat_rows


    @classmethod
    def _is_port_in_use(cls, host: str, port: int) -> bool:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except OSError:
            return False

    @classmethod
    def start_sqlite_web_server(cls, host: str = "127.0.0.1", port: int = 8080, no_browser: bool = True) -> bool:
        if cls._is_port_in_use(host, port):
            return True
        try:
            args = ["sqlite_web", cls.nome_db, "--host", host, "--port", str(port)]
            if no_browser:
                args.append("--no-browser")
            cls._sqlite_web_process = subprocess.Popen(args)
            return True
        except Exception:
            cls._sqlite_web_process = None
            return False

    @classmethod
    def is_sqlite_web_active(cls) -> bool:
        return cls._is_port_in_use(cls._sqlite_web_host, cls._sqlite_web_port)

    @classmethod
    def get_sqlite_web_url(cls) -> str:
        return f"http://{cls._sqlite_web_host}:{cls._sqlite_web_port}/"