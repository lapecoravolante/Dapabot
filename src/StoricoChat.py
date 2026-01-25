import sqlite3
import os
import json
from typing import List
from src.Messaggio import Messaggio

class StoricoChat:
    nome_db: str = "storico_chat.db"
    conn: sqlite3.Connection = None
    cursor: sqlite3.Cursor = None

    @classmethod
    def crea_db(cls, nome: str = ""):
        if nome:
            cls.nome_db = nome

        try:
            os.remove(cls.nome_db)
        except FileNotFoundError:
            pass

        cls.conn = sqlite3.connect(cls.nome_db)
        cls.conn.row_factory = sqlite3.Row
        cls.cursor = cls.conn.cursor()

        # Attiva enforcement delle foreign key
        cls.cursor.execute("PRAGMA foreign_keys = ON;")

        cls.cursor.execute("""
        CREATE TABLE IF NOT EXISTS Provider (
            id TEXT PRIMARY KEY
        );
        """)
        cls.cursor.execute("""
        CREATE TABLE IF NOT EXISTS Modello (
            id TEXT PRIMARY KEY,
            provider TEXT,
            FOREIGN KEY(provider) REFERENCES Provider(id) ON DELETE CASCADE
        );
        """)
        cls.cursor.execute("""
        CREATE TABLE IF NOT EXISTS Messaggio (
            id TEXT PRIMARY KEY,
            ruolo TEXT NOT NULL,
            contenuto TEXT NOT NULL
        );
        """)
        cls.cursor.execute("""
        CREATE TABLE IF NOT EXISTS Chat (
            provider TEXT NOT NULL,
            modello TEXT NOT NULL,
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            UNIQUE(provider, modello),
            FOREIGN KEY(provider) REFERENCES Provider(id) ON DELETE CASCADE,
            FOREIGN KEY(modello) REFERENCES Modello(id) ON DELETE CASCADE
        );
        """)
        cls.cursor.execute("""
        CREATE TABLE IF NOT EXISTS MessaggiInChat (
            id_chat INTEGER,
            messaggio_id TEXT,
            FOREIGN KEY(id_chat) REFERENCES Chat(id) ON DELETE CASCADE,
            FOREIGN KEY(messaggio_id) REFERENCES Messaggio(id) ON DELETE CASCADE,
            PRIMARY KEY(id_chat, messaggio_id)
        );
        """)

        cls.conn.commit()
        return cls.cursor

    @classmethod
    def salva_chat(cls, provider: str = "", modello: str = "", cronologia: List[Messaggio] = []):
        if cls.cursor is None:
            cls.crea_db()

        cls.cursor.execute("INSERT OR IGNORE INTO Provider (id) VALUES (?);", (provider,))
        cls.cursor.execute(
            "INSERT OR IGNORE INTO Modello (id, provider) VALUES (?, ?);",
            (modello, provider)
        )

        cls.cursor.execute(
            "SELECT id FROM Chat WHERE provider=? AND modello=?;",
            (provider, modello)
        )
        row = cls.cursor.fetchone()

        if row:
            chat_id = row["id"]
            cls.cursor.execute("DELETE FROM MessaggiInChat WHERE id_chat=?;", (chat_id,))
        else:
            cls.cursor.execute(
                "INSERT INTO Chat (provider, modello) VALUES (?, ?);",
                (provider, modello)
            )
            cls.conn.commit()
            cls.cursor.execute(
                "SELECT id FROM Chat WHERE provider=? AND modello=?;",
                (provider, modello)
            )
            chat_id = cls.cursor.fetchone()["id"]

        for mess in cronologia:
            msg_id = mess.get_id()
            ruolo = mess.get_ruolo()
            testo = mess.get_testo()

            cls.cursor.execute("""
            INSERT OR IGNORE INTO Messaggio (id, ruolo, contenuto)
            VALUES (?, ?, ?);
            """, (msg_id, ruolo, testo))

            cls.cursor.execute("""
            INSERT OR IGNORE INTO MessaggiInChat (id_chat, messaggio_id)
            VALUES (?, ?);
            """, (chat_id, msg_id))

        cls.conn.commit()

    @classmethod
    def cancella_cronologia(cls, provider: str = "", modello: str = ""):
        if cls.cursor is None:
            cls.crea_db()

        # elimina la chat
        cls.cursor.execute("""
            DELETE FROM Chat WHERE provider=? AND modello=?;
        """, (provider, modello))
        cls.conn.commit()

        # elimina messaggi “orfani”
        cls.cursor.execute("""
            DELETE FROM Messaggio
            WHERE id NOT IN (
                SELECT messaggio_id FROM MessaggiInChat
            );
        """)
        cls.conn.commit()

        # elimina eventuali modelli orfani
        cls.cursor.execute("""
            DELETE FROM Modello
            WHERE id NOT IN (SELECT modello FROM Chat);
        """)
        cls.conn.commit()

        # elimina eventuali provider orfani
        cls.cursor.execute("""
            DELETE FROM Provider
            WHERE id NOT IN (SELECT provider FROM Chat);
        """)
        cls.conn.commit()

    @classmethod
    def carica_cronologia(cls, provider: str = "", modello: str = "") -> List[Messaggio]:
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
        SELECT m.id, m.ruolo, m.contenuto
        FROM MessaggiInChat mic
        JOIN Messaggio m ON mic.messaggio_id = m.id
        WHERE mic.id_chat=?
        ORDER BY m.id;
        """, (chat_id,))

        messaggi = []
        for r in cls.cursor.fetchall():
            msg = Messaggio(
                testo=r["contenuto"],
                ruolo=r["ruolo"],
                id=r["id"]
            )
            messaggi.append(msg)
        return messaggi

    @classmethod
    def cancella_tutto(cls):
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
        """Esporta l’intero DB in formato JSON."""
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
            cls.cursor.execute("""
            INSERT OR IGNORE INTO Modello (id, provider) VALUES (?, ?);
            """, (m["id"], m["provider"]))

        for msg in data.get("Messaggio", []):
            cls.cursor.execute("""
            INSERT OR IGNORE INTO Messaggio (id, ruolo, contenuto)
            VALUES (?, ?, ?);
            """, (msg["id"], msg["ruolo"], msg["contenuto"]))

        for c in data.get("Chat", []):
            cls.cursor.execute("""
            INSERT OR IGNORE INTO Chat (provider, modello, id)
            VALUES (?, ?, ?);
            """, (c["provider"], c["modello"], c["id"]))

        for mic in data.get("MessaggiInChat", []):
            cls.cursor.execute("""
            INSERT OR IGNORE INTO MessaggiInChat (id_chat, messaggio_id)
            VALUES (?, ?);
            """, (mic["id_chat"], mic["messaggio_id"]))

        cls.conn.commit()