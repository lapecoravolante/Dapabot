"""
Modello base per tutti i modelli Peewee.
Configura la connessione al database unificato config.db
"""

from peewee import SqliteDatabase, Model

# Database unificato
db = SqliteDatabase('config.db', pragmas={
    'journal_mode': 'wal',
    'cache_size': -1024 * 64,
    'foreign_keys': 1,
    'ignore_check_constraints': 0,
    'synchronous': 0
})


class BaseModel(Model):
    """Classe base per tutti i modelli"""
    
    class Meta:
        database = db
    
    @classmethod
    def create_tables(cls, models=None):
        """Crea tutte le tabelle nel database"""
        if models is None:
            # Importa tutti i modelli
            from . import (
                ProviderModel, ConfigurazioneRagModel, ModelloModel,
                ChatModel, MessaggioModel, AllegatoModel,
                MessaggioInChatModel, ToolModel, MCPServerModel
            )
            models = [
                ProviderModel, ConfigurazioneRagModel, ModelloModel,
                ChatModel, MessaggioModel, AllegatoModel,
                MessaggioInChatModel, ToolModel, MCPServerModel
            ]
        
        db.create_tables(models, safe=True)
    
    @classmethod
    def drop_tables(cls, models=None):
        """Elimina tutte le tabelle dal database"""
        if models is None:
            from . import (
                ProviderModel, ConfigurazioneRagModel, ModelloModel,
                ChatModel, MessaggioModel, AllegatoModel,
                MessaggioInChatModel, ToolModel, MCPServerModel
            )
            models = [
                MCPServerModel, ToolModel, MessaggioInChatModel, AllegatoModel,
                MessaggioModel, ChatModel, ModelloModel,
                ConfigurazioneRagModel, ProviderModel
            ]
        
        db.drop_tables(models, safe=True)

# Made with Bob
