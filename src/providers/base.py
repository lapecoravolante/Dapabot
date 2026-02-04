from abc import ABC, abstractmethod
from langchain_core.prompts import ChatPromptTemplate
from langchain.messages import HumanMessage, SystemMessage, AIMessage
from langchain.agents import create_agent
from langchain_core.prompts import PromptTemplate
from typing import List, Tuple
from datetime import datetime
from src.Messaggio import Messaggio
from src.Allegato import Allegato
from src.Configurazione import Configurazione
from src.providers.rag import Rag
from src.StoricoChat import StoricoChat
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
        self._modalita_agentica = False # indica se la modalità agentica è attivata o no
        self._agent = None   # l'agent
        self._tools = []  # i tools per l'agent
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
                    # lista di tuple in cui il primo elemento è un messaggio in formato Langchain e il secondo è la corrispondente istanza di Messaggio
                    self._cronologia_messaggi[self._modello_scelto]=None 
                self.set_rag(attivo=p[Configurazione.RAG_KEY]["attivo"], 
                             topk=p[Configurazione.RAG_KEY]["top_k"],
                             modello=p[Configurazione.RAG_KEY]["modello"],
                             upload_dir=p[Configurazione.RAG_KEY]["directory_allegati"],
                             modalita_ricerca=p[Configurazione.RAG_KEY]["modalita_ricerca"])

    """
        Ritorna una lista di tuple (m0, m1) in cui m0 è un messaggio in formato Langchain (quindi un'istanza 
        di HumanMessage, AIMessage,...) mentre m1 è un'istanza della classe Messaggio, usata per mostrare 
        il contenuto sulla GUI e per i salvataggi sul DB
    """
    def _carica_cronologia_da_disco(self, modello) -> List[Tuple]:
        # ricostruisco la cronologia prendendo i messaggi dal disco e ricostruendo l'equivalente messaggio in formato Langchain
        messaggi_su_disco=StoricoChat.carica_cronologia(self._nome, modello)
        tuple_da_ritornare=[]
        for m in messaggi_su_disco:            
            match m.get_ruolo():
                case "system":
                    tuple_da_ritornare.append((SystemMessage(content=m.get_testo()), m))
                case "user"|"ai"|"assistant":
                    blocchi=[{"type": "text", "text": m.get_testo()}]
                    for allegato in m.get_allegati():
                        contenuto = allegato.contenuto
                        tipo      = allegato.tipo
                        mime_type = allegato.mime_type
                        filename  = allegato.filename                        
                        if tipo in ("image", "video", "audio"):
                            blocchi.append({"type": tipo, "mime_type": mime_type, "base64": contenuto})
                        elif mime_type=="text/plain":
                            blocchi.append({"type": "text-plain", "mime_type": mime_type, "text": contenuto})
                        else:
                            blocchi.append({"type": "file", "mime_type": mime_type, "base64": contenuto, "filename": filename})
                    if m.get_ruolo()=="user":
                        tuple_da_ritornare.append((HumanMessage(content_blocks=blocchi), m))
                    else: # m.get_ruolo()=="ai" o "assistant"
                        tuple_da_ritornare.append((AIMessage(content_blocks=blocchi), m))
        return tuple_da_ritornare

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
    
    def ripulisci_chat(self, modello):
        if modello in self._cronologia_messaggi and self._cronologia_messaggi[modello]!=None:
            self._cronologia_messaggi[modello].clear()
    
    def set_modello_scelto(self, modello, autocaricamento_dal_db=False):
        if not modello:
            return
        self._modello_scelto=modello
        # se non è presente nessuna cronologia per il modello...
        if modello not in self._cronologia_messaggi: 
            # ...allora la carico dal disco
            self._cronologia_messaggi[modello]=self._carica_cronologia_da_disco(modello) if autocaricamento_dal_db else []
        # se è None vuol dire che è la voce relativa al modello di default
        elif self._cronologia_messaggi[modello] is None:
            self._cronologia_messaggi[modello] = self._carica_cronologia_da_disco(modello) if autocaricamento_dal_db else []
        # se la modalità agentica è attiva allora ricrea l'agent col nuovo modello
        if self._modalita_agentica:
            self._crea_agent()
        

    def get_modalita_agentica(self):
        return self._modalita_agentica
    
    def set_modalita_agentica(self, attiva: bool):
        """Imposta la modalità agentica e crea/rimuove l'agent."""
        self._modalita_agentica = attiva
        if attiva and self._client is not None:
            self._crea_agent()
        else:
            self._agent = None

    def _crea_agent(self):
        """Crea l'agent ReAct con il nuovo API (graph-based)."""
        if not self._client:
            raise Exception("Client LLM non inizializzato.")
        try:
            self._agent = create_agent(
                model=self._client, 
                tools=self._tools,
                # verbose=True,  # Imposta True per debug (stampa pensieri/azioni)
                # max_iterations=5,  # Opzionale: limita loop ReAct
                # system_prompt="You are a helpful assistant."  
            )
        except ImportError as e:
            raise Exception(f"LangChain agents non disponibile: {e}. Assicurati di avere langchain-agents e langgraph installati.")
        except Exception as e:
            raise Exception(f"Errore creazione agent: {e}")
        
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
            self.set_modello_scelto(modello)
            self.set_disponibile(True)
        except Exception as errore:
            self.set_disponibile(False)
            self._client=None
            raise Exception(errore)
    
    def invia_messaggi(self, messaggi: list[Messaggio]):
        """Invia i messaggi al modello multimodale e aggiorna la cronologia."""
        if not self._modello_scelto:
            raise Exception("Client non inizializzato. Inserisci un'API KEY valida e scegli un modello.")
        # lista di tuple in cui il primo elemento è un messaggio in formato Langchain e il secondo è lo stesso elemento ma in formato "Messaggio"
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

            cronologia_precedente=[messaggio for messaggio, _ in cronologia_modello]
            cronologia_completa = cronologia_precedente + messaggi_da_inviare
            # Crea il prompt template
            prompt = ChatPromptTemplate.from_messages([*cronologia_completa])
            if self._modalita_agentica:
                # Invoca l'agent con i messaggi
                risposta = self._agent.invoke({"messages": cronologia_completa})
                # Estrae l'ultimo messaggio dell'agent. Se serve la risposta comprensiva dei messaggi intermedi allora va salvata tutta la lista risposta["messages"]
                ultimo_messaggio = risposta["messages"][-1]
                testo_risposta = getattr(ultimo_messaggio, "content", ultimo_messaggio)
                # Nessun content_blocks per agent di default
                m = AIMessage(content=testo_risposta)
            else:
                # Modalità normale (codice esistente)
                base_chain = prompt | self._client
                risposta = base_chain.invoke({})
                testo_risposta = getattr(risposta, "content", risposta)
                allegati_risposta = getattr(risposta, "content_blocks", [])
                m = AIMessage(content=testo_risposta, content_blocks=allegati_risposta)
            # Aggiungi messaggi utente alla cronologia (comune)
            cronologia_modello.extend([(msg, self._converti_messaggio(msg)) for msg in messaggi_da_inviare])
            # Aggiungi risposta finale (solo l'output, senza intermedi dell'agent)
            cronologia_modello.append((m, self._converti_messaggio(m)))
        except Exception as errore:
            raise Exception(f"Errore nell'invio del messaggio: {errore}")
            
    # converte un messaggio di Langchain (AIMessage, SystemMessage, HumanMessage,...) in un'istanza della classe Messaggio
    def _converti_messaggio(self, m):
        ruolo=m.type
        testo=""
        allegati: list[Allegato]=list()
        timestamp=datetime.now()
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
        return Messaggio(testo=testo, ruolo=ruolo, allegati=allegati, timestamp=timestamp, id=f"{self._nome}-{self._modello_scelto}")
        
    """ 
    Ritorna la lista di messaggi nella cronologia di un certo modello (se non specificato viene preso il modello_scelto)
    in formato "Messaggio". Self._cronologia_messaggi[self._modello_scelto] è una lista di tuple (m0, m1) in cui m0 
    è un messaggio in formato Langchain (quindi un'istanza di HumanMessage, AIMessage,...) mentre
    m1 è un'istanza della classe Messaggio, usata per mostrare il contenuto sulla GUI e per i salvataggi 
    sul DB. Questo metodo ritorna una lista di m1.
    """
    def get_cronologia_messaggi(self, modello=None) -> List[Messaggio]: 
        modello = modello or self._modello_scelto
        if not modello or not self._cronologia_messaggi or not self._cronologia_messaggi[modello]:
            return []
        return [messaggio for _, messaggio in self._cronologia_messaggi[modello]]
    
    # questo metodo va sul DB, carica i messaggi salvati e li aggiunge alla cronologia attuale
    def carica_chat_da_db(self, modello=None):
        modello=modello or self._modello_scelto
        # recupera i messaggi dal DB
        messaggi_su_disco=self._carica_cronologia_da_disco(modello=modello)
        # fonde i messaggi provenienti dal db con quelli già presenti in memoria.
        # Per evitare doppioni, confronta i timestamp dei messaggi in memoria con
        # quello del messaggio più recente su DB. Solo i messaggi successivi a quest'ultimo
        # saranno aggiunti alla cronologia della chat
        messaggi_da_aggiungere=[]
        if messaggi_su_disco: # se ci sono messaggi su disco, li unisco a quelli in memoria
            _, ultimo_messaggio_su_disco=messaggi_su_disco[-1]
            messaggi_da_aggiungere=[(m0,m1) for m0,m1 in self._cronologia_messaggi[modello] if m1.timestamp() > ultimo_messaggio_su_disco.timestamp()]
        else: # altrimenti la chat sarà composta solo dai messaggi già in memoria
            messaggi_da_aggiungere=self._cronologia_messaggi[modello]
        self._cronologia_messaggi[modello]=messaggi_su_disco+messaggi_da_aggiungere
    
    # ritorna la lista dei modelli che hanno almeno un messaggio in chat
    def get_lista_modelli_con_chat(self) -> List[Messaggio]: 
        return [modello for modello in self._cronologia_messaggi if self._cronologia_messaggi[modello]]
        
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