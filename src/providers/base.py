from abc import ABC, abstractmethod
from langchain_core.prompts import ChatPromptTemplate
from langchain.messages import HumanMessage, SystemMessage, AIMessage
from src.Messaggio import Messaggio
from src.Allegato import Allegato
from src.Configurazione import Configurazione
from src.providers.rag import Rag
import base64, validators

class Provider(ABC):
      
    def __init__(self, nome, base_url, prefisso_token=""):
        self._nome=nome
        self._prefisso_token=prefisso_token
        self.set_baseurl(base_url)
        self._modelli=set()
        self._modelli_rag=set()
        self._api_key=prefisso_token
        self._client=None
        self._cronologia_messaggi = {} # dizionario che associa un modello alla sua cronologia dei messaggi
        self._modello_scelto = ""
        self._motore_di_embedding=None
        self.set_disponibile(False) # mi dice se il provider è raggiungibile via rete o temporaneamente irragiungibile
        self._rag : Rag = Rag()
        # carico l'eventuale configurazione da file su disco 
        configurazione = Configurazione.carica().get(Configurazione.PROVIDERS_KEY, {})
        for p in configurazione:
            if p["nome"]== nome:
                self.set_baseurl(p["base_url"])
                self._api_key=p["api_key"]
                self._modello_scelto=p["modello"]
                if self._modello_scelto is not None: 
                    self._cronologia_messaggi[self._modello_scelto]=[]
                self.set_rag(attivo=p[Configurazione.RAG_KEY]["attivo"], 
                             topk=p[Configurazione.RAG_KEY]["top_k"],
                             modello=p[Configurazione.RAG_KEY]["modello"],
                             upload_dir=p[Configurazione.RAG_KEY]["directory_allegati"],
                             modalita_ricerca=p[Configurazione.RAG_KEY]["modalita_ricerca"])

    def to_dict(self):
        return {
            "nome": self._nome,
            "base_url": self._base_url,            
            "api_key": self._api_key,
            "modello": self._modello_scelto,
            Configurazione.RAG_KEY:{
                "attivo": self._rag.get_attivo(),
                "modello": self._rag.get_modello(),
                "top_k": self._rag.get_topk(),
                "directory_allegati": self._rag.get_upload_dir(),
                "modalita_ricerca": self._rag.get_modalita_ricerca()
            }
        }
        
    def get_prefisso_token(self):
        return self._prefisso_token
    
    def set_modello_scelto(self, modello):
        if modello:
            self._modello_scelto=modello
            if modello not in self._cronologia_messaggi:
                self._cronologia_messaggi[modello]=[]
        
    def set_baseurl(self, base_url):
        if (validators.url(base_url)):
            self._base_url=base_url
        else:
            raise ValueError(f"Url non valida: {base_url}")
    
    def get_baseurl(self):
        return self._base_url
    
    # Abilita o disabilita l'uso del RAG
    def set_rag(self, attivo: bool = False, topk: int = 3, modello: str = "", upload_dir="uploads/", modalita_ricerca=Rag.AVAILABLE_SEARCH_MODALITIES[0]):
        self._rag.set_attivo(attivo)
        self._rag.set_topk(topk)
        self._rag.set_modello(modello)
        self._rag.set_upload_dir(upload_dir)
        self._rag.set_modalita_ricerca(modalita_ricerca)
        
    def get_rag(self):
        return self._rag
        
    def set_apikey(self, api_key: str):
        if api_key is not None and api_key.startswith(self._prefisso_token):
            self._api_key=api_key
        else:
            raise Exception(f"L'API KEY inserita non inizia con \"{self._prefisso_token}\"")
       
    def set_disponibile(self, disponibile):
        self._disponibile=disponibile
    
    def disponibile(self):
        return self._disponibile
    
    def nome(self):
        return self._nome
    
    def prefisso_token(self):
        return self._prefisso_token

    def get_apikey(self):
        return self._api_key
               
    def get_modello_scelto(self):
        return self._modello_scelto
    
    def set_client(self, modello, api_key):
        # se non sono cambiati né il modello né l'apikey, ritorno il modello attualmente in uso
        if self._modello_scelto == modello and self._api_key == api_key and self._client:
            return self._client
        try:
            self.set_apikey(api_key=api_key)
            self._client=self._crea_client(base_url=self._base_url, modello=modello, api_key=api_key)
            self._modello_scelto = modello
            if modello not in self._cronologia_messaggi:
                self._cronologia_messaggi[modello]=[]
            self.set_disponibile(True)
        except Exception as errore:
            self.set_disponibile(False)
            self._client=None
            raise Exception(errore)
    
    def invia_messaggi(self, messaggi: list[Messaggio]):
        """Invia i messaggi al modello multimodale e aggiorna la cronologia."""
        if not self._modello_scelto:
            raise Exception("Client non inizializzato. Inserisci un'API KEY valida e scegli un modello.")
        cronologia_modello = self._cronologia_messaggi[self._modello_scelto]
        messaggi_da_inviare = []  
        preambolo_rag=" \nRispondi dando priorità al contesto fornito di seguito: \n"
        try:
            for m in messaggi:
                blocchi=[]
                match m.get_ruolo():
                    case "system":
                        messaggi_da_inviare.append(SystemMessage(content=m.get_testo()))
                    case "user":
                        blocchi=[{"type": "text", "text": m.get_testo()}]
                        if self._rag.get_attivo(): # sostituisco i file allegati con il testo tornato dal VectorDB
                            self._rag.set_prompt(m)
                            allegati_rag: list[Allegato] = self.rag()
                            contenuti_rag="\n---\n".join(allegato.contenuto for allegato in allegati_rag)
                            blocchi.append({"type": "text", "text": preambolo_rag})
                            blocchi.append({"type": "text", "text": contenuti_rag})
                        else: # se non devo fare il rag, allego i file in codifica base64
                            for f in m.get_allegati():
                                b64 = base64.b64encode(f.getvalue()).decode("utf-8")
                                tipo = f.type.split("/")[0]
                                if tipo in ("image", "video", "audio"):
                                    blocchi.append({"type": tipo, "mime_type": f.type, "base64": b64})
                                elif f.type=="text/plain":
                                    blocchi.append({"type": "text-plain", "mime_type": f.type, "text": str(f.getvalue())})
                                else:
                                    blocchi.append({"type": "file", "mime_type": f.type, "base64": b64, "filename": f.name})
                        messaggi_da_inviare.append(HumanMessage(content_blocks=blocchi))
                    case _:
                        pass
            # Crea il prompt template
            prompt = ChatPromptTemplate.from_messages([
                *cronologia_modello,        # cronologia precedente
                *messaggi_da_inviare,       # nuovi messaggi
            ])
            # Crea la catena e invoca il modello
            base_chain = prompt | self._client
            risposta = base_chain.invoke({})
            # Aggiungo il messaggio utente alla cronologia
            cronologia_modello.extend(messaggi_da_inviare)
            # Aggiungo la risposta del modello alla cronologia
            testo_risposta = getattr(risposta, "content", risposta)
            allegati_risposta = getattr(risposta, "content_blocks", [])
            cronologia_modello.append(AIMessage(content=testo_risposta, content_blocks=allegati_risposta))
        except Exception as errore:
            raise Exception(f"Errore nell'invio del messaggio: {errore}")
            
    def get_cronologia_messaggi(self): 
        cronologia_da_ritornare: list[Messaggio] = list()
        for m in self._cronologia_messaggi[self._modello_scelto]:
            ruolo=m.type
            testo=""
            allegati: list[Allegato]=list()
            for blocco in m.content_blocks:
                tipo = blocco["type"]
                # aggiunge i blocchi di tipo testo al testo principale del messaggio
                if tipo == "text": 
                    testo += blocco["text"] + "\n"
                # Tutti gli altri tipi diventano Allegato
                else: 
                    contenuto = base64.b64decode(blocco["base64"]) if "base64" in blocco else blocco.get("text", "")
                    mime_type = blocco.get("mime_type", tipo)
                    allegati.append(Allegato(tipo=tipo, contenuto=contenuto, mime_type=mime_type))    
            cronologia_da_ritornare.append(Messaggio(testo=testo, ruolo=ruolo, allegati=allegati))
        return cronologia_da_ritornare
        
    @abstractmethod
    def lista_modelli_rag(self):
        pass
    
    @abstractmethod
    def lista_modelli(self, api_key=""):
        pass

    @abstractmethod
    def rag(self):
        pass
    
    # funzione di utilità che torna il client specifico per il provider scelto
    @abstractmethod
    def _crea_client(self, base_url="", modello="", api_key=""):
        pass