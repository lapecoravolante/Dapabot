from langchain_docling import DoclingLoader
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from Provider import Provider
from Messaggio import Messaggio
from Allegato import Allegato
import os, uuid

# questa classe memorizza il prompt utente e fa le ricerche RAG sugli allegati.
# Restituisce i top-k risultati all'utente.
class Rag():
    
    EMBED_MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
    
    _cache_vectorstores = {}  # cache dei vectorstore per file già elaborati
    
    '''
    Argomenti
    - prompt: il testo del prompt scritto dall'utente
    - modello: il provider scelto nella schermata principale (providers_disponibili[provider_scelto]) 
    '''
    def __init__(self, prompt: Messaggio, modello: Provider):
        self.set_modello(modello)
        self._prompt=prompt
    
    def set_modello(self, modello):
        if not modello:
            raise Exception("Impostare il modello e l'api key per il RAG!")
        self._modello=modello 
    
    def _filtra_metadati_complessi(self, save_path):
        clean_splits = []
        loader = DoclingLoader(file_path=save_path)
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
        return  clean_splits
    
    def _get_vectorstore(self, save_path):
        """Recupera un vectorstore dalla cache o lo crea se non esiste"""
        if save_path in Rag._cache_vectorstores:
            return Rag._cache_vectorstores[save_path]

        splits = self._filtra_metadati_complessi(save_path)

        vectorstore = Chroma.from_documents(
            documents=splits,
            embedding=HuggingFaceEmbeddings(model_name=Rag.EMBED_MODEL_ID),
            collection_name=f"rag_{uuid.uuid4().hex}"  # collection unica temporanea
        )

        # Salva nella cache per riutilizzo futuro
        Rag._cache_vectorstores[save_path] = vectorstore
        return vectorstore
    
    def __call__(self):
        """Esegue il RAG e restituisce i top-k risultati per ciascun allegato"""
        risultato = []
        try:
            os.makedirs("uploads/", exist_ok=True)
            for f in self._prompt.get_allegati():
                save_path = os.path.join("uploads/", f.name)
                with open(save_path, "wb") as out:
                    out.write(f.getbuffer())
                # Recupera il vectorstore (dalla cache se già esiste)
                vectorstore = self._get_vectorstore(save_path)
                # Recupera i top-3 chunk più rilevanti
                top_docs = vectorstore.similarity_search(self._prompt.get_testo(), k=3)
                risultato.append(Allegato(tipo="text",contenuto="\r\n".join(doc.page_content for doc in top_docs),mime_type="text"))
            return risultato
        except Exception as e:
            raise Exception(f"Errore in fase RAG: {e}")