from Provider import Provider
from langchain_openai import ChatOpenAI
import requests

class HuggingfaceProvider(Provider):
       
    def __init__(self, nome="Huggingface", prefisso_token="hf_", base_url="https://router.huggingface.co/v1"):
        super().__init__(nome=nome, prefisso_token=prefisso_token, base_url=base_url)
    
    def lista_modelli(self, api_key=""):
        """Ritorna solo i modelli di tipo 'text-generation' disponibili su Hugging Face."""
        if self._modelli:  # caching alla vecchia maniera
            return self._modelli
        try:
            response = requests.get(f"{self._base_url}/models", timeout=10)
            response.raise_for_status()
            self._modelli.update([
                modello["id"]
                for modello in response.json().get("data", [])                
            ])
            return self._modelli
        except Exception as errore:
            print(f"Errore nel caricamento dei modelli da Hugging Face: {errore}")
            return []

    def _crea_client(_self, base_url, modello, api_key):
        return ChatOpenAI(model=modello, api_key=api_key, base_url=base_url)
