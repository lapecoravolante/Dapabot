import sqlite3
import os
import json
from typing import List

class StoricoChat:
    nome_db: str = "storico_chat.db"
    conn: sqlite3.Connection = None
    cursor: sqlite3.Cursor = None

    @classmethod
    def crea_db(cls, nome: str = ""):
        if nome:
            cls.nome_db = nome

        # elimina eventuale DB precedente
        try:
            os.remove(cls.nome_db)
        except FileNotFoundError:
            pass

        cls.conn = sqlite3.connect(cls.nome_db)
        cls.conn.row_factory = sqlite3.Row
        cls.cursor = cls.conn.cursor()

        # provider e modello
        cls.cursor.execute("""
        CREATE TABLE IF NOT EXISTS Provider (
            id TEXT PRIMARY KEY
        );
        """)
        cls.cursor.execute("""
        CREATE TABLE IF NOT EXISTS Modello (
            id TEXT PRIMARY KEY,
            provider TEXT,
            FOREIGN KEY(provider) REFERENCES Provider(id)
        );
        """)

        # messaggi con timestamp come PK
        cls.cursor.execute("""
        CREATE TABLE IF NOT EXISTS Messaggio (
            timestamp TEXT PRIMARY KEY,
            tipo TEXT NOT NULL,
            contenuto TEXT NOT NULL
        );
        """)

        # chat con PK provider+modello e ID progressivo
        cls.cursor.execute("""
        CREATE TABLE IF NOT EXISTS Chat (
            provider TEXT NOT NULL,
            modello TEXT NOT NULL,
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            UNIQUE(provider, modello),
            FOREIGN KEY(provider) REFERENCES Provider(id),
            FOREIGN KEY(modello) REFERENCES Modello(id)
        );
        """)

        # relazione 1 chat -> N messaggi
        cls.cursor.execute("""
        CREATE TABLE IF NOT EXISTS MessaggiInChat (
            id_chat INTEGER,
            messaggio TEXT,
            FOREIGN KEY(id_chat) REFERENCES Chat(id),
            FOREIGN KEY(messaggio) REFERENCES Messaggio(timestamp),
            PRIMARY KEY(id_chat, messaggio)
        );
        """)

        cls.conn.commit()
        return cls.cursor

    @classmethod
    def salva_chat(cls, provider: str = "", modello: str = "", cronologia: List = []):
        """Salva tutta la cronologia di chat (provider, modello)."""
        if cls.cursor is None:
            cls.crea_db()

        # assicuro provider e modello
        cls.cursor.execute("INSERT OR IGNORE INTO Provider (id) VALUES (?);", (provider,))
        cls.cursor.execute("INSERT OR IGNORE INTO Modello (id, provider) VALUES (?, ?);", (modello, provider))

        # cancello eventuale chat esistente per ri-crearla
        cls.cursor.execute(
            "DELETE FROM MessaggiInChat WHERE id_chat IN (SELECT id FROM Chat WHERE provider=? AND modello=?);",
            (provider, modello)
        )
        cls.cursor.execute(
            "DELETE FROM Chat WHERE provider=? AND modello=?;",
            (provider, modello)
        )

        # inserisco nuova chat
        cls.cursor.execute(
            "INSERT INTO Chat (provider, modello) VALUES (?, ?);",
            (provider, modello)
        )
        cls.conn.commit()

        # recupero l'id della chat appena creata
        cls.cursor.execute(
            "SELECT id FROM Chat WHERE provider=? AND modello=?;",
            (provider, modello)
        )
        row = cls.cursor.fetchone()
        if not row:
            return
        chat_id = row["id"]

        # inserisco tutti i messaggi e la loro relazione con la chat
        for mess in cronologia:
            ts = mess.timestamp().isoformat()
            tipo = mess.get_ruolo()
            testo = mess.get_testo()

            # inserisco messaggio se non esiste
            cls.cursor.execute("""
            INSERT OR IGNORE INTO Messaggio (timestamp, tipo, contenuto)
            VALUES (?, ?, ?);
            """, (ts, tipo, testo))

            # relaziono messaggio con chat
            cls.cursor.execute("""
            INSERT OR IGNORE INTO MessaggiInChat (id_chat, messaggio)
            VALUES (?, ?);
            """, (chat_id, ts))

        cls.conn.commit()

    @classmethod
    def carica_cronologia(cls, provider: str = "", modello: str = "") -> List:
        """Carica cronologia di una determinata chat."""
        if cls.cursor is None:
            cls.crea_db()

        cls.cursor.execute("""
        SELECT c.id FROM Chat c
        WHERE provider=? AND modello=?;
        """, (provider, modello))
        row = cls.cursor.fetchone()
        if not row:
            return []

        chat_id = row["id"]

        cls.cursor.execute("""
        SELECT m.timestamp, m.tipo, m.contenuto
        FROM MessaggiInChat mic
        JOIN Messaggio m ON mic.messaggio = m.timestamp
        WHERE mic.id_chat=?
        ORDER BY m.timestamp;
        """, (chat_id,))

        messaggi = []
        from src.Messaggio import Messaggio

        for r in cls.cursor.fetchall():
            msg = Messaggio(testo=r["contenuto"], ruolo=r["tipo"], timestamp=r["timestamp"])
            messaggi.append(msg)

        return messaggi

    @classmethod
    def cancella_cronologia(cls, provider: str = "", modello: str = ""):
        """Cancella cronologia di una specifica chat."""
        if cls.cursor is None:
            cls.crea_db()

        cls.cursor.execute("""
        SELECT id FROM Chat WHERE provider=? AND modello=?;
        """, (provider, modello))
        row = cls.cursor.fetchone()
        if not row:
            return

        chat_id = row["id"]

        # rimuovo tutti i messaggi associati
        cls.cursor.execute("DELETE FROM MessaggiInChat WHERE id_chat=?;", (chat_id,))

        # rimuovo la chat
        cls.cursor.execute("""
        DELETE FROM Chat WHERE provider=? AND modello=?;
        """, (provider, modello))

        cls.conn.commit()

    @classmethod
    def cancella_tutto(cls):
        """Elimina completamente il DB dal disco."""
        if cls.conn:
            cls.conn.close()
        try:
            os.remove(cls.nome_db)
        except FileNotFoundError:
            pass
        cls.conn = None
        cls.cursor = None

    @classmethod
    def esporta_json(cls) -> str:
        if cls.cursor is None:
            cls.crea_db()

        def fetch_all(table):
            cls.cursor.execute(f"SELECT * FROM {table};")
            return [dict(row) for row in cls.cursor.fetchall()]

        export_data = {
            "Provider": fetch_all("Provider"),
            "Modello": fetch_all("Modello"),
            "Messaggio": fetch_all("Messaggio"),
            "Chat": fetch_all("Chat"),
            "MessaggiInChat": fetch_all("MessaggiInChat")
        }
        return json.dumps(export_data, indent=2)

    @classmethod
    def importa_json(cls, json_data: str):
        if cls.cursor is None:
            cls.crea_db()

        data = json.loads(json_data)

        for p in data.get("Provider", []):
            cls.cursor.execute("INSERT OR IGNORE INTO Provider (id) VALUES (?);", (p["id"],))

        for m in data.get("Modello", []):
            cls.cursor.execute(
                "INSERT OR IGNORE INTO Modello (id, provider) VALUES (?, ?);",
                (m["id"], m["provider"])
            )

        for m in data.get("Messaggio", []):
            cls.cursor.execute("""
            INSERT OR IGNORE INTO Messaggio (timestamp, tipo, contenuto)
            VALUES (?, ?, ?);
            """, (m["timestamp"], m["tipo"], m["contenuto"]))

        for c in data.get("Chat", []):
            cls.cursor.execute("""
            INSERT OR IGNORE INTO Chat (provider, modello, id)
            VALUES (?, ?, ?);
            """, (c["provider"], c["modello"], c["id"]))

        for mic in data.get("MessaggiInChat", []):
            cls.cursor.execute("""
            INSERT OR IGNORE INTO MessaggiInChat (id_chat, messaggio)
            VALUES (?, ?);
            """, (mic["id_chat"], mic["messaggio"]))

        cls.conn.commit()
