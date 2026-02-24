"""
Adapter per integrare mcp-use con LangChain.
Mantiene i tools MCP in formato asincrono nativo per supportare streaming in tempo reale.
"""

from typing import List, Optional
from langchain_core.tools import BaseTool
from mcp_use import MCPClient
from mcp_use.agents.adapters import LangChainAdapter as MCPUseLangChainAdapter
import logging

logger = logging.getLogger(__name__)


class MCPLangChainAdapter:
    """
    Wrapper per LangChainAdapter di mcp-use.
    Mantiene i tools in formato asincrono nativo per supportare streaming.
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
        Mantiene i tools in formato asincrono nativo.
        
        Args:
            client: Istanza di MCPClient configurato
        """
        await self._adapter.create_all(client)
        
        # Mantieni i tools asincroni nativi (NON convertire in sincroni)
        self._tools = self._adapter.tools
        self._resources = self._adapter.resources
        self._prompts = self._adapter.prompts
        
        # Lista unificata
        self._all_tools = self._tools + self._resources + self._prompts
    
    async def create_tools(self, client: MCPClient) -> None:
        """
        Crea solo i tools dai server MCP attivi.
        
        Args:
            client: Istanza di MCPClient configurato
        """
        await self._adapter.create_tools(client)
        self._tools = self._adapter.tools
    
    async def create_resources(self, client: MCPClient) -> None:
        """
        Crea solo le risorse dai server MCP attivi.
        
        Args:
            client: Istanza di MCPClient configurato
        """
        await self._adapter.create_resources(client)
        self._resources = self._adapter.resources
    
    async def create_prompts(self, client: MCPClient) -> None:
        """
        Crea solo i prompt dai server MCP attivi.
        
        Args:
            client: Istanza di MCPClient configurato
        """
        await self._adapter.create_prompts(client)
        self._prompts = self._adapter.prompts
    
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