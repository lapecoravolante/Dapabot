from src.providers.base import Provider
from langchain_openai import OpenAIEmbeddings
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.callbacks import CallbackManagerForLLMRun
from src.Messaggio import Messaggio
from src.Allegato import Allegato
from replicate.client import Client
from replicate.exceptions import ModelError, ReplicateError
import replicate, requests, urllib
from typing import Any, Optional
import base64
import magic


class ReplicateChatModel(BaseChatModel):
    """
    Implementazione di BaseChatModel per Replicate.
    Supporta messaggi multimodali, tools e integrazione nativa con LangChain.
    """
    
    client: Any = None
    model_id: str = ""
    model_id_map: dict[str, str] = {}
    
    class Config:
        arbitrary_types_allowed = True
    
    @property
    def _llm_type(self) -> str:
        """Ritorna il tipo di LLM."""
        return "replicate"
    
    def _generate(
        self,
        messages: list[BaseMessage],
        stop: Optional[list[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """
        Genera una risposta dai messaggi usando l'API Replicate.
        
        Args:
            messages: Lista di messaggi in formato LangChain
            stop: Sequenze di stop opzionali
            run_manager: Manager per callbacks
            **kwargs: Parametri aggiuntivi
            
        Returns:
            ChatResult con la risposta generata
        """
        if not self.client:
            raise ValueError("Client Replicate non inizializzato")
        
        if not self.model_id:
            raise ValueError("Model ID non specificato")
        
        # Converti i messaggi in prompt per Replicate
        prompt = self._convert_messages_to_prompt(messages)
        
        # Prepara input multimodale se presente
        multimodal_input = self._prepare_multimodal_input(messages)
        
        # Prepara l'input completo per il modello
        model_input = {
            "prompt": prompt,
            **multimodal_input
        }
        
        # Aggiungi parametri di stop se presenti
        if stop:
            model_input["stop_sequences"] = stop
        
        # Aggiungi eventuali parametri extra
        model_input.update(kwargs)
        
        try:
            # Chiama l'API Replicate
            output = self.client.run(self.model_id, input=model_input)
            
            # Converti l'output in AIMessage
            ai_message = self._convert_output(output)
            
            # Crea il risultato
            generation = ChatGeneration(message=ai_message)
            return ChatResult(generations=[generation])
            
        except ModelError as e:
            raise ValueError(f"Errore del modello Replicate: {e}")
        except ReplicateError as e:
            raise ValueError(f"Errore API Replicate: {e}")
        except Exception as e:
            raise ValueError(f"Errore durante la generazione: {e}")
    
    def _convert_messages_to_prompt(self, messages: list[BaseMessage]) -> str:
        """
        Converte una lista di messaggi LangChain in un prompt testuale per Replicate.
        
        Args:
            messages: Lista di messaggi LangChain
            
        Returns:
            Prompt formattato come stringa
        """
        prompt_parts = []
        
        for msg in messages:
            role = msg.type
            content = getattr(msg, "content", "")
            
            # Gestisci diversi tipi di messaggi
            if role == "system":
                prompt_parts.append(f"System: {content}")
            elif role == "human":
                prompt_parts.append(f"User: {content}")
            elif role in ("ai", "assistant"):
                prompt_parts.append(f"Assistant: {content}")
            elif role == "tool":
                # Per i messaggi tool, includi il risultato
                tool_name = getattr(msg, "name", "tool")
                prompt_parts.append(f"Tool ({tool_name}): {content}")
            else:
                # Fallback per altri tipi
                prompt_parts.append(f"{role.capitalize()}: {content}")
        
        # Aggiungi il prompt per la risposta dell'assistente
        prompt_complete = "\n\n".join(prompt_parts) + "\n\nAssistant:"
        return prompt_complete
    
    def _prepare_multimodal_input(self, messages: list[BaseMessage]) -> dict[str, Any]:
        """
        Prepara input multimodale dai messaggi per Replicate.
        Estrae immagini, audio, video dai content_blocks dei messaggi.
        
        Args:
            messages: Lista di messaggi LangChain
            
        Returns:
            Dizionario con input multimodali
        """
        multimodal_input = {}
        
        for msg in messages:
            # Controlla se il messaggio ha content_blocks (formato multimodale)
            if hasattr(msg, "content_blocks") and msg.content_blocks:
                for block in msg.content_blocks:
                    if not isinstance(block, dict):
                        continue
                    
                    block_type: Literal['text-plain', 'audio', 'file', 'image', 'video', 'invalid_tool_call', 'server_tool_result', 'server_tool_call', 'server_tool_call_chunk', 'text', 'tool_call', 'tool_call_chunk', 'reasoning', 'non_standard'] = block.get("type", "")
                    
                    # Gestisci diversi tipi di contenuto multimodale
                    if block_type == "image":
                        # Decodifica base64 se presente
                        if "base64" in block:
                            image_data = base64.b64decode(block["base64"])
                            multimodal_input["image"] = image_data
                        elif "url" in block:
                            multimodal_input["image"] = block["url"]
                    
                    elif block_type == "audio":
                        if "base64" in block:
                            audio_data = base64.b64decode(block["base64"])
                            multimodal_input["audio"] = audio_data
                        elif "url" in block:
                            multimodal_input["audio"] = block["url"]
                    
                    elif block_type == "video":
                        if "base64" in block:
                            video_data = base64.b64decode(block["base64"])
                            multimodal_input["video"] = video_data
                        elif "url" in block:
                            multimodal_input["video"] = block["url"]
                    
                    elif block_type == "file":
                        if "base64" in block:
                            file_data = base64.b64decode(block["base64"])
                            multimodal_input["file"] = file_data
        
        return multimodal_input
    
    def _convert_output(self, output: Any) -> AIMessage:
        """
        Converte l'output di Replicate in un AIMessage di LangChain.
        
        Args:
            output: Output dall'API Replicate
            
        Returns:
            AIMessage con il contenuto della risposta
        """
        text_content = ""
        content_blocks = []
        
        if output is None:
            return AIMessage(content="")
        
        # Output può essere: stringa, lista, FileOutput, o URL
        if isinstance(output, str):
            # Potrebbe essere testo o URL
            if output.startswith(("http://", "https://")):
                # È un URL a un file - aggiungi come blocco
                content_blocks.append({
                    "type": "url",
                    "url": output
                })
            else:
                text_content = output
        
        elif isinstance(output, list):
            # Lista di elementi (stringhe, URL, FileOutput)
            for item in output:
                if isinstance(item, str):
                    if item.startswith(("http://", "https://")):
                        content_blocks.append({
                            "type": "url",
                            "url": item
                        })
                    else:
                        text_content += item
                elif hasattr(item, 'read'):
                    # FileOutput o file-like object
                    try:
                        file_content = item.read()
                        mime_type = self._detect_mime_type(file_content)
                        
                        content_blocks.append({
                            "type": mime_type.split('/')[0] if mime_type else "file",
                            "mime_type": mime_type,
                            "base64": base64.b64encode(file_content).decode('utf-8')
                        })
                    except Exception as e:
                        print(f"Errore nella lettura FileOutput: {e}")
                else:
                    text_content += str(item)
        
        elif hasattr(output, 'read'):
            # FileOutput singolo
            try:
                file_content = output.read()
                mime_type = self._detect_mime_type(file_content)
                
                content_blocks.append({
                    "type": mime_type.split('/')[0] if mime_type else "file",
                    "mime_type": mime_type,
                    "base64": base64.b64encode(file_content).decode('utf-8')
                })
            except Exception as e:
                print(f"Errore nella lettura FileOutput: {e}")
        
        else:
            # Altro tipo, converti in stringa
            text_content = str(output)
        
        # Crea AIMessage con contenuto e blocchi
        if content_blocks:
            # Aggiungi il testo come primo blocco se presente
            if text_content:
                content_blocks.insert(0, {"type": "text", "text": text_content})
            return AIMessage(content=text_content, content_blocks=content_blocks)
        else:
            return AIMessage(content=text_content)
    
    def _detect_mime_type(self, file_content: bytes) -> str:
        """
        Rileva il tipo MIME dal contenuto del file usando python-magic.
        
        Args:
            file_content: Contenuto del file in bytes
            
        Returns:
            Tipo MIME rilevato
        """
        if not file_content:
            return "application/octet-stream"
        
        try:
            # Usa i primi 2048 byte per il rilevamento (come raccomandato dalla documentazione)
            buffer = file_content[:2048] if len(file_content) > 2048 else file_content
            mime_type = magic.from_buffer(buffer, mime=True)
            return mime_type
        except Exception as e:
            print(f"Errore nel rilevamento MIME type: {e}")
            return "application/octet-stream"
    
    def bind_tools(
        self,
        tools: list[Any],
        **kwargs: Any,
    ) -> "ReplicateChatModel":
        """
        Associa tools al modello per l'uso con agents.
        
        Args:
            tools: Lista di tools LangChain
            **kwargs: Parametri aggiuntivi
            
        Returns:
            Nuova istanza del modello con tools associati
        """
        # Per ora, Replicate non supporta nativamente function calling
        # Ritorniamo una copia del modello che può essere usata con agents
        # Gli agents di LangChain gestiranno i tools tramite ReAct prompting
        return self.model_copy(update={"tools": tools, **kwargs})


class ReplicateProvider(Provider):
    
    def __init__(self, nome="Replicate", prefisso_token="r8_", base_url="https://api.replicate.com/v1/"):
        super().__init__(nome=nome, prefisso_token=prefisso_token, base_url=base_url)
        # Dizionario che mappa nomi user-friendly (owner/name o owner/name:version) agli ID effettivi
        self._model_id_map = {}

    def _query(self, url):
        """
            Replicate identifica i modelli con un ID poco user friendly ma fornisce anche la stringa
            "owner/nome:versione" alternativa per selezionare il modello. Non tutti i modelli però hanno 
            la versione pubblicamente visibile, quindi per tagliare la testa al toro viene costruita
            una mappa che associa ad ogni nome user-friendly di modello il relativo nome da usare nel codice.
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
        Crea un'istanza di ReplicateChatModel che implementa l'interfaccia LangChain.
        """
        # Crea il client Replicate nativo
        replicate_client = Client(api_token=api_key, proxy=urllib.request.getproxies().get("https", None))
        
        # Ottieni l'ID del modello dalla mappa
        model_id = self._model_id_map.get(modello, modello)
        
        # Crea e ritorna il ReplicateChatModel
        return ReplicateChatModel(
            client=replicate_client,
            model_id=model_id,
            model_id_map=self._model_id_map
        )

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
