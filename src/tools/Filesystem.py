from src.tools.Tool import Tool
from typing import List
from langchain_community.agent_toolkits import FileManagementToolkit

class Filesystem(Tool):

    def __init__(self) -> None:
        # I parametri iniziali vengono impostati dalla classe base come attributi dell'oggetto
        super().__init__(
            nome="Filesystem",
            pacchetti_pytthon_necessari=["langchain-community"],
            parametri_iniziali={
                "root_dir": "",
                "selected_tools": [tool.name for tool in FileManagementToolkit().get_tools()]
            }
        )

    def get_tool(self):
        return FileManagementToolkit(root_dir=self.root_dir, selected_tools=self.selected_tools).get_tools()