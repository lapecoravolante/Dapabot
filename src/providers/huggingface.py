from src.providers.base import Provider
from langchain_openai import ChatOpenAI
from huggingface_hub import list_models
from langchain_huggingface import HuggingFaceEmbeddings
import requests, logging

class HuggingfaceProvider(Provider):
       
    def __init__(self, nome="Huggingface", prefisso_token="hf_", base_url="https://router.huggingface.co/v1"):
        super().__init__(nome=nome, prefisso_token=prefisso_token, base_url=base_url)
        # Silenzia i log di sentence-transformers
        logging.getLogger("sentence_transformers").setLevel(logging.ERROR)
        logging.getLogger("sentence_transformers.SentenceTransformer").setLevel(logging.ERROR)
            
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
    
    def lista_modelli_rag(self):
        """Ritorna solo i modelli di tipo 'text-generation' disponibili su Hugging Face."""
        if self._modelli_rag:  # caching alla vecchia maniera
            return self._modelli_rag
        try:
            modelli = list_models(filter="sentence-transformers")                
            self._modelli_rag=[m.modelId for m in modelli]
        except Exception as errore:
            print(f"Errore nel caricamento dei modelli da Hugging Face: {errore}")
            self._modelli_rag=[]
        finally:
            return self._modelli_rag

    def _crea_client(self, base_url, modello, api_key):
        return ChatOpenAI(model=modello, api_key=api_key, base_url=base_url)

    def rag(self):
        if self._rag.get_modello():
            self._rag.set_motore_di_embedding(HuggingFaceEmbeddings(model_name=self._rag.get_modello()))
            # per hugging face i tokenizer hanno lo stesso nome del modello di embedding
            self._rag.set_tokenizer(self._rag.get_modello())
        return self._rag.run()