from src.tools.Tool import Tool
from langchain_community.utilities import WikipediaAPIWrapper
from langchain_community.tools.wikipedia.tool import WikipediaQueryRun

class Wikipedia(Tool):

    def __init__(self) -> None:
        # I parametri iniziali vengono impostati dalla classe base come attributi dell'oggetto
        super().__init__(
            nome="Wikipedia",
            pacchetti_python_necessari={
                "langchain-community": "langchain_community",
                "wikipedia":"wikipedia"
            },
            parametri_iniziali={
                "lang": "it",
                "top_k_results": 3,
                "load_all_available_meta": False,
                "doc_content_chars_max": 4000
            }
        )

    def get_tool(self):
        # Crea il wrapper Arxiv con i parametri configurati
        wiki_wrapper = WikipediaAPIWrapper(
            top_k_results=self.top_k_results,
            lang=self.lang,
            load_all_available_meta=self.load_all_available_meta,
            doc_content_chars_max=self.doc_content_chars_max
        )
        # Crea il tool usando la classe ArxivQueryRun
        return [WikipediaQueryRun(api_wrapper=wiki_wrapper)]
        