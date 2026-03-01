from src.tools.Tool import Tool
from langchain_community.agent_toolkits import FileManagementToolkit

class Filesystem(Tool):

    def __init__(self) -> None:
        # I parametri iniziali vengono impostati dalla classe base come attributi dell'oggetto
        super().__init__(
            nome="Filesystem",
            pacchetti_python_necessari={
                "langchain-community": "langchain_community"
            },
            parametri_iniziali={
                "root_dir": "",
                "selected_tools": [
                    "copy_file",
                    "file_delete",
                    "file_search",
                    "move_file",
                    "read_file",
                    "write_file",
                    "list_directory"
                ]
            }
        )
        
        # Descrizioni per i parametri nella GUI
        self._param_descriptions = {
            "root_dir": "Directory radice per le operazioni sui file (lasciare vuoto per usare la directory corrente)",
            "selected_tools": "Lista dei tool da abilitare (seleziona uno o più tool)"
        }
        
        # Opzioni disponibili per selected_tools (nomi corretti da FileManagementToolkit)
        self._param_options = {
            "selected_tools": [
                "copy_file",
                "file_delete",
                "file_search",
                "move_file",
                "read_file",
                "write_file",
                "list_directory"
            ]
        }

    def get_tool(self):
        return FileManagementToolkit(root_dir=self.root_dir, selected_tools=self.selected_tools).get_tools()