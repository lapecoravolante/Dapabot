from langchain_docling import DoclingLoader
from docling.chunking import HybridChunker
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from src.Messaggio import Messaggio
from src.Allegato import Allegato
import os, logging, hashlib, json, shutil, gc, time
from typing import Dict, Tuple

class Rag():
    
    DEFAULT_EMBEDDING_MODEL="sentence-transformers/all-MiniLM-L6-v2"
    DEFAULT_UPLOAD_DIR="uploads/"
    DEFAULT_TOPK=3
    DEFAULT_EMBEDDING_ENGINE=HuggingFaceEmbeddings
    DEFAULT_VECTORSTORE_PATH = "vectorstore_cache/"  # dove vengono persistiti i vector store
    DEFAULT_VECTORSTORE_INDEX_FILE="index.json"
    DEFAULT_VECTORSTORE_INDEX_FILE_PATH = os.path.join(DEFAULT_VECTORSTORE_PATH, DEFAULT_VECTORSTORE_INDEX_FILE)
    AVAILABLE_SEARCH_MODALITIES=["similarity", "mmr"]
    
    # cache dei vectorstore per file già elaborati
    _cache_vectorstores: Dict[Tuple, Chroma] = {}
    # indice su disco della cache dei vectorstore
    _indice_vectorstores: Dict[Tuple, Dict[str, str]] = {}
    
    _pulizia_fatta = False  # esegue la pulizia solo una volta per processo
    
    def __init__(self, attivo=False, modello=None, upload_dir=None, topk=None, 
                 motore_di_embedding=None, tokenizer="", modalita_ricerca="similarity"):
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
        self.init_vectorstore_cache() # inizializza la cache e la directory per la persistenza dei vectorstores
        self.set_modalita_ricerca(modalita_ricerca)

    def to_dict(self):
        return {
            "modello": self._modello,
            "directory_allegati": self._upload_dir,
            "top_k": self._topk,
            "directory_vectorstores": Rag.DEFAULT_VECTORSTORE_PATH,
            "modalita_ricerca": self._modalita_ricerca
        }
        
    # Per ora il rag supporta solo 2 modalità di ricerca: mmr e similarity
    def set_modalita_ricerca(self, modalita_ricerca):
        if modalita_ricerca not in Rag.AVAILABLE_SEARCH_MODALITIES:
            raise ValueError(f"Modalità di ricerca non valida: {modalita_ricerca}")
        self._modalita_ricerca = modalita_ricerca
        
    def get_modalita_ricerca(self):
        return self._modalita_ricerca

    @classmethod
    def _pulizia_orfani(cls) -> None:
        """
        Rimuove le directory orfane dentro Rag.DEFAULT_VECTORSTORE_PATH, cioè quelle 
        che non corrispondono a nessuna 'collection_name' nell'indice JSON.
        Esegue la pulizia una sola volta per processo.
        """
        if cls._pulizia_fatta or not os.path.isdir(cls.DEFAULT_VECTORSTORE_PATH):
            cls._pulizia_fatta=True
            return
        try:
            indice = cls.get_indice()
            # Directory "attese": <persist_dir>/<collection_name>
            attese = set()

            for _, entry in indice.items():
                cn = entry.get("collection_name", "")
                if cn:
                    attese.add(cn)

            # Scansiona solo sottocartelle (non file come chroma.sqlite3)
            for nome in os.listdir(cls.DEFAULT_VECTORSTORE_PATH):
                percorso = os.path.join(cls.DEFAULT_VECTORSTORE_PATH, nome)
                if not os.path.isdir(percorso):
                    continue
                if nome not in attese:
                    try:
                        shutil.rmtree(percorso)
                        logging.info(f"[RAG] Rimossa directory orfana: {percorso}")
                    except Exception as e:
                        logging.warning(f"[RAG] Impossibile rimuovere {percorso}: {e}")

        except Exception as e:
            logging.warning(f"[RAG] Errore pulizia orfani in '{Rag.DEFAULT_VECTORSTORE_PATH}': {e}")
        finally:
            # In ogni caso segna come eseguito per evitare più passaggi
            cls._pulizia_fatta = True

    @classmethod
    def get_indice(cls) -> dict:
        """
        Ritorna l'indice dei vectorstore. Se la cache RAM è vuota (es. dopo rerun Streamlit), ricarica automaticamente da disco.
        """
        if not cls._indice_vectorstores:
            cls._indice_vectorstores = cls.carica_indice_vectorstores() or {}
        return cls._indice_vectorstores

    # crea la directory dove vengono memorizzati i vectorstore
    @classmethod
    def init_vectorstore_cache(cls):
        # Pulizia one-shot delle directory orfane
        cls._pulizia_orfani()
        # se non esiste creo la directory per i vectorstores
        os.makedirs(cls.DEFAULT_VECTORSTORE_PATH, exist_ok=True)
        # inizializzo la cache in RAM
        cls.get_indice()

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
    
    @staticmethod
    def _genera_nome_collezione(vectorstore_id: Tuple) -> str:
        """
        Genera un nome di collection a partire dal vectorstore_id.
        Il parametro "salt" serve per non generare mai lo stesso nome per lo stesso file.
        Il motivo è complesso ed è legato al funzionamento interno di ChromaDB il quale:
        -   mantiene un singleton client;
        -   mantiene connessioni aperte;
        -   mantiene file descriptor su SQLite;
        -   non rilascia mai completamente il lock.
        Perciò quando una collection viene cancellata e poi ricreata per fare ulteriori ricerche RAG succede che:
        -   SQLite trova WAL (Write-Ahead Log) incoerenti;
        -   entra in safe mode;
        -   diventa readonly
        e la creazione del vectorstore per il file va in errore con un messaggio del tipo:
        "Database error: error returned from database: (code: 1032) attempt to write a readonly database"
        Questo succede anche se la directory è stata eliminata correttamente in precedenza.
        """
        salt = time.time_ns()
        return "rag_" + hashlib.sha256(f"{vectorstore_id}-{salt}".encode()).hexdigest()

    def _get_vectorstore(self, vectorstore_id: Tuple, path: str, tipo: str) -> Chroma:
        """
        Recupera (o crea) il vectorstore della collection usando una cartella
        di persistenza dedicata: <persist_dir>/<collection_name>/.
        """
        # Trasforma la tupla "vectorstore_id" in una stringa da usare come chiave sia in RAM sia nell’indice JSON.
        key = json.dumps(vectorstore_id, ensure_ascii=False)

        # 1) Cache RAM
        if key in Rag._cache_vectorstores:
            return Rag._cache_vectorstores[key]

        # 2) Prova dall'indice (collection_name già noto)
        vs = Rag.get_indice().get(key)  # dict {"collection_name": str, "label": str}
        collection_name = vs.get("collection_name") if vs else None
        if collection_name:
            # ✅ cartella dedicata per la collection
            collection_dir = os.path.join(Rag.DEFAULT_VECTORSTORE_PATH, collection_name)
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
            label = vs.get("label", "")
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
                    Rag.get_indice()[key] = {"collection_name": collection_name, "label": label}
                    try:
                        Rag.salva_indice_vectorstores()
                    except Exception as e:
                        logging.warning(f"Non riesco a salvare l'indice con label: {e}")

            return vectorstore

        # 3) Non esiste nell’indice: crea una nuova collection
        splits = self._filtra_metadati_complessi(path, tipo)
        collection_name = self._genera_nome_collezione(vectorstore_id)

        # ✅ cartella dedicata per la collection
        collection_dir = os.path.join(Rag.DEFAULT_VECTORSTORE_PATH, collection_name)
        os.makedirs(collection_dir, exist_ok=True)

        try:
            vectorstore = Chroma.from_documents(
                splits,
                self._motore_di_embedding,
                collection_name=collection_name,
                persist_directory=collection_dir
            )
        except Exception as e:
            raise Exception(f"Errore creazione collection '{collection_name}': {e}")

        Rag._cache_vectorstores[key] = vectorstore

        # Calcolo label utente (basename del file) dai metadati
        label = Rag._estrai_label_da_splits(splits)
        Rag.get_indice()[key] = {"collection_name": collection_name, "label": label}
        try:
            Rag.salva_indice_vectorstores()
        except Exception as e:
            logging.warning(f"Non riesco a salvare l'indice dei vector store: {e}")

        return vectorstore

    #Cancella la collection dal DB Chroma e aggiorna indice/cache.
    @classmethod
    def delete_vectorstore(cls, vectorstore_id_str: str) -> bool:
        entry = cls.get_indice().get(vectorstore_id_str)
        if not entry:
            logging.warning(f"[RAG] delete_vectorstore: id non trovato nell'indice: {vectorstore_id_str}")
            return False
        collection_name = entry.get("collection_name")
        if not collection_name:
            return False
        collection_dir = os.path.join(cls.DEFAULT_VECTORSTORE_PATH, collection_name)
        try:
            # 1) Rimuove il vectorstore dalla cache in RAM
            vectorstore = cls._cache_vectorstores.pop(vectorstore_id_str, None)
            if vectorstore is not None:
                del vectorstore
                gc.collect()

            # 2) Apre un client "pulito" solo per il delete logico
            vectorstore = Chroma(
                collection_name=collection_name,
                persist_directory=collection_dir,
            )

            client = getattr(vectorstore, "_client", None)
            if client is None:
                raise RuntimeError("Client interno Chroma non disponibile.")

            # Cancellazione logica sul DB
            client.delete_collection(name=collection_name)
            # 3) Distruggi TUTTO
            del client
            del vectorstore
            gc.collect()
            # 4) Cancello anche dal disco
            shutil.rmtree(collection_dir, ignore_errors=False)
            # 5) Aggiorna indice
            cls.get_indice().pop(vectorstore_id_str, None)            
        except Exception as e:
            logging.warning(f"Errore cancellazione collection '{collection_name}': {e}")
        try:
            cls.salva_indice_vectorstores()
        except Exception as e:
            logging.warning(f"Non riesco a salvare l'indice dopo delete: {e}")
        return True
    
    @staticmethod
    def _estrai_label_da_splits(splits) -> str:
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
            key = (doc.metadata.get("source"), doc.metadata.get("page"), content)
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
    @classmethod
    def carica_indice_vectorstores(cls):
        """
        Carica l'indice dei vector store. Ritorna un dict:
            { vectorstore_id_str: { "collection_name": str, "label": str } }
        """
        if os.path.exists(cls.DEFAULT_VECTORSTORE_INDEX_FILE_PATH):
            try:
                data = {}
                with open(cls.DEFAULT_VECTORSTORE_INDEX_FILE_PATH, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                for k, v in raw.items():
                    data[k] = {"collection_name": v.get("collection_name", ""), "label": v.get("label", "")}
                return data
            except Exception:
                return {}
        return {}

    # funzione che salva i vectorstore su file
    @classmethod
    def salva_indice_vectorstores(cls):
        """
        Salva su disco l'indice dei vector store:
            { vectorstore_id_str: { "collection_name": str, "label": str } }
        """
        try:
            with open(cls.DEFAULT_VECTORSTORE_INDEX_FILE_PATH, "w", encoding="utf-8") as f:
                json.dump(cls._indice_vectorstores, f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise Exception(f"Errore salvataggio indice Chroma: {e}")

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

        return righe

    @staticmethod
    def costruisci_righe() -> list[tuple[str, str, str, str]]:
        """
        Ritorna una lista di tuple:
        (id_str, collection_name, label, model_name)
        """
        righe = []
        indice = Rag.get_indice()  # { id_str: {"collection_name": str, "label": str} }

        for id_str, entry in indice.items():
            collection_name = entry.get("collection_name", "")
            label = entry.get("label", "") or collection_name
            model_name = Rag.estrai_modello_da_id(id_str)
            righe.append((id_str, collection_name, label, model_name))

        return righe
