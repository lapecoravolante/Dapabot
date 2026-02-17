from src.providers.base import Provider
from langchain_openai import OpenAIEmbeddings
from langchain.messages import HumanMessage, SystemMessage, AIMessage
from src.Messaggio import Messaggio
from src.Allegato import Allegato
from replicate.client import Client
from replicate.exceptions import ModelError, ReplicateError
import replicate, requests, urllib

class ReplicateProvider(Provider):
    
    def __init__(self, nome="Replicate", prefisso_token="r8_", base_url="https://api.replicate.com/v1/"):
        super().__init__(nome=nome, prefisso_token=prefisso_token, base_url=base_url)
        # Dizionario che mappa nomi user-friendly (owner/name o owner/name:version) agli ID effettivi
        self._model_id_map = {}

    def _query(self, url):
        """
        Usa requests per ottenere la lista dei modelli
        Replicate identifica i modelli con un ID poco user friendly ma fornisce anche la stringa
        "owner/nome:versione" alternativa per selezionare il modello. Non tutti i modelli però hanno 
        la versione pubblicamente visibile, quindi per tagliare la testa al toro viene costruita
        una mappa che associa ad ogni id di modello la stringa 'owner/nome:versione' da ritornare 
        per avere qualcosa di più descrittivo sulla GUI.
        Il codice usa l'id per lavorare mentre l'utente sulla gui vede 'owner/nome:versione'.
        """
        # Popola il dizionario _model_id_map con la mappatura nome → ID versione.        
        try:
            modelli = []
            self._model_id_map.clear()
            
            # Usa requests che gestisce meglio i proxy di sistema
            headers = {}
            if self._api_key and self._api_key != self._prefisso_token:
                headers['Authorization'] = f'Bearer {self._api_key}'
            
            response = requests.get(f"{self._base_url}/models", headers=headers)
            response.raise_for_status()
            json_list = response.json().get("results", [])
            
            for modello in json_list:
                if modello.get("visibility") != "public":
                    continue
                owner = modello["owner"]
                name = modello["name"]
                default_example = modello.get("default_example", {})
                version = default_example.get("version", "hidden")
                model_id = default_example.get("id", "")
                # Costruisci il nome user-friendly
                user_friendly_name = f"{owner}/{name}:{version}" if version != "hidden" else f"{owner}/{name}"
                # Mappa il nome user-friendly all'identificatore da usare con l'API
                # Per modelli con versione "hidden", usa il formato "owner/name"
                # Per altri modelli, usa l'ID univoco della versione
                self._model_id_map[user_friendly_name] = user_friendly_name if version == "hidden" else model_id if model_id else version
                modelli.append(user_friendly_name)
            
            self.set_disponibile(True)
        except Exception as e:
            print(f"Errore in _query: {e}")
            self.set_disponibile(False)
            modelli = []
            self._model_id_map.clear()
        finally:
            return modelli
    
    def lista_modelli(self, api_key=""):
        if self._modelli:  # caching
            return list(self._modelli)
        self._modelli = set(self._query(url="models"))
        return list(self._modelli)
    
    def lista_modelli_rag(self):
        if self._modelli_rag:  # caching
            return self._modelli_rag
        self._modelli_rag = self._query(url="embeddings/models")
        return self._modelli_rag
        
    def set_modello_scelto(self, modello, autocaricamento_dal_db=False):
        """
        Override per convertire il nome user-friendly nell'ID effettivo.
        """
        if not modello:
            return
        
        # Se il modello non è nella mappa, carica la lista
        if modello not in self._model_id_map and not self._modelli:
            self.lista_modelli()
        
        # Chiama il metodo della classe base
        super().set_modello_scelto(modello, autocaricamento_dal_db)
    
    def _crea_client(self, base_url, modello, api_key):
        """
        Crea un client Replicate nativo. Gli passo il proxy nel caso servisse
        """
        return Client(api_token=api_key, proxy=urllib.request.getproxies()["https"])
    
    def invia_messaggi(self, messaggi: list[Messaggio], status_container=None):
        """
        Invia messaggi usando il client Replicate nativo.
        Supporta multimodalità e RAG.
        """
        if not self._modello_scelto:
            raise Exception("Client non inizializzato. Inserisci un'API KEY valida e scegli un modello.")
        
        if not self._client:
            raise Exception("Client Replicate non inizializzato.")
        
        cronologia_modello = self._cronologia_messaggi[self._modello_scelto]
        preambolo_rag = "\nRispondi dando priorità al contesto fornito di seguito:\n"
        
        try:
            # 1. Costruisce il prompt a partire dalla cronologia esistente
            prompt_parts = []
            
            # Cronologia precedente
            for msg_langchain, _ in cronologia_modello:
                ruolo = msg_langchain.type
                contenuto = getattr(msg_langchain, "content", "")
                if ruolo == "system":
                    prompt_parts.append(f"System: {contenuto}")
                elif ruolo == "user":
                    prompt_parts.append(f"User: {contenuto}")
                elif ruolo in ("ai", "assistant"):
                    prompt_parts.append(f"Assistant: {contenuto}")
            
            # 2. Appende al prompt i nuovi messaggi
            messaggi_da_salvare = []
            input_multimodale = {}
            
            for m in messaggi:
                if m.get_ruolo() == "system":
                    prompt_parts.append(f"System: {m.get_testo()}")
                    # Crea messaggio con ID per il salvataggio
                    msg_system = Messaggio(
                        ruolo="system",
                        testo=m.get_testo(),
                        allegati=[],
                        timestamp="",
                        id=f"{self._nome}-{self._modello_scelto}"
                    )
                    messaggi_da_salvare.append((SystemMessage(content=m.get_testo()), msg_system))
                
                elif m.get_ruolo() == "user":
                    contenuto_testo = m.get_testo()
                    allegati_utente = m.get_allegati()
                    
                    # 3. Gestisce il RAG
                    if self._rag.get_attivo():
                        self._rag.set_prompt(m)
                        allegati_rag: list[Allegato] = self.rag()
                        contenuti_rag = "\n---\n".join(allegato.contenuto for allegato in allegati_rag)
                        contenuto_testo += preambolo_rag + contenuti_rag
                    
                    # 4. Se non bisgona fare RAG, allora gli allegati si possono aggiungere come sono
                    elif allegati_utente:
                        input_multimodale = self._prepara_input_multimodale(m)
                    
                    prompt_parts.append(f"User: {contenuto_testo}")
                    # Crea messaggio con ID per il salvataggio
                    msg_user = Messaggio(
                        ruolo="user",
                        testo=contenuto_testo,
                        allegati=allegati_utente,
                        timestamp="",
                        id=f"{self._nome}-{self._modello_scelto}"
                    )
                    messaggi_da_salvare.append((HumanMessage(content=contenuto_testo), msg_user))
            
            # 5. Costruisce il prompt completo aggiungendo i nuovi messaggi a quelli della cronologia
            prompt_completo = "\n\n".join(prompt_parts) + "\n\nAssistant:"
            
            # 6. Ottiene l'ID del modello della mappa
            model_id = self._model_id_map.get(self._modello_scelto)
            if not model_id:
                raise Exception(f"Modello non trovato nella mappa: {self._modello_scelto}")
            
            # 7. Prepara l'input per il modello
            model_input = {
                "prompt": prompt_completo,
                **input_multimodale  # Aggiungi eventuali input multimodali
            }

            # 8. Manda il prompt al modello e recupera la risposta 
            try:
                risposta = self._client.run(model_id, input=model_input)
            except ModelError as e:
                raise Exception(f"Errore del modello: {e}")
            except ReplicateError as e:
                raise Exception(f"Errore API Replicate: {e}")
            
            # 9. Separa il testo e gli allegati della risposta
            testo_risposta, allegati_risposta = self._converti_output(risposta)
            
            # 10. Creare messaggio risposta
            m = AIMessage(content=testo_risposta)
            
            # 11. Aggiorna la cronologia con i messaggi che hanno già l'ID
            cronologia_modello.extend(messaggi_da_salvare)
            
            # Crea il messaggio finale (con eventuali allegati) da salvare in cronologia
            messaggio_risposta = Messaggio(
                ruolo="assistant",
                testo=testo_risposta,
                allegati=allegati_risposta,
                timestamp="",
                id=f"{self._nome}-{self._modello_scelto}"
            )
            cronologia_modello.append((m, messaggio_risposta))
            
        except Exception as errore:
            raise Exception(f"Errore nell'invio del messaggio: {errore}")
    
    def _prepara_input_multimodale(self, messaggio: Messaggio) -> dict:
        """
        Prepara input multimodale per Replicate.
        Converte allegati in formato accettato dall'API.
        """
        input_extra = {}
        
        for allegato in messaggio.get_allegati():
            # Ottieni il tipo MIME
            mime_type = getattr(allegato, 'type', 'application/octet-stream')
            tipo_principale = mime_type.split('/')[0]
            
            # Replicate accetta file handle o URL
            if tipo_principale == "image":
                input_extra["image"] = allegato
            elif tipo_principale == "audio":
                input_extra["audio"] = allegato
            elif tipo_principale == "video":
                input_extra["video"] = allegato
            else:
                # Per altri tipi, prova a passare come file generico
                input_extra["file"] = allegato
        
        return input_extra
    
    def _converti_output(self, output) -> tuple[str, list]:
        """
        Converte l'output di Replicate in testo e allegati.
        
        Returns:
            tuple: (testo, lista_allegati)
        """
        testo = ""
        allegati = []
        
        if output is None:
            return "", []
        
        # Output può essere: stringa, lista, FileOutput, o URL
        if isinstance(output, str):
            # Potrebbe essere testo o URL
            if output.startswith(("http://", "https://")):
                # È un URL a un file
                allegati.append(self._crea_allegato_da_url(output))
            else:
                testo = output
        
        elif isinstance(output, list):
            # Lista di elementi (stringhe, URL, FileOutput)
            for item in output:
                if isinstance(item, str):
                    if item.startswith(("http://", "https://")):
                        allegati.append(self._crea_allegato_da_url(item))
                    else:
                        testo += item
                elif hasattr(item, 'read'):
                    # FileOutput o file-like object
                    allegati.append(self._crea_allegato_da_file_output(item))
                else:
                    testo += str(item)
        
        elif hasattr(output, 'read'):
            # FileOutput singolo
            allegati.append(self._crea_allegato_da_file_output(output))
        
        else:
            # Altro tipo, converti in stringa
            testo = str(output)
        
        return testo, allegati
    
    def _crea_allegato_da_url(self, url: str):
        """
        Crea un oggetto Allegato da un URL.
        """
        # Per ora, salva solo l'URL come riferimento
        # In futuro si potrebbe scaricare il file
        return Allegato(
            contenuto=url,
            tipo="url",
            mime_type="text/uri-list",
            filename=url.split('/')[-1]
        )
    
    def _crea_allegato_da_file_output(self, file_output):
        """
        Crea un oggetto Allegato da un FileOutput di Replicate.
        """
        try:
            # Leggi il contenuto del file
            contenuto = file_output.read()
            
            # Determina il tipo MIME dall'URL se disponibile
            url = getattr(file_output, 'url', '')
            mime_type = "application/octet-stream"
            
            if '.png' in url or '.jpg' in url or '.jpeg' in url:
                mime_type = f"image/{url.split('.')[-1]}"
            elif '.mp4' in url or '.webm' in url:
                mime_type = f"video/{url.split('.')[-1]}"
            elif '.mp3' in url or '.wav' in url:
                mime_type = f"audio/{url.split('.')[-1]}"
            
            return Allegato(
                contenuto=contenuto,
                tipo=mime_type.split('/')[0],
                mime_type=mime_type,
                filename=url.split('/')[-1] if url else "output"
            )
        except Exception as e:
            print(f"Errore nella conversione FileOutput: {e}")
            return None
    
    def _converti_messaggio(self, m):
        """Converte un messaggio LangChain in un oggetto Messaggio."""
        ruolo = m.type
        testo = getattr(m, "content", "")
        allegati = []
        
        return Messaggio(ruolo=ruolo, testo=testo, allegati=allegati, timestamp="")

    def rag(self):
        if self._rag.get_modello():
            self._rag.set_motore_di_embedding(
                OpenAIEmbeddings(
                    model=self._rag.get_modello(), 
                    base_url=self._base_url, 
                    api_key=self._api_key
                )
            )
            self._rag.set_tokenizer(tokenizer="gpt2", max_tokens=1000, overlap=150)
        return self._rag.run()

# Made with Bob
