"""
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


class MCPClientManager:
    """
    Gestisce i client MCP usando mcp-use.
    Fornisce un'interfaccia semplificata per caricare configurazioni dal database
    e ottenere tools, risorse e prompt per gli agenti LangChain.
    """
    
    def __init__(self):
        """Inizializza il manager"""
        self._client: Optional[MCPClient] = None
        self._adapter: Optional[MCPLangChainAdapter] = None
        self._server_configs: Dict[str, Dict[str, Any]] = {}
        self._all_tools_cache: List[BaseTool] = []
        self._config_hash: Optional[str] = None
        # Stato del riavvio in background
        self._restart_in_progress: bool = False
        self._restart_thread: Optional[threading.Thread] = None
    
    def carica_configurazioni_da_db(self) -> None:
        """
        Carica le configurazioni dei server MCP attivi dal database
        e le prepara per MCPClient.
        NON resetta il client se le configurazioni non sono cambiate.
        """
        servers_attivi = ConfigurazioneDB.carica_mcp_servers_attivi()
        
        # Costruisci le nuove configurazioni nel formato mcp-use
        new_server_configs = {}
        
        for server in servers_attivi:
            nome = server['nome']
            tipo = server['tipo']
            config = server['configurazione']
            
            if tipo == 'local':
                # Configurazione per server locale (stdio)
                new_server_configs[nome] = {
                    'command': config.get('comando', ''),
                    'args': config.get('args', []),
                    'env': config.get('env', {})
                }
            elif tipo == 'remote':
                # Configurazione per server remoto (HTTP/SSE)
                server_config = {
                    'url': config.get('url', '')
                }
                
                # Aggiungi headers se presenti
                headers = config.get('headers', {})
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
        old_config_json = json.dumps(self._server_configs, sort_keys=True)
        new_config_json = json.dumps(new_server_configs, sort_keys=True)
        
        # Aggiorna solo se le configurazioni sono cambiate
        if old_config_json != new_config_json:
            self._server_configs = new_server_configs
            # Resetta il client per forzare la riconnessione con le nuove configurazioni
            self._client = None
            self._adapter = None
            self._all_tools_cache = []
            self._config_hash = None
            # NON pulire gli errori qui! Verranno puliti in get_all_as_langchain_tools()
            # quando effettivamente ricarica i tools
    
    def get_client(self) -> MCPClient:
        """
        Ottiene o crea il client MCP con le configurazioni caricate.
        Se un riavvio è in corso, aspetta che finisca prima di restituire il client.
        
        Returns:
            Istanza di MCPClient
        """
        # Se un riavvio è in corso, aspetta che finisca
        if self._restart_in_progress and self._restart_thread:
            self._restart_thread.join(timeout=5.0)
        
        if not self._server_configs:
            self.carica_configurazioni_da_db()
        
        if self._client is None:
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
        config_str = json.dumps(self._server_configs, sort_keys=True)
        current_hash = hashlib.md5(config_str.encode()).hexdigest()
        
        # Se la configurazione non è cambiata e abbiamo una cache, usala
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
    
    def _do_restart(self) -> None:
        """
        Esegue il riavvio effettivo del client in background.
        Questo metodo viene eseguito in un thread separato.
        """
        try:
            # Resetta il client
            self._client = None
            self._adapter = None
            self._all_tools_cache = []
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
    
    def invalidate_cache(self) -> None:
        """
        Invalida la cache di tools/risorse/prompt.
        Utile quando si sa che le configurazioni sono cambiate.
        """
        self._all_tools_cache = []
        self._config_hash = None


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