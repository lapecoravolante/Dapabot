from src.tools.Tool import Tool
from langchain_community.utilities import ArxivAPIWrapper

class Arxiv(Tool):

    def __init__(self) -> None:
        super().__init__(nome="Arxiv", 
                        pacchetti_pytthon_necessari=["langchain-community", "arxiv"])

    def get_tool(self):
        return [ArxivAPIWrapper(),]