"""
Modello per le sessioni di chat
"""

from peewee import AutoField, ForeignKeyField
from .base import BaseModel
from .provider import ProviderModel
from .modello import ModelloModel


class ChatModel(BaseModel):
    """
    Rappresenta una sessione di chat tra un provider e un modello
    """
    id = AutoField(primary_key=True)
    provider = ForeignKeyField(ProviderModel, backref='chats', on_delete='CASCADE')
    modello = ForeignKeyField(ModelloModel, backref='chats', on_delete='CASCADE')
    
    class Meta:
        table_name = 'chat'
        indexes = (
            (('provider', 'modello'), True),  # Indice unico su provider+modello
        )

# Made with Bob
