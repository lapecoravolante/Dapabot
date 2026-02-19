"""
Modelli Peewee per il database unificato config.db
"""

from .base import db, BaseModel
from .provider import ProviderModel
from .configurazione_rag import ConfigurazioneRagModel
from .modello import ModelloModel
from .chat import ChatModel
from .messaggio import MessaggioModel
from .allegato import AllegatoModel
from .messaggio_in_chat import MessaggioInChatModel
from .tool import ToolModel
from .mcp_server import MCPServerModel

__all__ = [
    'db',
    'BaseModel',
    'ProviderModel',
    'ConfigurazioneRagModel',
    'ModelloModel',
    'ChatModel',
    'MessaggioModel',
    'AllegatoModel',
    'MessaggioInChatModel',
    'ToolModel',
    'MCPServerModel',
]

# Made with Bob
