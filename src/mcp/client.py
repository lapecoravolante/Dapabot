"""
Client MCP semplificato usando langchain-mcp-adapters per i tools
e SDK nativo MCP per discovery di risorse e prompt
"""

from typing import Dict, Any, List, Optional, Tuple
import asyncio
import threading
from functools import wraps
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.tools import BaseTool, StructuredTool
from src.ConfigurazioneDB import ConfigurazioneDB

# Import SDK nativo MCP per discovery
from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.sse import sse_client
import httpx


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
        # Stato del riavvio in background
        self._restart_in_progress: bool = False
        self._restart_thread: Optional[threading.Thread] = None
        # Cache per discovery di risorse e prompt (SDK nativo)
        self._resources_cache: Dict[str, List[Dict[str, Any]]] = {}
        self._prompts_cache: Dict[str, List[Dict[str, Any]]] = {}
        self._discovery_cache_hash: Optional[str] = None
    
    def carica_configurazioni_da_db(self) -> None:
        """
        Carica le configurazioni dei server MCP attivi dal database
        e le prepara per MultiServerMCPClient.
        NON resetta il client se le configurazioni non sono cambiate.
        """
        servers_attivi = ConfigurazioneDB.carica_mcp_servers_attivi()
        
        # Costruisci le nuove configurazioni
        new_server_configs = {}
        
        for server in servers_attivi:
            nome = server['nome']
            tipo = server['tipo']
            config = server['configurazione']
            
            if tipo == 'local':
                # Configurazione per server locale (stdio)
                new_server_configs[nome] = {
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
                
                new_server_configs[nome] = server_config
        
        # Confronta con le configurazioni esistenti
        import json
        old_config_json = json.dumps(self._server_configs, sort_keys=True)
        new_config_json = json.dumps(new_server_configs, sort_keys=True)
        
        # Aggiorna solo se le configurazioni sono cambiate
        if old_config_json != new_config_json:
            self._server_configs = new_server_configs
            # Resetta il client per forzare la riconnessione con le nuove configurazioni
            self._client = None
            self._tools_cache = []
            self._config_hash = None
            # Invalida anche la cache di discovery
            self.invalidate_discovery_cache()
    
    def get_client(self) -> MultiServerMCPClient:
        """
        Ottiene o crea il client MCP con le configurazioni caricate.
        Se un riavvio è in corso, aspetta che finisca prima di restituire il client.
        
        Returns:
            Istanza di MultiServerMCPClient
        """
        # Se un riavvio è in corso, aspetta che finisca
        if self._restart_in_progress and self._restart_thread:
            self._restart_thread.join(timeout=5.0)
        
        if not self._server_configs:
            self.carica_configurazioni_da_db()
        
        if self._client is None:
            self._client = MultiServerMCPClient(self._server_configs)
        
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
    
    def _do_restart(self) -> None:
        """
        Esegue il riavvio effettivo del client in background.
        Questo metodo viene eseguito in un thread separato.
        """
        try:
            # Resetta il client
            self._client = None
            self._tools_cache = []
            self._config_hash = None
            # Invalida anche la cache di discovery
            self.invalidate_discovery_cache()
        finally:
            # Marca il riavvio come completato
            self._restart_in_progress = False
    
    def reset(self) -> None:
        """
        Resetta il client e ricarica le configurazioni.
        Il riavvio avviene in background per non bloccare la GUI.
        
        Nota: Questo metodo viene chiamato solo quando serve effettivamente un riavvio,
        perché il confronto delle configurazioni avviene in ConfigurazioneDB.salva_mcp_server().
        """
        # Carica i server attivi correnti
        self.carica_configurazioni_da_db()
        
        # Se c'è già un riavvio in corso, aspetta che finisca
        if self._restart_in_progress and self._restart_thread:
            self._restart_thread.join(timeout=1.0)
        
        # Marca il riavvio come in corso
        self._restart_in_progress = True
        
        # Avvia il riavvio in un thread separato
        self._restart_thread = threading.Thread(
            target=self._do_restart,
            daemon=True,
            name="MCP-Restart"
        )
        self._restart_thread.start()
    
    def is_restart_in_progress(self) -> bool:
        """
        Verifica se un riavvio è in corso.
        
        Returns:
            True se un riavvio è in corso, False altrimenti
        """
        return self._restart_in_progress
    
    def get_server_names(self) -> List[str]:
        """
        Ottiene i nomi di tutti i server configurati.
        
        Returns:
            Lista di nomi dei server
        """
        if not self._server_configs:
            self.carica_configurazioni_da_db()
        return list(self._server_configs.keys())
    
    def salva_mcp_server(self, nome: str, tipo: str, descrizione: str = "",
                         configurazione: Optional[dict] = None, attivo: bool = True) -> None:
        """
        Salva o aggiorna la configurazione di un server MCP nel database.
        Se la configurazione cambia, forza il ricaricamento del client.
        
        Args:
            nome: Nome identificativo del server
            tipo: Tipo di server ('local' o 'remote')
            descrizione: Descrizione del server
            configurazione: Dizionario con la configurazione specifica
            attivo: Se il server è attivo o meno
        """
        # Salva nel database
        config_changed = ConfigurazioneDB.salva_mcp_server(
            nome=nome,
            tipo=tipo,
            descrizione=descrizione,
            configurazione=configurazione or {},
            attivo=attivo
        )
        
        # Se la configurazione è cambiata, forza il ricaricamento
        if config_changed:
            self.carica_configurazioni_da_db()
    
    def cancella_mcp_server(self, nome: str) -> None:
        """
        Cancella un server MCP dal database e forza il ricaricamento del client.
        
        Args:
            nome: Nome del server da cancellare
        """
        # Cancella dal database
        ConfigurazioneDB.cancella_mcp_server(nome)
        
        # Forza il ricaricamento delle configurazioni
        self.carica_configurazioni_da_db()
    
    async def _create_native_session(self, server_name: str) -> Optional[Tuple[ClientSession, Any]]:
        """
        Crea una sessione nativa MCP per un server specifico.
        Supporta sia server locali (stdio) che remoti (HTTP).
        
        Args:
            server_name: Nome del server MCP
            
        Returns:
            Tupla (ClientSession, context_manager) o None se il server non esiste
        """
        if server_name not in self._server_configs:
            return None
        
        config = self._server_configs[server_name]
        transport = config.get('transport', 'stdio')
        
        if transport == 'stdio':
            # Server locale con stdio
            server_params = StdioServerParameters(
                command=config.get('command', ''),
                args=config.get('args', []),
                env=config.get('env', {})
            )
            
            context = stdio_client(server_params)
            read, write = await context.__aenter__()
            session = ClientSession(read, write)
            await session.__aenter__()
            await session.initialize()
            
            return session, context
            
        elif transport == 'http':
            # Server remoto con SSE
            url = config.get('url', '')
            headers = config.get('headers', {})
            
            # Crea client HTTP con headers personalizzati
            http_client = httpx.AsyncClient(headers=headers)
            
            context = sse_client(url, http_client=http_client)
            read, write = await context.__aenter__()
            session = ClientSession(read, write)
            await session.__aenter__()
            await session.initialize()
            
            return session, context
        
        return None
    
    async def list_available_resources(self, server_name: str, use_cache: bool = True) -> List[Dict[str, Any]]:
        """
        Elenca tutte le risorse disponibili da un server MCP usando l'SDK nativo.
        
        Args:
            server_name: Nome del server MCP
            use_cache: Se True, usa la cache se disponibile
            
        Returns:
            Lista di dizionari con informazioni sulle risorse:
            [{'uri': str, 'name': str, 'description': str, 'mimeType': str}, ...]
        """
        # Calcola hash della configurazione per invalidare cache
        import hashlib
        import json
        config_str = json.dumps(self._server_configs, sort_keys=True)
        current_hash = hashlib.md5(config_str.encode()).hexdigest()
        
        # Usa cache se disponibile e richiesta
        if use_cache and self._discovery_cache_hash == current_hash:
            if server_name in self._resources_cache:
                return self._resources_cache[server_name]
        
        # Altrimenti interroga il server
        session_tuple = await self._create_native_session(server_name)
        if not session_tuple:
            return []
        
        session, context = session_tuple
        
        try:
            # Lista le risorse disponibili
            result = await session.list_resources()
            
            # Converti in formato semplice
            resources = []
            for resource in result.resources:
                resources.append({
                    'uri': str(resource.uri),
                    'name': resource.name,
                    'description': resource.description or '',
                    'mimeType': resource.mimeType or ''
                })
            
            # Aggiorna cache
            self._resources_cache[server_name] = resources
            self._discovery_cache_hash = current_hash
            
            return resources
            
        finally:
            # Chiudi la sessione
            await session.__aexit__(None, None, None)
            await context.__aexit__(None, None, None)
    
    async def list_available_prompts(self, server_name: str, use_cache: bool = True) -> List[Dict[str, Any]]:
        """
        Elenca tutti i prompt disponibili da un server MCP usando l'SDK nativo.
        
        Args:
            server_name: Nome del server MCP
            use_cache: Se True, usa la cache se disponibile
            
        Returns:
            Lista di dizionari con informazioni sui prompt:
            [{'name': str, 'description': str, 'arguments': [...]}, ...]
        """
        # Calcola hash della configurazione per invalidare cache
        import hashlib
        import json
        config_str = json.dumps(self._server_configs, sort_keys=True)
        current_hash = hashlib.md5(config_str.encode()).hexdigest()
        
        # Usa cache se disponibile e richiesta
        if use_cache and self._discovery_cache_hash == current_hash:
            if server_name in self._prompts_cache:
                return self._prompts_cache[server_name]
        
        # Altrimenti interroga il server
        session_tuple = await self._create_native_session(server_name)
        if not session_tuple:
            return []
        
        session, context = session_tuple
        
        try:
            # Lista i prompt disponibili
            result = await session.list_prompts()
            
            # Converti in formato semplice
            prompts = []
            for prompt in result.prompts:
                prompt_info = {
                    'name': prompt.name,
                    'description': prompt.description or '',
                    'arguments': []
                }
                
                # Aggiungi informazioni sugli argomenti se presenti
                if prompt.arguments:
                    for arg in prompt.arguments:
                        prompt_info['arguments'].append({
                            'name': arg.name,
                            'description': arg.description or '',
                            'required': arg.required
                        })
                
                prompts.append(prompt_info)
            
            # Aggiorna cache
            self._prompts_cache[server_name] = prompts
            self._discovery_cache_hash = current_hash
            
            return prompts
            
        finally:
            # Chiudi la sessione
            await session.__aexit__(None, None, None)
            await context.__aexit__(None, None, None)
    
    def invalidate_discovery_cache(self) -> None:
        """
        Invalida la cache di discovery (risorse e prompt).
        Utile quando si sa che le configurazioni sono cambiate.
        """
        self._resources_cache = {}
        self._prompts_cache = {}
        self._discovery_cache_hash = None


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