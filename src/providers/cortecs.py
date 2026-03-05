from src.providers.base import Provider
from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings
import requests, re
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

class CortecsProvider(Provider):
    
    def __init__(self, nome="Cortecs", prefisso_token="eyJ", base_url="https://api.cortecs.ai/v1"):
        super().__init__(nome=nome, prefisso_token=prefisso_token, base_url=base_url)

    def _query(self, url):
        try:
            modelli=[]
            url=self._base_url+f"/{url}"
            response=requests.get(url, timeout=10)
            response.raise_for_status()
            json_list = response.json().get("data", [])
            for modello in json_list:
                pricing = modello.get("pricing", {})
                input_token = pricing.get("input_token", None)
                output_token = pricing.get("output_token", None)
                # I prezzi sono numeri (int/float), non stringhe
                if input_token == 0 and output_token == 0:
                    modelli.append(modello["id"])
            self.set_disponibile(True)
        except Exception as e:
            self.set_disponibile(False)
            modelli = []
        finally:
            return modelli
    
    def lista_modelli(self, api_key=""):
        if self._modelli:  # caching
            return self._modelli
        self._modelli=self._query(url="models")
        return self._modelli
    
    def lista_modelli_rag(self):
        """
        Estrae la lista dei modelli di embedding dalla pagina web di Cortecs.ai
        usando Playwright per gestire il contenuto JavaScript dinamico.
        """
        if self._modelli_rag: # caching
            return self._modelli_rag

        try:
            modelli = []
            url = "https://cortecs.ai/serverlessModels?tags=Embedding"
            
            # Usa Playwright per caricare la pagina con JavaScript
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                # Naviga alla pagina e aspetta che il contenuto sia caricato
                page.goto(url, wait_until="networkidle")
                
                # Aspetta che i link dei modelli siano visibili
                page.wait_for_selector('a[href^="/detailedServerlessView/"]', timeout=10000)
                
                # Ottieni l'HTML renderizzato
                html_content = page.content()
                browser.close()
            
            # Parsing HTML con BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Trova tutti i link che puntano a /detailedServerlessView/
            links = soup.find_all('a', href=re.compile(r'^/detailedServerlessView/'))
            
            # Estrai i nomi dei modelli dai link
            for link in links:
                href = link.get('href')
                # Verifica che href sia una stringa
                if href and isinstance(href, str):
                    # Estrai il nome del modello dall'URL
                    match = re.search(r'/detailedServerlessView/(.+)$', href)
                    if match:
                        nome_modello = match.group(1)
                        modelli.append(nome_modello)
            
            # Rimuovi duplicati mantenendo l'ordine
            modelli = list(dict.fromkeys(modelli))
            
            self._modelli_rag = modelli
        except Exception as e:
            self._modelli_rag = []
        
        return self._modelli_rag
        
    def _crea_client(self, base_url, modello, api_key):
        return ChatOpenAI(model=modello, api_key=api_key, base_url=base_url)

    def rag(self):
        """
        Configura e esegue il RAG per OpenRouter.
        Usa il metodo centralizzato _esegui_rag_con_feedback() per il feedback visivo.
        """
        if self._rag.get_modello():
            self._rag.set_motore_di_embedding(
                OpenAIEmbeddings(model=self._rag.get_modello(),
                                base_url=self._base_url,
                                api_key=self._api_key))
            # per openrouter si usa il tokenizer di default: gpt2
            self._rag.set_tokenizer(tokenizer="gpt2", max_tokens=1000, overlap=150)
        
        return self._esegui_rag_con_feedback()