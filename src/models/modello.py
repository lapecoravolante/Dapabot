"""
Modello per i modelli LLM disponibili per ogni provider
"""

from peewee import CharField, ForeignKeyField
from .base import BaseModel
from .provider import ProviderModel


class ModelloModel(BaseModel):
    """
    Rappresenta un modello LLM disponibile per un provider
    """
    id = CharField(primary_key=True, max_length=200)
    provider = ForeignKeyField(ProviderModel, backref='modelli', on_delete='CASCADE')
    
    class Meta:
        table_name = 'modello'

# Made with Bob
