"""
Modello per la configurazione RAG di ogni provider
"""

from peewee import CharField, IntegerField, BooleanField, ForeignKeyField
from .base import BaseModel
from .provider import ProviderModel


class ConfigurazioneRagModel(BaseModel):
    """
    Configurazione RAG (Retrieval Augmented Generation) per un provider
    """
    provider = ForeignKeyField(ProviderModel, backref='configurazioni_rag', on_delete='CASCADE')
    attivo = BooleanField(default=False)
    modello = CharField(max_length=200, null=True)
    top_k = IntegerField(default=5)
    directory_allegati = CharField(max_length=500, default='uploads')
    modalita_ricerca = CharField(max_length=50, default='similarity')
    
    class Meta:
        table_name = 'configurazione_rag'
    
    def to_dict(self):
        """Converte il modello in dizionario"""
        return {
            'attivo': self.attivo,
            'modello': self.modello,
            'top_k': self.top_k,
            'directory_allegati': self.directory_allegati,
            'modalita_ricerca': self.modalita_ricerca,
        }

# Made with Bob
