"""
Adapter per integrare mcp-use con LangChain.
Converte tools, risorse e prompt MCP in formato LangChain compatibile.
"""

from typing import List, Optional
import asyncio
from functools import wraps
from langchain_core.tools import BaseTool, StructuredTool
from mcp_use import MCPClient
from mcp_use.agents.adapters import LangChainAdapter as MCPUseLangChainAdapter


def async_to_sync_tool(async_tool: BaseTool) -> BaseTool:
    """
    Converte un tool async in un tool sincrono wrappando la funzione.
    Necessario perché mcp-use ritorna tools async ma LangChain agents
    nel progetto li usa in modo sincrono.
    
    Args:
        async_tool: Tool async da convertire
        
    Returns:
        Tool sincrono equivalente
    """
    if not hasattr(async_tool, 'coroutine'):
        # Tool già sincrono
        return async_tool
    
    # Wrapper sincrono per la coroutine
    @wraps(async_tool.coroutine)
    def sync_wrapper(*args, **kwargs):
        return asyncio.run(async_tool.coroutine(*args, **kwargs))
    
    # Crea un nuovo StructuredTool sincrono
    return StructuredTool(
        name=async_tool.name,
        description=async_tool.description,
        func=sync_wrapper,
        args_schema=async_tool.args_schema if hasattr(async_tool, 'args_schema') else None
    )


class MCPLangChainAdapter:
    """
    Wrapper per LangChainAdapter di mcp-use.
    Gestisce la conversione di tools, risorse e prompt MCP in formato LangChain.
    """
    
    def __init__(self, disallowed_tools: Optional[List[str]] = None):
        """
        Inizializza l'adapter.
        
        Args:
            disallowed_tools: Lista di nomi di tools/risorse/prompt da escludere
        """
        self._adapter = MCPUseLangChainAdapter(disallowed_tools=disallowed_tools or [])
        self._tools: List[BaseTool] = []
        self._resources: List[BaseTool] = []
        self._prompts: List[BaseTool] = []
        self._all_tools: List[BaseTool] = []
    
    async def create_all(self, client: MCPClient) -> None:
        """
        Crea tutti i tools, risorse e prompt dai server MCP attivi.
        
        Args:
            client: Istanza di MCPClient configurato
        """
        await self._adapter.create_all(client)
        
        # Converti tutti i tools async in sincroni
        self._tools = [async_to_sync_tool(tool) for tool in self._adapter.tools]
        self._resources = [async_to_sync_tool(tool) for tool in self._adapter.resources]
        self._prompts = [async_to_sync_tool(tool) for tool in self._adapter.prompts]
        
        # Lista unificata
        self._all_tools = self._tools + self._resources + self._prompts
    
    async def create_tools(self, client: MCPClient) -> None:
        """
        Crea solo i tools dai server MCP attivi.
        
        Args:
            client: Istanza di MCPClient configurato
        """
        await self._adapter.create_tools(client)
        self._tools = [async_to_sync_tool(tool) for tool in self._adapter.tools]
    
    async def create_resources(self, client: MCPClient) -> None:
        """
        Crea solo le risorse dai server MCP attivi.
        
        Args:
            client: Istanza di MCPClient configurato
        """
        await self._adapter.create_resources(client)
        self._resources = [async_to_sync_tool(tool) for tool in self._adapter.resources]
    
    async def create_prompts(self, client: MCPClient) -> None:
        """
        Crea solo i prompt dai server MCP attivi.
        
        Args:
            client: Istanza di MCPClient configurato
        """
        await self._adapter.create_prompts(client)
        self._prompts = [async_to_sync_tool(tool) for tool in self._adapter.prompts]
    
    @property
    def tools(self) -> List[BaseTool]:
        """Ritorna la lista dei tools convertiti"""
        return self._tools
    
    @property
    def resources(self) -> List[BaseTool]:
        """Ritorna la lista delle risorse convertite"""
        return self._resources
    
    @property
    def prompts(self) -> List[BaseTool]:
        """Ritorna la lista dei prompt convertiti"""
        return self._prompts
    
    @property
    def all_tools(self) -> List[BaseTool]:
        """Ritorna la lista unificata di tools, risorse e prompt"""
        return self._all_tools
    
    def get_tools_count(self) -> int:
        """Ritorna il numero di tools"""
        return len(self._tools)
    
    def get_resources_count(self) -> int:
        """Ritorna il numero di risorse"""
        return len(self._resources)
    
    def get_prompts_count(self) -> int:
        """Ritorna il numero di prompt"""
        return len(self._prompts)
    
    def get_total_count(self) -> int:
        """Ritorna il numero totale di elementi"""
        return len(self._all_tools)


# Made with Bob