import sqlite3
import os
import json
import subprocess
import socket
from typing import List
from src.Messaggio import Messaggio

class StoricoChat:
    nome_db: str = "storico_chat.db"

    # Stato interno del server sqlite-web
    _sqlite_web_process = None
    _sqlite_web_host = "127.0.0.1"
    _sqlite_web_port = 8080

    @classmethod
    def _get_connection(cls):
        """Crea e ritorna una nuova connessione SQLite locale."""
        conn = sqlite3.connect(cls.nome_db)
        conn.row_factory = sqlite3.Row
        return conn

    @classmethod
    def crea_db(cls, nome: str = ""):
        if nome:
            cls.nome_db = nome

        try:
            os.remove(cls.nome_db)
        except FileNotFoundError:
            pass

        # Crea solo il file / schema, poi chiude connessione
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
            id TEXT PRIMARY KEY,
            ruolo TEXT NOT NULL,
            contenuto TEXT NOT NULL
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
            FOREIGN KEY(id_chat) REFERENCES Chat(id) ON DELETE CASCADE,
            FOREIGN KEY(messaggio_id) REFERENCES Messaggio(id) ON DELETE CASCADE,
            PRIMARY KEY(id_chat, messaggio_id)
        );
        """)
        conn.commit()
        conn.close()

    @classmethod
    def salva_chat(cls, provider: str, modello: str, cronologia: List[Messaggio]):
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

            cursor.execute("""
            INSERT OR IGNORE INTO Messaggio (id, ruolo, contenuto)
            VALUES (?, ?, ?);
            """, (msg_id, ruolo, testo))

            cursor.execute("""
            INSERT OR IGNORE INTO MessaggiInChat (id_chat, messaggio_id)
            VALUES (?, ?);
            """, (chat_id, msg_id))

        conn.commit()
        conn.close()

    @classmethod
    def carica_cronologia(cls, provider: str, modello: str) -> List[Messaggio]:
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
        SELECT m.id, m.ruolo, m.contenuto
        FROM MessaggiInChat mic
        JOIN Messaggio m ON mic.messaggio_id = m.id
        WHERE mic.id_chat=?
        ORDER BY m.id;
        """, (chat_id,))

        messaggi = [
            Messaggio(testo=r["contenuto"], ruolo=r["ruolo"], id=r["id"])
            for r in cursor.fetchall()
        ]

        conn.close()
        return messaggi

    @classmethod
    def cancella_cronologia(cls, provider: str, modello: str):
        conn = cls._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
        DELETE FROM Chat WHERE provider=? AND modello=?;
        """, (provider, modello))
        conn.commit()

        cursor.execute("""
        DELETE FROM Messaggio
        WHERE id NOT IN (SELECT messaggio_id FROM MessaggiInChat);
        """)
        conn.commit()

        cursor.execute("""
        DELETE FROM Modello
        WHERE id NOT IN (SELECT modello FROM Chat);
        """)
        conn.commit()

        cursor.execute("""
        DELETE FROM Provider
        WHERE id NOT IN (SELECT provider FROM Chat);
        """)
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
        conn = cls._get_connection()
        cursor = conn.cursor()

        export_data = {}
        for table in ["Provider", "Modello", "Messaggio", "Chat", "MessaggiInChat"]:
            try:
                cursor.execute(f"SELECT * FROM {table};")
                rows = cursor.fetchall()
                # lista di dict per ogni tabella
                export_data[table] = [dict(row) for row in rows]
            except sqlite3.OperationalError:
                # se la tabella non esiste, la rappresentiamo con lista vuota
                export_data[table] = []

        conn.close()
        return json.dumps(export_data, indent=2)

    @classmethod
    def importa_json(cls, json_data: str):
        # Assicura schema (crea tabelle se non ci sono)
        conn = cls._get_connection()
        cursor = conn.cursor()

        # crea lo schema minimo senza eliminare tabelle esistenti
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
            id TEXT PRIMARY KEY,
            ruolo TEXT NOT NULL,
            contenuto TEXT NOT NULL
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
            FOREIGN KEY(id_chat) REFERENCES Chat(id) ON DELETE CASCADE,
            FOREIGN KEY(messaggio_id) REFERENCES Messaggio(id) ON DELETE CASCADE,
            PRIMARY KEY(id_chat, messaggio_id)
        );
        """)

        conn.commit()

        data = json.loads(json_data)

        for p in data.get("Provider", []):
            cursor.execute("INSERT OR IGNORE INTO Provider (id) VALUES (?);", (p["id"],))

        for m in data.get("Modello", []):
            cursor.execute("""
            INSERT OR IGNORE INTO Modello (id, provider) VALUES (?, ?);
            """, (m["id"], m["provider"]))

        for msg in data.get("Messaggio", []):
            cursor.execute("""
            INSERT OR IGNORE INTO Messaggio (id, ruolo, contenuto)
            VALUES (?, ?, ?);
            """, (msg["id"], msg["ruolo"], msg["contenuto"]))

        for c in data.get("Chat", []):
            cursor.execute("""
            INSERT OR IGNORE INTO Chat (provider, modello, id)
            VALUES (?, ?, ?);
            """, (c["provider"], c["modello"], c["id"]))

        for mic in data.get("MessaggiInChat", []):
            cursor.execute("""
            INSERT OR IGNORE INTO MessaggiInChat (id_chat, messaggio_id)
            VALUES (?, ?);
            """, (mic["id_chat"], mic["messaggio_id"]))

        conn.commit()
        conn.close()

    # ───────────────────────────────────────────────────────────────
    # sqlite-web (browser DB) support
    # ───────────────────────────────────────────────

    @classmethod
    def _is_port_in_use(cls, host: str, port: int) -> bool:
        """Verifica se la porta è già occupata."""
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except OSError:
            return False

    @classmethod
    def start_sqlite_web_server(cls, host: str = "127.0.0.1", port: int = 8080, no_browser: bool = True) -> bool:
        """
        Avvia il server sqlite-web per il DB.
        Ritorna True se il server è avviato o già attivo, False altrimenti.
        """
        cls._sqlite_web_host = host
        cls._sqlite_web_port = port

        # Se già raggiungibile sulla porta, consideralo attivo.
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
        """Ritorna True se il server è raggiungibile."""
        return cls._is_port_in_use(cls._sqlite_web_host, cls._sqlite_web_port)

    @classmethod
    def get_sqlite_web_url(cls) -> str:
        """Ritorna l’URL di accesso alla web UI."""
        return f"http://{cls._sqlite_web_host}:{cls._sqlite_web_port}/"

    @classmethod
    def _table_exists(cls, table_name: str) -> bool:
        conn = cls._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name=?;
        """, (table_name,))
        exists = cursor.fetchone() is not None
        conn.close()
        return exists
