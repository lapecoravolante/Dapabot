import json, os

class Configurazione():
    PROVIDERS_KEY="providers"
    RAG_KEY="rag"
    FILENAME="config.json"
    CONFIG={}

    # imposta una chiave di configurazione e salva subito su disco
    @classmethod
    def set(cls, chiave, valore):
        cls.CONFIG[chiave] = valore
        cls._salva_su_file()

    @classmethod
    def _salva_su_file(cls):
        try:
            with open(cls.FILENAME, "w", encoding="utf-8") as f:
                json.dump(cls.CONFIG, f, indent=4, ensure_ascii=False)
        except Exception as e:
            raise RuntimeError(f"Errore in fase di salvataggio della configurazione: {e}")

    @classmethod
    def carica(cls):
        try:
            with open(cls.FILENAME, "r", encoding="utf-8") as f:
                cls.CONFIG = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Configurazione non valida: {e}")
        except Exception as e:
            raise ValueError(f"Errore di accesso al file {cls.FILENAME}: {e}")
        finally:
            return cls.CONFIG

