from src.providers.base import Provider
from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings
import requests
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re
import subprocess
import sys

class VeniceProvider(Provider):
    
    def __init__(self, nome="Venice", prefisso_token="VENICE_", base_url="https://api.venice.ai/api/v1"):
        super().__init__(nome=nome, prefisso_token=prefisso_token, base_url=base_url)

    def _ensure_chromium_installed(self):
        """
        Verifica se Chromium è installato per Playwright e lo installa automaticamente se necessario.
        Questo metodo viene chiamato prima di usare Playwright per evitare errori.
        """
        try:
            # Prova a lanciare chromium per verificare se è installato
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                browser.close()
        except Exception:
            # Chromium non è installato, installalo automaticamente
            try:
                print("Installazione di Chromium per Playwright in corso...")
                subprocess.run(
                    [sys.executable, "-m", "playwright", "install", "chromium"],
                    check=True,
                    capture_output=True
                )
                print("Chromium installato con successo!")
            except subprocess.CalledProcessError as e:
                print(f"Errore durante l'installazione di Chromium: {e}")
                raise

    def _query(self, url):
        try:
            modelli=[]
            url=self._base_url+f"/{url}"
            response=requests.get(url, timeout=10)
            response.raise_for_status()
            json_list = response.json().get("data", [])
            # Venice ha solo modelli a pagamento, quindi li inserisco tutti 
            # senza necessità di filtrare quelli gratuiti
            modelli = [modello["id"] for modello in json_list]
            self.set_disponibile(True)
        except:
            self.set_disponibile(False)
            modelli.clear()
        finally:
            return modelli
    
    def lista_modelli(self, api_key=""):
        if self._modelli:  # caching
            return self._modelli
        self._modelli=self._query(url="models")
        return self._modelli
    
    def lista_modelli_rag(self):
        """
        Estrae la lista dei modelli di embedding dalla pagina web di Venice.ai
        usando Playwright per gestire il contenuto JavaScript dinamico.
        """
        if self._modelli_rag: # caching
            return self._modelli_rag
        
        try:
            # Assicurati che Chromium sia installato
            self._ensure_chromium_installed()
            
            modelli = []
            url = "https://docs.venice.ai/models/embeddings"
            
            # Usa Playwright per caricare la pagina con JavaScript
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                # Naviga alla pagina e aspetta che il contenuto sia caricato
                page.goto(url, wait_until="networkidle")
                
                # Ottieni l'HTML renderizzato
                html_content = page.content()
                browser.close()
            
            # Parsing HTML con BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Cerca tutti gli span con classe 'vmb-model-id' che contengono i nomi dei modelli
            model_spans = soup.find_all('span', class_='vmb-model-id')
            
            # Estrai i nomi dei modelli
            for span in model_spans:
                text = span.get_text(strip=True)
                if text:  # Verifica che non sia vuoto
                    modelli.append(text)
            
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