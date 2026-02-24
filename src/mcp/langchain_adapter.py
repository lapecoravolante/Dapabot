"""
Adapter per integrare mcp-use con LangChain.
Converte tools, risorse e prompt MCP in formato LangChain compatibile.
"""

from typing import List, Optional, Any
import asyncio
import inspect
from langchain_core.tools import BaseTool, StructuredTool
from mcp_use import MCPClient
from mcp_use.agents.adapters import LangChainAdapter as MCPUseLangChainAdapter
import logging

logger = logging.getLogger(__name__)


def async_to_sync_tool(async_tool: BaseTool) -> BaseTool:
    """
    Converte un tool async in un tool sincrono wrappando la funzione.
    I tools di mcp-use hanno un metodo arun() async che deve essere wrappato.
    """
    # Trova il metodo async corretto
    original_func = None
    is_bound_method = False
    
    # Strategia 1: func attribute
    if hasattr(async_tool, 'func') and callable(async_tool.func) and inspect.iscoroutinefunction(async_tool.func):
        original_func = async_tool.func
        is_bound_method = False
    # Strategia 2: coroutine attribute
    elif hasattr(async_tool, 'coroutine') and callable(async_tool.coroutine):
        original_func = async_tool.coroutine
        is_bound_method = False
    # Strategia 3: _run method
    elif hasattr(async_tool, '_run') and inspect.iscoroutinefunction(async_tool._run):
        original_func = async_tool._run
        is_bound_method = True
    # Strategia 4: arun method (caso più comune per mcp-use)
    elif hasattr(async_tool, 'arun') and inspect.iscoroutinefunction(async_tool.arun):
        original_func = async_tool.arun
        is_bound_method = True
    else:
        logger.warning(f"Tool {async_tool.name}: nessun metodo async trovato, ritorno il tool originale")
        return async_tool
    
    # Crea wrapper sincrono
    def sync_wrapper(tool_input: Any = None, **kwargs: Any) -> Any:
        """Wrapper sincrono che esegue la funzione async"""
        # Prepara gli argomenti
        if is_bound_method:
            # Per metodi bound (arun, _run), passa tool_input direttamente
            if tool_input is None and kwargs:
                # Se abbiamo solo kwargs, usali come tool_input
                call_args = (kwargs,)
            elif isinstance(tool_input, dict):
                call_args = (tool_input,)
            else:
                call_args = (tool_input,) if tool_input is not None else ({},)
        else:
            # Per funzioni non bound (func, coroutine), usa **kwargs
            if tool_input is None and kwargs:
                call_args = ()
                call_kwargs = kwargs
            elif isinstance(tool_input, dict):
                call_args = ()
                call_kwargs = tool_input
            else:
                call_args = ()
                call_kwargs = {"input": tool_input} if tool_input is not None else {}
        
        # Esegui la coroutine
        try:
            loop = asyncio.get_running_loop()
            # Loop già in esecuzione: usa ThreadPoolExecutor
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                if is_bound_method:
                    future = executor.submit(asyncio.run, original_func(*call_args))
                else:
                    future = executor.submit(asyncio.run, original_func(**call_kwargs))
                return future.result()
        except RuntimeError:
            # Nessun loop in esecuzione: usa asyncio.run
            if is_bound_method:
                return asyncio.run(original_func(*call_args))
            else:
                return asyncio.run(original_func(**call_kwargs))
    
    # Crea un nuovo StructuredTool con il wrapper sincrono
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