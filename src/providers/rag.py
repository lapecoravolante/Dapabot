from langchain_docling import DoclingLoader
from docling.chunking import HybridChunker
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from src.Messaggio import Messaggio
from src.Allegato import Allegato
from src.Configurazione import Configurazione
import os, logging, hashlib, json, shutil
from typing import Dict, Literal, Tuple

class Rag():
    
    DEFAULT_EMBEDDING_MODEL="sentence-transformers/all-MiniLM-L6-v2"
    DEFAULT_UPLOAD_DIR="uploads/"
    DEFAULT_TOPK=3
    DEFAULT_EMBEDDING_ENGINE=HuggingFaceEmbeddings
    DEFAULT_VECTORSTORE_PATH = "vectorstore_cache/"  # dove vengono persistiti i vector store
    DEFAULT_VECTORSTORE_INDEX_FILE="index.json"
    AVAILABLE_SEARCH_MODALITIES=["similarity", "mmr"]
    
    # cache dei vectorstore per file già elaborati
    _cache_vectorstores: Dict[Tuple, Chroma] = {}
    # Configurazione dell'applicazione
    configurazione = Configurazione().get(Configurazione.RAG_KEY)
    
    _pulizia_fatta = False  # esegue la pulizia solo una volta per processo
    
    def __init__(self, attivo=False, modello=None, upload_dir=None, topk=None, 
                 motore_di_embedding=None, tokenizer="", vectorstore_cache_path="", modalita_ricerca="similarity"):
        # Silenzia i log di sentence-transformers
        logging.getLogger("sentence_transformers").setLevel(logging.ERROR)
        logging.getLogger("sentence_transformers.SentenceTransformer").setLevel(logging.ERROR)
        self.set_upload_dir(upload_dir) # la directory con gli allegati
        self.set_modello(modello) # il modello di embedding scelto
        self.set_topk(topk) # imposto quanti risultati tornare all'utente (k)
        self.set_prompt(None) # inizializzo un prompt vuoto  
        self.set_motore_di_embedding(motore_di_embedding) 
        self.set_attivo(attivo) 
        self.set_tokenizer(tokenizer)
        self.set_vectorstore_cache_path(vectorstore_cache_path) # Directory di persistenza (per provider)
        self.set_modalita_ricerca(modalita_ricerca)

    def to_dict(self):
        return {
            "modello": self._modello,
            "directory_allegati": self._upload_dir,
            "top_k": self._topk,
            "directory_vectorstores": self._persist_dir,
            "modalita_ricerca": self._modalita_ricerca
        }
        
    # Per ora il rag supporta solo 2 modalità di ricerca: mmr e similarity
    def set_modalita_ricerca(self, modalita_ricerca):
        if modalita_ricerca not in Rag.AVAILABLE_SEARCH_MODALITIES:
            raise ValueError(f"Modalità di ricerca non valida: {modalita_ricerca}")
        self._modalita_ricerca = modalita_ricerca
        
    def get_modalita_ricerca(self):
        return self._modalita_ricerca

    def _pulizia_orfani(self) -> None:
        """
        Rimuove le directory orfane dentro self._persist_dir, cioè quelle 
        che non corrispondono a nessuna 'collection_name' nell'indice JSON.
        Esegue la pulizia una sola volta per processo.
        """
        if Rag._pulizia_fatta:
            return
        try:
            indice = self.get_indice_collezioni() or {}
            # Directory "attese": <persist_dir>/<collection_name>
            attese = set()

            for _, entry in indice.items():
                if isinstance(entry, dict):
                    cn = entry.get("collection_name", "")
                else:
                    cn = str(entry)
                if cn:
                    attese.add(cn)

            # Se la persist dir non esiste, nulla da fare
            if not os.path.isdir(self._persist_dir):
                Rag._pulizia_fatta = True
                return

            # Scansiona solo sottocartelle (non file come chroma.sqlite3)
            for nome in os.listdir(self._persist_dir):
                percorso = os.path.join(self._persist_dir, nome)
                if not os.path.isdir(percorso):
                    continue
                if nome not in attese:
                    try:
                        shutil.rmtree(percorso)
                        logging.info(f"[RAG] Rimossa directory orfana: {percorso}")
                    except Exception as e:
                        logging.warning(f"[RAG] Impossibile rimuovere {percorso}: {e}")

        except Exception as e:
            logging.warning(f"[RAG] Errore pulizia orfani in '{self._persist_dir}': {e}")
        finally:
            # In ogni caso segna come eseguito per evitare più passaggi
            Rag._pulizia_fatta = True

    # crea la directory dove vengono memorizzati i vectorstore
    def set_vectorstore_cache_path(self, path: str):
        self._persist_dir = path or os.path.join(Rag.DEFAULT_VECTORSTORE_PATH, "default")
        os.makedirs(self._persist_dir, exist_ok=True)
        self._indice_vectorestore_path = os.path.join(self._persist_dir, Rag.DEFAULT_VECTORSTORE_INDEX_FILE)
        self._indice_collezioni = self.carica_indice_collezioni()

        if not isinstance(Rag._cache_vectorstores, dict):
            Rag._cache_vectorstores = {}
        # Pulizia one-shot delle directory orfane
        self._pulizia_orfani()

    # imposta i parametri per il chunker: 
    # tokenizer: il tokenizzatore da usare
    # max_tokens: lunghezza massima del chunk
    # overlap: quanti caratteri saranno sovrapposti tra 2 tokens consecutivi
    def set_tokenizer(self, tokenizer, max_tokens=1000, overlap=150):
        self._chunker=HybridChunker()
        if tokenizer!="" and tokenizer:
            if max_tokens > 0 and overlap > 0:
                self._chunker = HybridChunker(tokenizer=tokenizer, 
                                            max_tokens=max_tokens,
                                            overlap=overlap)
            else:
                self._chunker = HybridChunker(tokenizer=tokenizer)
    
    def set_attivo(self, attivo=False):
        self._attivo=attivo
    
    def get_attivo(self):
        return self._attivo
    
    # Imposta il motore per generare gli embedding
    def set_motore_di_embedding(self, motore_di_embedding):
        if motore_di_embedding:
            self._motore_di_embedding=motore_di_embedding
        else:
            self._motore_di_embedding=Rag.DEFAULT_EMBEDDING_ENGINE(model_name=Rag.DEFAULT_EMBEDDING_MODEL)

    def set_modello(self, modello):
        self._modello=Rag.DEFAULT_EMBEDDING_MODEL
        if modello:
           self._modello=modello 
    
    def get_modello(self):
        return self._modello
            
    def set_upload_dir(self, upload_dir):
        self._upload_dir=Rag.DEFAULT_UPLOAD_DIR
        if upload_dir:
            self._upload_dir=upload_dir
    
    def get_upload_dir(self):
        return self._upload_dir
            
    def set_topk(self, topk):
        self._topk=Rag.DEFAULT_TOPK
        if topk:
            self._topk=topk
    
    def get_topk(self):
        return self._topk
    
    def set_prompt(self, prompt: Messaggio):
        self._prompt=prompt
    
    def _filtra_metadati_complessi(self, save_path, mimetype):
        clean_splits = []
        # Docling non supporta i file in testo semplice, quindi devo gestirli separatamente
        if mimetype!="text/plain":
            loader = DoclingLoader(file_path=save_path, chunker=self._chunker)
            splits=loader.load()
            for item in splits:
                # DoclingLoader può restituire Document o tuple, normalizziamo tutto
                if isinstance(item, tuple):
                    doc, extra_meta = item
                    metadata = extra_meta or {}
                else:
                    doc = item
                    metadata = doc.metadata if hasattr(doc, "metadata") else {}
                # convertiamo in Document di LangChain
                clean_splits.append(
                    Document(
                        page_content=doc.page_content,
                        metadata={
                            "source": save_path,
                            "page": metadata.get("page", None),
                        },
                    )
                )
        else:  # se il file è di testo semplice (text/plain)
            try:
                # Lettura robusta con UTF-8, rimpiazza caratteri non decodificabili
                with open(save_path, "rb") as f:
                    content = f.read().decode("utf-8", errors="replace")
                clean_splits.append(
                    Document(
                        page_content=content,
                        metadata={"source": save_path, "page": None},
                    )
                )
            except Exception as e:
                raise Exception(f"Errore nel parsing del testo semplice: {e}")
        return clean_splits
    

    def _key_str(self, vectorstore_id: Tuple) -> str:
        """
        Serializza in modo deterministico il vectorstore_id (tuple) in una stringa,
        da usare come chiave sia in RAM sia nell’indice JSON.
        """
        return json.dumps(vectorstore_id, ensure_ascii=False)

    def _genera_nome_collezione(self, vectorstore_id: Tuple) -> str:
        """
        Genera un nome di collection deterministico e stabile a partire dal vectorstore_id.
        """
        return "rag_" + hashlib.sha256(str(vectorstore_id).encode("utf-8")).hexdigest()

    def _get_vectorstore(self, vectorstore_id: Tuple, path: str, tipo: str) -> Chroma:
        """
        Recupera (o crea) il vectorstore della collection usando una cartella
        di persistenza dedicata: <persist_dir>/<collection_name>/.
        """
        key = self._key_str(vectorstore_id)

        # 1) Cache RAM
        if key in Rag._cache_vectorstores:
            return Rag._cache_vectorstores[key]

        # 2) Prova dall'indice (collection_name già noto)
        entry = self._indice_collezioni.get(key)  # dict {"collection_name": str, "label": str}
        collection_name = entry["collection_name"] if isinstance(entry, dict) else None

        if collection_name:
            # ✅ cartella dedicata per la collection
            collection_dir = os.path.join(self._persist_dir, collection_name)
            os.makedirs(collection_dir, exist_ok=True)
            try:
                vectorstore = Chroma(
                    collection_name=collection_name,
                    embedding_function=self._motore_di_embedding,
                    persist_directory=collection_dir,  # per-collection
                )
            except Exception as e:
                raise Exception(f"Errore apertura collection '{collection_name}': {e}")

            Rag._cache_vectorstores[key] = vectorstore

            # Se la label non è presente, prova a ricostruirla interrogando metadati
            label = entry.get("label", "") if isinstance(entry, dict) else ""
            if not label:
                try:
                    coll = getattr(vectorstore, "_collection", None)
                    if coll is not None:
                        got = coll.get(include=["metadatas"], limit=1)
                        metas = got.get("metadatas") or []
                        if metas and isinstance(metas[0], dict):
                            src = metas[0].get("source")
                            if src:
                                label = os.path.basename(src)
                except Exception:
                    pass

                if label:
                    self._indice_collezioni[key] = {"collection_name": collection_name, "label": label}
                    try:
                        self.salva_indice_collezioni()
                    except Exception as e:
                        logging.warning(f"Non riesco a salvare l'indice con label: {e}")

            return vectorstore

        # 3) Non esiste nell’indice: crea una nuova collection
        splits = self._filtra_metadati_complessi(path, tipo)
        collection_name = self._genera_nome_collezione(vectorstore_id)

        # ✅ cartella dedicata per la collection
        collection_dir = os.path.join(self._persist_dir, collection_name)
        os.makedirs(collection_dir, exist_ok=True)

        try:
            # Passa l’oggetto embeddings come argomento posizionale
            vectorstore = Chroma.from_documents(
                splits,
                self._motore_di_embedding,
                collection_name=collection_name,
                persist_directory=collection_dir,  # per-collection
            )
        except Exception as e:
            raise Exception(f"Errore creazione collection '{collection_name}': {e}")

        Rag._cache_vectorstores[key] = vectorstore

        # Calcolo label utente (basename del file) dai metadati
        label = self._estrai_label_da_splits(splits)
        self._indice_collezioni[key] = {"collection_name": collection_name, "label": label}
        try:
            self.salva_indice_collezioni()
        except Exception as e:
            logging.warning(f"Non riesco a salvare l'indice dei vector store: {e}")

        return vectorstore


    def delete_vectorstore(self, vectorstore_id_str: str) -> bool:
        """
        Cancella la collection dal DB Chroma e aggiorna indice/cache.
        Non rimuove i file su disco: la pulizia avverrà all'avvio tramite
        il metodo pulizia_orfani().
        """
        entry = self._indice_collezioni.get(vectorstore_id_str)
        collection_name = None
        if isinstance(entry, dict):
            collection_name = entry.get("collection_name")
        elif isinstance(entry, str):
            collection_name = entry

        if not collection_name:
            return False

        try:
            # Apri la collection usando la sua cartella dedicata (persistenza per-collection)
            collection_dir = os.path.join(self._persist_dir, collection_name)
            vectorstore = Chroma(
                collection_name=collection_name,
                embedding=self._motore_di_embedding,
                persist_directory=collection_dir,
            )

            client = getattr(vectorstore, "_client", None)
            if client is None:
                raise RuntimeError("Client interno Chroma non disponibile.")

            # Delete logica lato DB
            client.delete_collection(name=collection_name)

        except Exception as e:
            logging.warning(f"Errore cancellazione collection '{collection_name}': {e}")

        # Aggiorna cache e indice
        Rag._cache_vectorstores.pop(vectorstore_id_str, None)
        self._indice_collezioni.pop(vectorstore_id_str, None)
        try:
            self.salva_indice_collezioni()
        except Exception as e:
            logging.warning(f"Non riesco a salvare l'indice dopo delete: {e}")
        return True

    def _estrai_label_da_splits(self, splits) -> str:
        """
        Prova a ricavare una label utente (nome file) dai metadati 'source' dei Document.
        Ritorna il basename del primo 'source' trovato, altrimenti stringa vuota.
        """
        for doc in splits:
            try:
                src = doc.metadata.get("source")
                if src:
                    return os.path.basename(src)
            except Exception:
                continue
        return ""

    # Inizialmente facevo una semplice similarity_search ma mi sono reso conto che con
    # query brevi o con chunk piccoli uscivano molti duplicati. Quindi ho deciso di 
    # implementare anche una MMR (Maximal Marginal Relevance) seguita da una deduplica
    # dei doppioni per pagina.
    def _recupero_chunk(self, vectorstore, modo):
        """
        L'argomento "modo" specifica il tipo di ricerca da effettuare:
            - "mmr": effettua una ricerca Maximal Marginal Relevance. In sostanza vengono presi 
                    un numero di chunk (fetch_k) che è più alto rispetto a quello impostato
                    (top_k) in modo da massimizzare la diversità dei chunk
            - "similarity": effettua una semplice ricerca in basse alla somiglianza tra la 
                            query e il contenuto del testo nel chucnk.
        Qualunque sia la modalità scelta, poi si filtrano i doppioni in base al numero di pagina e al
        contenuto del chunk (si fa l'hash del testo del chuck) 
        """
        top_docs=None
        if modo=="similarity":
            top_docs = vectorstore.similarity_search(self._prompt.get_testo(), k=self._topk)
        elif modo=="mmr":
            # --------- MMR con deduplica --------------
            # 1. Prima si fa la MMR recuperando più chuck di quelli previsti da top_k
            fetch_k = max(self._topk * 4, 20)
            top_docs = vectorstore.max_marginal_relevance_search(
                self._prompt.get_testo(),
                k=self._topk,
                fetch_k=fetch_k,
                lambda_mult=0.3,
            )
        # Elimino i chuck duplicati 
        chunk_unici = []
        seen = set()
        for doc in top_docs:
            content = doc.page_content or ""
            # Faccio l'hash del testo del chunk
            hash = hashlib.sha256(content.encode("utf-8", errors="ignore")).hexdigest()
            key = (doc.metadata.get("source"), doc.metadata.get("page"), hash)
            if key in seen:
                continue
            seen.add(key)
            chunk_unici.append(doc)
        return chunk_unici
    
    def run(self):
        """Esegue il RAG e restituisce i top-k risultati per ciascun allegato"""
        if not self._prompt:
            raise Exception("Errore in fase di RAG: prompt non impostato")
        risultato = []
        try:
            os.makedirs(self._upload_dir, exist_ok=True)
            # imposto le varie parti che compongono il nome della chiave nella cache dei vectorstores            
            engine_name = type(self._motore_di_embedding).__name__
            model_name = self._modello
            chunker_sig = f"{type(self._chunker).__name__}:{getattr(self._chunker,'max_tokens',None)}:{getattr(self._chunker,'overlap',None)}"
            # inizio a scorrere gli allegati
            for f in self._prompt.get_allegati():
                save_path = os.path.join(self._upload_dir, f.name)
                with open(save_path, "wb") as out:
                    out.write(f.getbuffer())
                    file_id=hashlib.sha256(f.getbuffer()).hexdigest()  
                # Questa tupla identifica univocamente un vectorstore nella cache
                chiave_cache = (file_id, engine_name, model_name, chunker_sig)
                # Recupera il vectorstore (dalla cache se già esiste)
                vectorstore = self._get_vectorstore(path=save_path, vectorstore_id=chiave_cache, tipo=f.type)
                # Cancella il file ORIGINARIO (non serve più)
                try:
                    os.remove(save_path)
                except Exception:
                    # Non blocca il flusso se non riesce a cancellare il file (lock, antivirus, etc.)
                    pass
                # Recupera i top-k chunk più rilevanti usando di default la ricerca mmr
                top_docs=self._recupero_chunk(vectorstore=vectorstore, modo=self._modalita_ricerca)
                # Rende ciascun chunk in un code fence "text" (niente interpretazione markdown)
                def as_code_block(s: str) -> str:
                    return f"```text\n{s}\n```"
                risultato.append(Allegato(tipo="text", contenuto="\n\n---\n\n".join(as_code_block(doc.page_content) for doc in top_docs), mime_type="text/plain"))
            return risultato
        except Exception as e:
            raise Exception(f"Errore in fase RAG: {e}")

    # funzione che carica i vectorstore da file
    def carica_indice_collezioni(self):
        """
        Carica l'indice dei vector store. Ritorna un dict:
            { vectorstore_id_str: { "collection_name": str, "label": str } }
        Se il file è della vecchia versione (mappa semplice id->collection), effettua backfill minimale.
        """
        if os.path.exists(self._indice_vectorestore_path):
            try:
                data = {}
                with open(self._indice_vectorestore_path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                for k, v in raw.items():
                    data[k] = {"collection_name": v.get("collection_name", ""), "label": v.get("label", "")}
                return data
            except Exception:
                return {}
        return {}

    # funzione che salva i vectorstore su file
    def salva_indice_collezioni(self):
        """
        Salva su disco l'indice dei vector store:
            { vectorstore_id_str: { "collection_name": str, "label": str } }
        """
        try:
            with open(self._indice_vectorestore_path, "w", encoding="utf-8") as f:
                json.dump(self._indice_collezioni, f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise Exception(f"Errore salvataggio indice Chroma: {e}")
    
    def get_indice_collezioni(self):
        return self._indice_collezioni

    @staticmethod
    def estrai_modello_da_id(id_str: str) -> str:
        """
        Decodifica l'id JSON serializzato: (file_id, engine_name, model_name, chunker_sig)
        e ritorna model_name. In caso di formato non valido, ritorna stringa vuota.
        """
        try:
            _file_id, _engine, model_name, _chunker = json.loads(id_str)
            return model_name
        except Exception:
            return ""

    @staticmethod
    def costruisci_righe(providers: dict) -> list[tuple[str, object, str, str, str, str]]:
        """
        Costruisce le righe per la modale globale dei vector store aggregando TUTTI i provider.

        Ritorna una lista di tuple:
          (provider_name, rag, id_str, collection_name, label, model_name)

        Dove:
          - id_str: stringa JSON dell'identificatore (file_id, engine, model, chunker)
          - collection_name: nome della collection in Chroma
          - label: etichetta utente (basename file), con fallback a collection_name
          - model_name: estratto da id_str
        """
        righe: list[tuple[str, object, str, str, str, str]] = []

        for provider_name, provider in (providers or {}).items():
            # Evita import circolari: trattiamo provider come oggetto "duck-typed"
            rag = getattr(provider, "get_rag", lambda: None)()
            if rag is None:
                continue

            indice = rag.get_indice_collezioni() or {}  # { id_str: {"collection_name": str, "label": str} }

            for id_str, entry in indice.items():
                if isinstance(entry, dict):
                    collection_name = entry.get("collection_name", "") or ""
                    label = entry.get("label", "") or collection_name
                else:
                    # compat con vecchie versioni dell'indice: entry è la collection_name
                    collection_name = str(entry)
                    label = collection_name

                model_name = Rag.estrai_modello_da_id(id_str)
                righe.append((provider_name, rag, id_str, collection_name, label, model_name))

        return righe
