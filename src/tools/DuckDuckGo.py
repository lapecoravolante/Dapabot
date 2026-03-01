from src.tools.Tool import Tool
from langchain_community.tools import DuckDuckGoSearchRun

class DuckDuckGo(Tool):

    def __init__(self) -> None:
        # I parametri iniziali vengono impostati dalla classe base come attributi dell'oggetto
        super().__init__(
            nome="DuckDuckGo",
            pacchetti_python_necessari={
                "langchain-community": "langchain_community",
                "ddgs": "ddgs"
            },
            parametri_iniziali={
                "max_results": 5,
                "region": "wt-wt",
                "safesearch": "moderate",
                "time": "y",
                "backend": "auto",
                "source": "text"
            }
        )
        
        # Metadati per i parametri con valori specifici (per la GUI)
        self._param_options = {
            "safesearch": ["strict", "moderate", "off"],
            "time": ["d", "w", "m", "y"],
            "backend": ["auto", "html", "lite"],
            "source": ["text", "news", "images"]
        }
        
        # Descrizioni dei parametri per la GUI
        self._param_descriptions = {
            "max_results": "Numero massimo di risultati da restituire",
            "region": "Regione per i risultati (es: wt-wt, it-it, us-en)",
            "safesearch": "Livello di sicurezza: strict (rigoroso), moderate (moderato), off (disattivato)",
            "time": "Periodo temporale: d (giorno), w (settimana), m (mese), y (anno)",
            "backend": "Backend da utilizzare: auto (automatico), html, lite",
            "source": "Tipo di ricerca: text (testo), news (notizie), images (immagini)"
        }

    def get_tool(self):
        """
        Crea e ritorna il tool DuckDuckGo Search configurato.
        
        Returns:
            Lista contenente un'istanza di DuckDuckGoSearchRun
        """
        # Crea il tool DuckDuckGo con i parametri configurati
        search_tool = DuckDuckGoSearchRun(
            name="duckduckgo_search",
            description="Cerca informazioni su internet usando DuckDuckGo. Utile per trovare informazioni aggiornate, notizie, articoli e contenuti web generici.",
            max_results=self.max_results,
            region=self.region,
            safesearch=self.safesearch,
            time=self.time,
            backend=self.backend
        )
        
        return [search_tool]