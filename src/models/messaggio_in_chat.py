"""
Modello per la relazione many-to-many tra Chat e Messaggio
"""

from peewee import ForeignKeyField, DateTimeField, CharField, CompositeKey
from .base import BaseModel
from .chat import ChatModel


class MessaggioInChatModel(BaseModel):
    """
    Tabella di associazione tra Chat e Messaggio (relazione many-to-many)
    """
    chat = ForeignKeyField(ChatModel, backref='messaggi_in_chat', on_delete='CASCADE')
    messaggio_id = CharField(max_length=100)
    messaggio_timestamp = DateTimeField()
    
    class Meta:
        table_name = 'messaggio_in_chat'
        primary_key = CompositeKey('chat', 'messaggio_id', 'messaggio_timestamp')
        indexes = (
            (('messaggio_id', 'messaggio_timestamp'), False),  # Indice per foreign key
        )

# Made with Bob
