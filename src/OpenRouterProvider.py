from Provider import Provider
from langchain_openai import ChatOpenAI
import requests

class OpenRouterProvider(Provider):
    
#    _instance = None
    
#    def __new__(cls): # faccio il Singleton
#        if cls._instance is None:
#            cls._instance = super(OpenRouterProvider, cls).__new__(cls)
#        return cls._instance
    
    def __init__(self, nome="OpenRouter", prefisso_token="sk-", base_url="https://openrouter.ai/api/v1"):
        super().__init__(nome=nome, prefisso_token=prefisso_token, base_url=base_url)
        
    def lista_modelli(self, api_key=""):
        if self._modelli:  # caching
            return self._modelli
        try:
            json_list = requests.get(f"{self._base_url}/models").json().get("data", [])
            for modello in json_list:
                pricing = modello.get("pricing", {})
                prompt_cost = pricing.get("prompt", None)
                completion_cost = pricing.get("completion", None)
                if prompt_cost == "0" and completion_cost == "0":
                    self._modelli.add(modello["id"])
            return self._modelli
        except:
            return []
    
    def _crea_client(_self, base_url, modello, api_key):
        return ChatOpenAI(model=modello, api_key=api_key, base_url=base_url)