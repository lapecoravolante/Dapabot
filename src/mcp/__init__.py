"""
Modulo per il supporto ai server MCP (Model Context Protocol)
Utilizza langchain-mcp-adapters per l'integrazione con LangChain
e SDK nativo MCP per discovery di risorse e prompt
"""

from .client import MCPClientManager, get_mcp_client_manager
from .gui_mcp_discovery import (
    mostra_dialog_mcp_discovery,
    mostra_quick_access_buttons,
    get_selected_mcp_resources,
    get_selected_mcp_prompt,
    clear_mcp_selection
)

__all__ = [
    'MCPClientManager',
    'get_mcp_client_manager',
    'mostra_dialog_mcp_discovery',
    'mostra_quick_access_buttons',
    'get_selected_mcp_resources',
    'get_selected_mcp_prompt',
    'clear_mcp_selection'
]

# Made with Bob
