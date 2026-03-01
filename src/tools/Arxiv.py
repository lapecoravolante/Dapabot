from src.tools.Tool import Tool
from langchain_community.tools.arxiv.tool import ArxivQueryRun
from langchain_community.utilities import ArxivAPIWrapper

class Arxiv(Tool):

    def __init__(self) -> None:
        super().__init__(
            nome="Arxiv",
            pacchetti_python_necessari={
                "langchain-community": "langchain_community",
                "arxiv": "arxiv"
            },
            parametri_iniziali={
                "top_k_results": 3,
                "ARXIV_MAX_QUERY_LENGTH": 300,
                "continue_on_failure": False,
                "load_max_docs": 100,
                "load_all_available_meta": False,
                "doc_content_chars_max": 4000
            }
        )
        
        # Descrizioni per i parametri nella GUI
        self._param_descriptions = {
            "top_k_results": "Numero di risultati top-scored da restituire",
            "ARXIV_MAX_QUERY_LENGTH": "Lunghezza massima della query (caratteri)",
            "continue_on_failure": "Se True, continua il caricamento anche in caso di errori",
            "load_max_docs": "Numero massimo di documenti da caricare",
            "load_all_available_meta": "Se True, carica tutti i metadati disponibili; se False, solo data, titolo, autori e sommario",
            "doc_content_chars_max": "Lunghezza massima del contenuto del documento (caratteri)"
        }

    def get_tool(self):
        # Crea il wrapper Arxiv con i parametri configurati
        arxiv_wrapper = ArxivAPIWrapper(
            top_k_results=self.top_k_results,
            ARXIV_MAX_QUERY_LENGTH=self.ARXIV_MAX_QUERY_LENGTH,
            continue_on_failure=self.continue_on_failure,
            load_max_docs=self.load_max_docs,
            load_all_available_meta=self.load_all_available_meta,
            doc_content_chars_max=self.doc_content_chars_max
        )
        # Crea il tool usando la classe ArxivQueryRun
        arxiv_tool = ArxivQueryRun(api_wrapper=arxiv_wrapper)
        return [arxiv_tool]