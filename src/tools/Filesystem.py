from src.tools.Tool import Tool
from typing import List
from langchain_community.agent_toolkits import FileManagementToolkit

class Filesystem(Tool):

    def __init__(self) -> None:
        super().__init__(nome="Filesystem", 
                        pacchetti_pytthon_necessari=["langchain-community"])
        # Di seguito i parametri configurabili del tool
        self.root_dir: str =""
        self.selected_tools: List[str] = []

    def get_tool(self):
        return FileManagementToolkit(root_dir=self.root_dir, selected_tools=self.selected_tools).get_tools()