"""
Modulo per il supporto ai server MCP (Model Context Protocol)
<<<<<<< HEAD
Utilizza langchain-mcp-adapters per l'integrazione con LangChain
"""

from .client import MCPClientManager, get_mcp_client_manager

__all__ = ['MCPClientManager', 'get_mcp_client_manager']
=======
Utilizza mcp-use per l'integrazione unificata di tools, risorse e prompt
"""

from .client import MCPClientManager, get_mcp_client_manager
from .gui_mcp_discovery import (
    mostra_dialog_mcp_discovery,
    mostra_quick_access_button,
    get_selected_mcp_resources,
    get_selected_mcp_prompt,
    clear_mcp_selection
)

__all__ = [
    'MCPClientManager',
    'get_mcp_client_manager',
    'mostra_dialog_mcp_discovery',
    'mostra_quick_access_button',
    'get_selected_mcp_resources',
    'get_selected_mcp_prompt',
    'clear_mcp_selection'
]
>>>>>>> dev

# Made with Bob
