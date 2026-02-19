"""
Modulo per il supporto ai server MCP (Model Context Protocol)
Utilizza langchain-mcp-adapters per l'integrazione con LangChain
"""

from .client import MCPClientManager, get_mcp_client_manager
from .gui_mcp import mostra_gestione_mcp

__all__ = ['MCPClientManager', 'get_mcp_client_manager', 'mostra_gestione_mcp']

# Made with Bob
