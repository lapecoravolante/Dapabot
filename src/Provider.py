from abc import ABC, abstractmethod
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.messages import HumanMessage, SystemMessage, AIMessage
from Messaggio import Messaggio
from Allegato import Allegato
import base64

class Provider(ABC):
      
    def __init__(self, nome, prefisso_token="", base_url=""):
        self._nome=nome
        self._prefisso_token=prefisso_token
        self._base_url=base_url
        self._modelli=set()
        self._api_key=prefisso_token
        self._client=None
        self._cronologia_messaggi = {} # dizionario che associa un modello alla sua cronologia dei messaggi
        self._modello_scelto = ""
    
    @abstractmethod
    def get_cronologia_messaggi():
        pass
        
    def _controlla_api_key(self, api_key):
        if (self._api_key=="" or api_key==self._prefisso_token) and api_key=="":
            raise Exception("API_KEY non valida!")
        if (self._api_key=="" or self._api_key==self._prefisso_token) and api_key!="":
            self._api_key=api_key
        return True
            
    @abstractmethod
    def lista_modelli(self, api_key=""):
        pass
       
    def nome(self):
        return self._nome
    
    def prefisso_token(self):
        return self._prefisso_token

    @abstractmethod
    def set_client(self, modello, api_key):
        pass
    
    @abstractmethod
    def invia_messaggi(self, messaggi):
        pass

    def set_client(self, modello, api_key):
        # se non sono cambiati né il modello né l'apikey, ritorno il modello attualmente in uso
        if self._modello_scelto == modello and self._api_key == api_key:
            return self._client
        try:
            self._controlla_api_key(api_key=api_key)
            self._client=self._crea_client(base_url=self._base_url, modello=modello, api_key=api_key)
            self._modello_scelto = modello
            if modello not in self._cronologia_messaggi.keys():
                self._cronologia_messaggi[modello]=[]
        except Exception as errore:
            raise Exception(errore)
    
    def invia_messaggi(self, messaggi):
        """Invia i messaggi al modello multimodale e aggiorna la cronologia."""
        if not self._modello_scelto:
            raise Exception("Client non inizializzato. Chiama prima set_client().")
        cronologia_modello = self._cronologia_messaggi[self._modello_scelto]
        messaggi_da_inviare = []        
        try:
            for m in messaggi:
                match m.get_ruolo():
                    case "system":
                        messaggi_da_inviare.append(SystemMessage(content=m.get_testo()))
                    case "user":
                        blocchi=[{"type": "text", "text": m.get_testo()}]
                        for f in m.get_allegati():
                            b64 = base64.b64encode(f.getvalue()).decode("utf-8")
                            tipo = f.type.split("/")[0] 
                            match tipo:
                                case "image" | "video" | "audio" | "text-plain":
                                    blocchi.append({"type": tipo, "mime_type": f.type, "base64": b64})
                                case _:
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
            for allegato in m.content_blocks:
                tipo = allegato["type"]
                testo=allegato["text"] if tipo == "text" else ""
                contenuto = base64.b64decode(allegato["base64"]) if tipo!="text" else allegato["text"]
                mime_type = allegato["mime_type"] if tipo!="text" else "text"
                allegati.append(Allegato(tipo=tipo, contenuto=contenuto, mime_type=mime_type))
            cronologia_da_ritornare.append(Messaggio(testo=testo, ruolo=ruolo, allegati=allegati))
        return cronologia_da_ritornare