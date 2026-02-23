"""
<<<<<<< HEAD
Client MCP semplificato usando langchain-mcp-adapters
"""

from typing import Dict, Any, List, Optional
import asyncio
import threading
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
=======
Client MCP unificato usando mcp-use per tools, risorse e prompt.
Sostituisce completamente langchain-mcp-adapters e l'SDK nativo MCP.
"""

from typing import Dict, Any, List, Optional, Tuple
import asyncio
import threading
import hashlib
import json
import logging
from mcp_use import MCPClient
from langchain_core.tools import BaseTool
from src.ConfigurazioneDB import ConfigurazioneDB
from src.mcp.langchain_adapter import MCPLangChainAdapter

# Configura un handler per catturare i log di mcp-use
class MCPErrorHandler(logging.Handler):
    """Handler personalizzato per catturare errori da mcp-use"""
    def __init__(self):
        super().__init__()
        self.errors = []
    
    def emit(self, record):
        if record.levelno >= logging.ERROR:
            self.errors.append(record.getMessage())
    
    def clear(self):
        self.errors = []
    
    def get_errors(self):
        return self.errors.copy()

# Crea un'istanza globale del handler
_mcp_error_handler = MCPErrorHandler()
_mcp_logger = logging.getLogger('mcp_use')
_mcp_logger.addHandler(_mcp_error_handler)
>>>>>>> dev


class MCPClientManager:
    """
<<<<<<< HEAD
    Gestisce i client MCP usando langchain-mcp-adapters.
    Fornisce un'interfaccia semplificata per caricare configurazioni dal database
    e ottenere tools per gli agenti LangChain.
=======
    Gestisce i client MCP usando mcp-use.
    Fornisce un'interfaccia semplificata per caricare configurazioni dal database
    e ottenere tools, risorse e prompt per gli agenti LangChain.
>>>>>>> dev
    """
    
    def __init__(self):
        """Inizializza il manager"""
<<<<<<< HEAD
        self._client: Optional[MultiServerMCPClient] = None
        self._server_configs: Dict[str, Dict[str, Any]] = {}
        self._tools_cache: List[BaseTool] = []
=======
        self._client: Optional[MCPClient] = None
        self._adapter: Optional[MCPLangChainAdapter] = None
        self._server_configs: Dict[str, Dict[str, Any]] = {}
        self._all_tools_cache: List[BaseTool] = []
>>>>>>> dev
        self._config_hash: Optional[str] = None
        # Stato del riavvio in background
        self._restart_in_progress: bool = False
        self._restart_thread: Optional[threading.Thread] = None
    
    def carica_configurazioni_da_db(self) -> None:
        """
        Carica le configurazioni dei server MCP attivi dal database
<<<<<<< HEAD
        e le prepara per MultiServerMCPClient.
=======
        e le prepara per MCPClient.
>>>>>>> dev
        NON resetta il client se le configurazioni non sono cambiate.
        """
        servers_attivi = ConfigurazioneDB.carica_mcp_servers_attivi()
        
<<<<<<< HEAD
        # Costruisci le nuove configurazioni
=======
        # Costruisci le nuove configurazioni nel formato mcp-use
>>>>>>> dev
        new_server_configs = {}
        
        for server in servers_attivi:
            nome = server['nome']
            tipo = server['tipo']
            config = server['configurazione']
            
            if tipo == 'local':
                # Configurazione per server locale (stdio)
                new_server_configs[nome] = {
<<<<<<< HEAD
                    'transport': 'stdio',
=======
>>>>>>> dev
                    'command': config.get('comando', ''),
                    'args': config.get('args', []),
                    'env': config.get('env', {})
                }
            elif tipo == 'remote':
<<<<<<< HEAD
                # Configurazione per server remoto (HTTP)
                server_config = {
                    'transport': 'http',
=======
                # Configurazione per server remoto (HTTP/SSE)
                server_config = {
>>>>>>> dev
                    'url': config.get('url', '')
                }
                
                # Aggiungi headers se presenti
                headers = config.get('headers', {})
<<<<<<< HEAD
                if config.get('api_key'):
                    headers['Authorization'] = f"Bearer {config['api_key']}"
                
                if headers:
                    server_config['headers'] = headers
                
                new_server_configs[nome] = server_config
        
        # Confronta con le configurazioni esistenti
        import json
=======
                if headers:
                    server_config['headers'] = headers
                
                # Gestione autenticazione
                if config.get('api_key'):
                    # Bearer token authentication
                    server_config['auth'] = config['api_key']
                elif config.get('oauth_config'):
                    # OAuth configuration
                    server_config['auth'] = config['oauth_config']
                # Se non c'è né api_key né oauth_config, NON aggiungere 'auth'
                # mcp-use tratterà il server come pubblico (no auth)
                
                new_server_configs[nome] = server_config
        
        # Confronta con le configurazioni esistenti
>>>>>>> dev
        old_config_json = json.dumps(self._server_configs, sort_keys=True)
        new_config_json = json.dumps(new_server_configs, sort_keys=True)
        
        # Aggiorna solo se le configurazioni sono cambiate
        if old_config_json != new_config_json:
            self._server_configs = new_server_configs
            # Resetta il client per forzare la riconnessione con le nuove configurazioni
            self._client = None
<<<<<<< HEAD
            self._tools_cache = []
            self._config_hash = None
    
    def get_client(self) -> MultiServerMCPClient:
=======
            self._adapter = None
            self._all_tools_cache = []
            self._config_hash = None
            # NON pulire gli errori qui! Verranno puliti in get_all_as_langchain_tools()
            # quando effettivamente ricarica i tools
    
    def get_client(self) -> MCPClient:
>>>>>>> dev
        """
        Ottiene o crea il client MCP con le configurazioni caricate.
        Se un riavvio è in corso, aspetta che finisca prima di restituire il client.
        
        Returns:
<<<<<<< HEAD
            Istanza di MultiServerMCPClient
=======
            Istanza di MCPClient
>>>>>>> dev
        """
        # Se un riavvio è in corso, aspetta che finisca
        if self._restart_in_progress and self._restart_thread:
            self._restart_thread.join(timeout=5.0)
        
        if not self._server_configs:
            self.carica_configurazioni_da_db()
        
        if self._client is None:
<<<<<<< HEAD
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
=======
            # Crea configurazione nel formato mcp-use
            config = {"mcpServers": self._server_configs}
            self._client = MCPClient(config=config)
        
        return self._client
    
    def get_adapter(self) -> MCPLangChainAdapter:
        """
        Ottiene o crea l'adapter LangChain.
        
        Returns:
            Istanza di MCPLangChainAdapter
        """
        if self._adapter is None:
            self._adapter = MCPLangChainAdapter()
        return self._adapter
    
    async def get_all_as_langchain_tools(self) -> Tuple[List[BaseTool], List[str]]:
        """
        Ottiene tutti i tools, risorse e prompt dai server MCP configurati
        come lista unificata di tools LangChain.
        Usa caching per evitare di ricreare i tools ad ogni chiamata.
        
        Returns:
            Tupla (tools, errors) dove:
            - tools: Lista di tools LangChain sincroni (tools + risorse + prompt)
            - errors: Lista di messaggi di errore (vuota se nessun errore)
        """
        # Calcola hash della configurazione per invalidare cache se cambia
>>>>>>> dev
        config_str = json.dumps(self._server_configs, sort_keys=True)
        current_hash = hashlib.md5(config_str.encode()).hexdigest()
        
        # Se la configurazione non è cambiata e abbiamo una cache, usala
<<<<<<< HEAD
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
=======
        if self._config_hash == current_hash and self._all_tools_cache:
            # Ritorna cache con errori vuoti (già gestiti al caricamento precedente)
            return self._all_tools_cache, []
        
        # Altrimenti ricarica tutto
        # Pulisci gli errori precedenti
        _mcp_error_handler.clear()
        
        client = self.get_client()
        adapter = self.get_adapter()
        
        # Crea tutti i tools, risorse e prompt
        await adapter.create_all(client)
        
        # Ottieni la lista unificata
        all_tools = adapter.all_tools
        
        # Ottieni gli errori catturati durante il caricamento
        errors = _mcp_error_handler.get_errors()
        
        # Aggiorna cache
        self._all_tools_cache = all_tools
        self._config_hash = current_hash
        
        # Ritorna tools ed errori separatamente
        return all_tools, errors
    
    async def get_tools_only(self) -> List[BaseTool]:
        """
        Ottiene solo i tools (esclude risorse e prompt).
        
        Returns:
            Lista di tools LangChain
        """
        client = self.get_client()
        adapter = self.get_adapter()
        await adapter.create_tools(client)
        return adapter.tools
    
    async def get_resources_only(self) -> List[BaseTool]:
        """
        Ottiene solo le risorse (come tools LangChain).
        
        Returns:
            Lista di risorse convertite in tools LangChain
        """
        client = self.get_client()
        adapter = self.get_adapter()
        await adapter.create_resources(client)
        return adapter.resources
    
    async def get_prompts_only(self) -> List[BaseTool]:
        """
        Ottiene solo i prompt (come tools LangChain).
        
        Returns:
            Lista di prompt convertiti in tools LangChain
        """
        client = self.get_client()
        adapter = self.get_adapter()
        await adapter.create_prompts(client)
        return adapter.prompts
    
    async def get_preview_info(self) -> Dict[str, Dict[str, int]]:
        """
        Ottiene informazioni di preview su tools, risorse e prompt
        per ogni server configurato.
        
        Returns:
            Dizionario con conteggi per server:
            {
                'server_name': {
                    'tools': 5,
                    'resources': 3,
                    'prompts': 2
                }
            }
        """
        client = self.get_client()
        adapter = self.get_adapter()
        
        # Crea tutto per ottenere i conteggi
        await adapter.create_all(client)
        
        # Per ora ritorniamo conteggi globali
        # TODO: mcp-use potrebbe non fornire info per-server facilmente
        return {
            'total': {
                'tools': adapter.get_tools_count(),
                'resources': adapter.get_resources_count(),
                'prompts': adapter.get_prompts_count()
            }
        }
>>>>>>> dev
    
    def _do_restart(self) -> None:
        """
        Esegue il riavvio effettivo del client in background.
        Questo metodo viene eseguito in un thread separato.
        """
        try:
            # Resetta il client
            self._client = None
<<<<<<< HEAD
            self._tools_cache = []
=======
            self._adapter = None
            self._all_tools_cache = []
>>>>>>> dev
            self._config_hash = None
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
<<<<<<< HEAD
=======
    
    def invalidate_cache(self) -> None:
        """
        Invalida la cache di tools/risorse/prompt.
        Utile quando si sa che le configurazioni sono cambiate.
        """
        self._all_tools_cache = []
        self._config_hash = None
>>>>>>> dev


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