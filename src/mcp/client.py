"""
Client MCP semplificato usando langchain-mcp-adapters
"""

from typing import Dict, Any, List, Optional
import asyncio
from functools import wraps
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.tools import BaseTool, StructuredTool
from src.ConfigurazioneDB import ConfigurazioneDB


def async_to_sync_tool(async_tool: BaseTool) -> BaseTool:
    """
    Converte un tool async in un tool sincrono wrappando la funzione.
    Necessario perché langchain-mcp-adapters ritorna tools async.
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


class MCPClientManager:
    """
    Gestisce i client MCP usando langchain-mcp-adapters.
    Fornisce un'interfaccia semplificata per caricare configurazioni dal database
    e ottenere tools per gli agenti LangChain.
    """
    
    def __init__(self):
        """Inizializza il manager"""
        self._client: Optional[MultiServerMCPClient] = None
        self._server_configs: Dict[str, Dict[str, Any]] = {}
        self._tools_cache: List[BaseTool] = []
        self._config_hash: Optional[str] = None
        # Traccia le configurazioni precedenti per ogni server
        self._previous_server_configs: Dict[str, Dict[str, Any]] = {}
    
    def _config_changed(self, server_name: str, new_config: Dict[str, Any]) -> bool:
        """
        Verifica se la configurazione di un server è cambiata rispetto alla precedente.
        
        Args:
            server_name: Nome del server
            new_config: Nuova configurazione
            
        Returns:
            True se la configurazione è cambiata, False altrimenti
        """
        import json
        
        # Se non abbiamo una configurazione precedente, è cambiata
        if server_name not in self._previous_server_configs:
            return True
        
        old_config = self._previous_server_configs[server_name]
        
        # Confronta le configurazioni serializzandole in JSON
        # Questo gestisce correttamente liste, dizionari, ecc.
        old_json = json.dumps(old_config, sort_keys=True)
        new_json = json.dumps(new_config, sort_keys=True)
        
        return old_json != new_json
    
    def carica_configurazioni_da_db(self) -> None:
        """
        Carica le configurazioni dei server MCP attivi dal database
        e le prepara per MultiServerMCPClient.
        """
        servers_attivi = ConfigurazioneDB.carica_mcp_servers_attivi()
        
        self._server_configs = {}
        
        for server in servers_attivi:
            nome = server['nome']
            tipo = server['tipo']
            config = server['configurazione']
            
            if tipo == 'local':
                # Configurazione per server locale (stdio)
                self._server_configs[nome] = {
                    'transport': 'stdio',
                    'command': config.get('comando', ''),
                    'args': config.get('args', []),
                    'env': config.get('env', {})
                }
            elif tipo == 'remote':
                # Configurazione per server remoto (HTTP)
                server_config = {
                    'transport': 'http',
                    'url': config.get('url', '')
                }
                
                # Aggiungi headers se presenti
                headers = config.get('headers', {})
                if config.get('api_key'):
                    headers['Authorization'] = f"Bearer {config['api_key']}"
                
                if headers:
                    server_config['headers'] = headers
                
                self._server_configs[nome] = server_config
    
    def get_client(self) -> MultiServerMCPClient:
        """
        Ottiene o crea il client MCP con le configurazioni caricate.
        
        Returns:
            Istanza di MultiServerMCPClient
        """
        if not self._server_configs:
            self.carica_configurazioni_da_db()
        
        if self._client is None:
            self._client = MultiServerMCPClient(self._server_configs)
            # Salva le configurazioni correnti come baseline per futuri confronti
            import copy
            self._previous_server_configs = copy.deepcopy(self._server_configs)
        
        return self._client
    
    async def get_tools(self) -> List[BaseTool]:
        """
        Ottiene tutti i tools dai server MCP configurati.
        Converte i tools async in sincroni per compatibilità con LangChain.
        Usa caching per evitare di ricreare i tools ad ogni chiamata.
        
        Returns:
            Lista di tools LangChain sincroni pronti per l'uso con gli agenti
        """
        # Calcola hash della configurazione per invalidare cache se cambia
        import hashlib
        import json
        config_str = json.dumps(self._server_configs, sort_keys=True)
        current_hash = hashlib.md5(config_str.encode()).hexdigest()
        
        # Se la configurazione non è cambiata e abbiamo una cache, usala
        if self._config_hash == current_hash and self._tools_cache:
            return self._tools_cache
        
        # Altrimenti ricarica i tools
        client = self.get_client()
        async_tools = await client.get_tools()
        
        # Converti tutti i tools async in sincroni
        sync_tools = [async_to_sync_tool(tool) for tool in async_tools]
        
        # Aggiorna cache
        self._tools_cache = sync_tools
        self._config_hash = current_hash
        
        return sync_tools
    
    async def get_resources(self, server_name: str, uris: Optional[List[str]] = None) -> List[Any]:
        """
        Ottiene le risorse da un server MCP specifico.
        
        Args:
            server_name: Nome del server MCP
            uris: Lista opzionale di URI specifici da caricare
            
        Returns:
            Lista di Blob objects con le risorse
        """
        client = self.get_client()
        return await client.get_resources(server_name, uris=uris)
    
    async def get_prompt(self, server_name: str, prompt_name: str, 
                        arguments: Optional[Dict[str, Any]] = None) -> List[Any]:
        """
        Ottiene un prompt da un server MCP specifico.
        
        Args:
            server_name: Nome del server MCP
            prompt_name: Nome del prompt
            arguments: Argomenti opzionali per il prompt
            
        Returns:
            Lista di messaggi LangChain
        """
        client = self.get_client()
        return await client.get_prompt(server_name, prompt_name, arguments=arguments)
    
    def reset(self) -> None:
        """
        Resetta il client e ricarica le configurazioni.
        Riavvia solo i server la cui configurazione è cambiata.
        """
        # Carica le nuove configurazioni dal database
        self.carica_configurazioni_da_db()
        
        # Determina quali server devono essere riavviati
        servers_to_restart = set()
        
        # Controlla i server attualmente configurati
        for server_name, new_config in self._server_configs.items():
            if self._config_changed(server_name, new_config):
                servers_to_restart.add(server_name)
        
        # Controlla i server che sono stati rimossi
        for server_name in self._previous_server_configs.keys():
            if server_name not in self._server_configs:
                servers_to_restart.add(server_name)
        
        # Se ci sono server da riavviare, resetta il client
        if servers_to_restart:
            self._client = None
            self._tools_cache = []
            self._config_hash = None
            
            # Aggiorna le configurazioni precedenti
            import copy
            self._previous_server_configs = copy.deepcopy(self._server_configs)
        # Altrimenti, mantieni il client esistente (nessun riavvio necessario)
    
    def get_server_names(self) -> List[str]:
        """
        Ottiene i nomi di tutti i server configurati.
        
        Returns:
            Lista di nomi dei server
        """
        if not self._server_configs:
            self.carica_configurazioni_da_db()
        return list(self._server_configs.keys())


# Istanza singleton globale
_mcp_client_manager = None


def get_mcp_client_manager() -> MCPClientManager:
    """
    Ottiene l'istanza singleton del manager MCP.
    
    Returns:
        Istanza di MCPClientManager
    """
    global _mcp_client_manager
    if _mcp_client_manager is None:
        _mcp_client_manager = MCPClientManager()
    return _mcp_client_manager


# Made with Bob