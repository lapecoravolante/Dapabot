import json, os

class Configurazione:
    # Applico il singleton per non duplicare le configurazioni in giro per l'applicazione
    _istanza = None
    _inizializzata = False
    PROVIDERS_KEY="providers"
    RAG_KEY="rag"
    FILENAME="config.json"

    def __new__(cls, *args, **kwargs):
        if cls._istanza is None:
            cls._istanza = super().__new__(cls)
        return cls._istanza

    def __init__(self, filename=""):
        # Evita di rieseguire l'inizializzazione
        if self.__class__._inizializzata:
            return
        
        self._filename=Configurazione.FILENAME
        if filename:
            self._filename = filename
            
        self._config = {}
        if not os.path.exists(self._filename):
            self._config = {
                Configurazione.PROVIDERS_KEY: [
                    {
                        "nome": "HuggingFace",
                        "base_url": "https://router.huggingface.co/v1",
                        "api_key": "hf_",
                        "modello": "",
                        Configurazione.RAG_KEY: {
                            "attivo": False,
                            "modello": "sentence-transformers/all-MiniLM-L6-v2",
                            "directory_allegati": "uploads/",
                            "top_k": 3,
                            "modalita_ricerca": "similarity"
                        }
                    },
                    {
                        "nome": "OpenRouter",
                        "base_url": "https://openrouter.ai/api/v1",
                        "api_key": "sk-",
                        "modello": "",
                        Configurazione.RAG_KEY: {
                            "attivo": False,
                            "modello": "",
                            "directory_allegati": "uploads/",
                            "top_k": 3,
                            "modalita_ricerca": "similarity"
                        }
                    }
                ]
            }
            self._salva_su_file()
        else:
            try:
                with open(self._filename, "r", encoding="utf-8") as f:
                    self._config = json.load(f)
            except json.JSONDecodeError as e:
                raise ValueError(f"Configurazione non valida: {e}")
            except Exception as e:
                raise ValueError(f"Errore di accesso al file {self._filename}: {e}")
        self.__class__._inizializzata = True

    def get(self, chiave):
        return self._config.get(chiave)
    
    def set(self, chiave, valore):
        self._config[chiave] = valore
        self._salva_su_file()

    def get_all(self):
        return dict(self._config)

    def _salva_su_file(self):
        try:
            with open(self._filename, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            raise RuntimeError(
                f"Errore in fase di salvataggio della configurazione: {e}"
            )




