from src.providers.base import Provider
from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings
import requests

class OpenRouterProvider(Provider):
    
    def __init__(self, nome="OpenRouter", prefisso_token="sk-", base_url="https://openrouter.ai/api/v1"):
        super().__init__(nome=nome, prefisso_token=prefisso_token, base_url=base_url)

    def _query(self, url):
        try:
            modelli=[]
            url=self._base_url+f"/{url}"
            json_list = requests.get(url).json().get("data", [])
            for modello in json_list:
                pricing = modello.get("pricing", {})
                prompt_cost = pricing.get("prompt", None)
                completion_cost = pricing.get("completion", None)
                if prompt_cost == "0" and completion_cost == "0":
                    modelli.append(modello["id"])
            return modelli
        except:
            return []
    
    def lista_modelli(self, api_key=""):
        if self._modelli:  # caching
            return self._modelli
        self._modelli=self._query(url="models")
        return self._modelli
    
    def lista_modelli_rag(self):
        if self._modelli_rag: # caching
            return self._modelli_rag
        self._modelli_rag=self._query(url="embeddings/models")
        return self._modelli_rag
        
    def _crea_client(self, base_url, modello, api_key):
        return ChatOpenAI(model=modello, api_key=api_key, base_url=base_url)

    def rag(self):
        if self._rag.get_modello():
            self._rag.set_motore_di_embedding(
                OpenAIEmbeddings(model=self._rag.get_modello(), 
                                base_url=self._base_url, 
                                api_key=self._api_key))
            # per openrouter si usa il tokenizer di default: gpt2
            self._rag.set_tokenizer(tokenizer="gpt2", max_tokens=1000, overlap=150)
        return self._rag.run()