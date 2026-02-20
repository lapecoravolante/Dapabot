"""
Modulo per il supporto ai server MCP (Model Context Protocol)
Utilizza langchain-mcp-adapters per l'integrazione con LangChain
"""

from .client import MCPClientManager, get_mcp_client_manager

__all__ = ['MCPClientManager', 'get_mcp_client_manager']

# Made with Bob
