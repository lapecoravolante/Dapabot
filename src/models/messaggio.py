"""
Modello per i messaggi nelle chat
"""

from peewee import CharField, TextField, DateTimeField
from datetime import datetime
from .base import BaseModel


class MessaggioModel(BaseModel):
    """
    Rappresenta un messaggio in una chat
    """
    id = CharField(max_length=100)
    timestamp = DateTimeField(default=datetime.now)
    ruolo = CharField(max_length=20)  # user, assistant, system
    contenuto = TextField()
    
    class Meta:
        table_name = 'messaggio'
        primary_key = False  # Chiave primaria composita
        indexes = (
            (('id', 'timestamp'), True),  # Chiave primaria composita unica
        )

# Made with Bob
